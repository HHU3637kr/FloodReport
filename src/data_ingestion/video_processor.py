import subprocess
import os
import uuid
import cv2
import torch
import whisper
from loguru import logger
from src.config import config
from src.data_ingestion.image_processor import compress_image, upload_image

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

def trim_audio(audio_file, duration=300):
    """使用 FFmpeg 截取音频前 duration 秒"""
    trimmed_audio = audio_file.replace('.mp3', '_trimmed.mp3')
    cmd = ["ffmpeg", "-i", audio_file, "-t", str(duration), "-c", "copy", trimmed_audio, "-y"]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.debug(f"音频截取成功: {trimmed_audio}")
        return trimmed_audio
    except subprocess.CalledProcessError as e:
        logger.error(f"音频截取失败: {e.stderr}")
        return audio_file

def download_video(video_url, video_id):
    """下载视频并提取音频"""
    output_file = f"temp_{video_id}.mp4"
    audio_file = f"temp_{video_id}.mp3"
    cmd_download = ["yt-dlp", video_url, "-o", output_file]
    cmd_extract_audio = ["yt-dlp", "-x", "--audio-format", "mp3", video_url, "-o", audio_file]
    try:
        subprocess.run(cmd_download, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(cmd_extract_audio, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.debug(f"下载视频和音频成功: {output_file}, {audio_file}")
        return output_file, audio_file
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"视频下载失败: {video_url}, 错误: {e}")
        return None, None

def extract_video_frames(video_file, num_frames=5, interval=10):
    """从视频中提取指定数量的帧"""
    logger.debug(f"开始提取视频帧: {video_file}")
    cap = cv2.VideoCapture(video_file)
    if not cap.isOpened():
        logger.error(f"无法打开视频: {video_file}")
        return []
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    frame_interval = int(fps * interval)
    frame_indices = [int(i * frame_interval) for i in range(min(num_frames, int(duration / interval)))]
    frames = []
    for idx in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            _, buffer = cv2.imencode('.jpg', frame)
            frames.append(buffer.tobytes())
    cap.release()
    logger.debug(f"提取到 {len(frames)} 帧")
    return frames

def transcribe_audio(audio_file):
    """使用 Whisper 转录音频，启用 GPU 加速"""
    logger.debug(f"开始转录音频: {audio_file}")
    trimmed_audio = trim_audio(audio_file)
    try:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.debug(f"使用设备: {device}")
        model = whisper.load_model("medium", device=device)
        result = model.transcribe(trimmed_audio)
        transcription = result["text"]
        logger.debug(f"音频转录成功: {transcription[:100]}...")
        return transcription
    except Exception as e:
        logger.error(f"音频转录异常: {e}")
        return None
    finally:
        if trimmed_audio != audio_file and os.path.exists(trimmed_audio):
            os.remove(trimmed_audio)
        if os.path.exists(audio_file):
            os.remove(audio_file)

def process_video(video_url, object_key_prefix, client):
    """处理视频，返回转录内容"""
    video_id = uuid.uuid4().hex[:8]
    video_file, audio_file = download_video(video_url, video_id)
    if not video_file or not audio_file:
        logger.warning(f"无法下载视频: {video_url}")
        return [f"嵌入视频链接: {video_url}"]

    transcription = transcribe_audio(audio_file) if audio_file else None
    video_transcriptions = [f"视频音频转录: {transcription}"] if transcription else []

    frames = extract_video_frames(video_file) if video_file else []
    if frames:
        frame_urls = []
        for frame_data in frames:
            compressed_frame = compress_image(frame_data)
            pre_signed_url = upload_image(compressed_frame, object_key_prefix)
            frame_urls.append({"type": "image_url", "image_url": {"url": pre_signed_url}})

        prompt = (
            "以下是视频的多个关键帧，按照时间顺序排列。请将这些帧视为一个连续的视频，推测视频的完整内容，包括场景变化、人物行为、可能的对话和动作细节。"
            "尽可能多地保留细节，描述视频中的所有信息（例如时间、地点、人物、对话、事件等），不要生成摘要，而是提供详细的逐帧描述和推测内容。"
            "不要生成任何不真实的内容"
        )
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}] + frame_urls}]
        try:
            response = client.chat.completions.create(
                model=config['model']['understanding']['model_name'],
                messages=messages
            )
            frame_description = response.choices[0].message.content if response.choices else "视频帧描述不可用"
            video_transcriptions.append(f"视频视觉内容: {frame_description}")
        except Exception as e:
            logger.error(f"调用 Ark API 处理视频帧失败: {e}")
            video_transcriptions.append("视频视觉内容: 处理失败")

    if video_file and os.path.exists(video_file):
        os.remove(video_file)
    if audio_file and os.path.exists(audio_file):
        os.remove(audio_file)

    return video_transcriptions