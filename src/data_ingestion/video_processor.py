import subprocess
import os
import uuid
import cv2
import torch
import whisper
from loguru import logger
from src.config import config
from src.data_ingestion.image_processor import compress_image, upload_image

# 配置日志记录
logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

def trim_audio(audio_file, duration=300):
    """
    使用 FFmpeg 截取音频文件的前N秒
    
    对长音频文件进行截取，减少处理时间和资源消耗
    
    Args:
        audio_file (str): 原始音频文件路径
        duration (int): 要保留的音频时长，单位为秒，默认为300秒（5分钟）
    
    Returns:
        str: 截取后的音频文件路径，如果截取失败则返回原始文件路径
    """
    trimmed_audio = audio_file.replace('.mp3', '_trimmed.mp3')
    cmd = ["ffmpeg", "-i", audio_file, "-t", str(duration), "-c", "copy", trimmed_audio, "-y"]
    try:
        # 运行FFmpeg命令，截取音频
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.debug(f"音频截取成功: {trimmed_audio}")
        return trimmed_audio
    except subprocess.CalledProcessError as e:
        logger.error(f"音频截取失败: {e.stderr}")
        return audio_file  # 失败时返回原始文件

def download_video(video_url, video_id):
    """
    从URL下载视频并提取音频文件
    
    使用yt-dlp工具下载各种平台的视频，并提取音频轨道为MP3格式
    
    Args:
        video_url (str): 视频URL，支持各种视频平台
        video_id (str): 用于生成临时文件名的唯一标识符
    
    Returns:
        tuple: (视频文件路径, 音频文件路径)，如果下载失败则返回 (None, None)
    """
    output_file = f"temp_{video_id}.mp4"
    audio_file = f"temp_{video_id}.mp3"
    
    # 下载视频命令
    cmd_download = ["yt-dlp", video_url, "-o", output_file]
    # 提取音频命令
    cmd_extract_audio = ["yt-dlp", "-x", "--audio-format", "mp3", video_url, "-o", audio_file]
    
    try:
        # 执行下载视频和提取音频命令
        subprocess.run(cmd_download, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        subprocess.run(cmd_extract_audio, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        logger.debug(f"下载视频和音频成功: {output_file}, {audio_file}")
        return output_file, audio_file
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        logger.error(f"视频下载失败: {video_url}, 错误: {e}")
        return None, None

def extract_video_frames(video_file, num_frames=5, interval=10):
    """
    从视频文件中提取关键帧
    
    按照固定时间间隔从视频中提取指定数量的帧，用于后续分析和处理
    
    Args:
        video_file (str): 视频文件路径
        num_frames (int): 要提取的帧数量，默认为5
        interval (int): 相邻帧之间的时间间隔，单位为秒，默认为10秒
    
    Returns:
        list: 包含所提取帧的二进制数据的列表，每帧为JPEG格式
    """
    logger.debug(f"开始提取视频帧: {video_file}")
    cap = cv2.VideoCapture(video_file)
    
    if not cap.isOpened():
        logger.error(f"无法打开视频: {video_file}")
        return []
    
    # 获取视频基本信息
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    
    # 计算采样间隔和关键帧索引
    frame_interval = int(fps * interval)
    frame_indices = [int(i * frame_interval) for i in range(min(num_frames, int(duration / interval)))]
    
    frames = []
    for idx in frame_indices:
        # 设置读取位置并获取帧
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = cap.read()
        if ret:
            # 将帧编码为JPEG格式的二进制数据
            _, buffer = cv2.imencode('.jpg', frame)
            frames.append(buffer.tobytes())
    
    cap.release()
    logger.debug(f"提取到 {len(frames)} 帧")
    return frames

def transcribe_audio(audio_file):
    """
    使用Whisper模型转录音频内容
    
    将音频文件转录为文本，自动检测是否可使用GPU加速
    
    Args:
        audio_file (str): 要转录的音频文件路径
    
    Returns:
        str: 转录后的文本内容，如果转录失败则返回None
    """
    logger.debug(f"开始转录音频: {audio_file}")
    trimmed_audio = trim_audio(audio_file)  # 先截取音频
    
    try:
        # 检查并使用可用的GPU设备
        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.debug(f"使用设备: {device}")
        
        # 加载Whisper中型模型
        model = whisper.load_model("medium", device=device)
        
        # 执行音频转录
        result = model.transcribe(trimmed_audio)
        transcription = result["text"]
        logger.debug(f"音频转录成功: {transcription[:100]}...")
        return transcription
    except Exception as e:
        logger.error(f"音频转录异常: {e}")
        return None
    finally:
        # 清理临时文件
        if trimmed_audio != audio_file and os.path.exists(trimmed_audio):
            os.remove(trimmed_audio)
        if os.path.exists(audio_file):
            os.remove(audio_file)

def process_video(video_url, object_key_prefix, client):
    """
    全面处理视频：下载、提取帧、转录音频并分析内容
    
    整合视频处理流程，提取视频的文本和视觉信息
    
    Args:
        video_url (str): 要处理的视频URL
        object_key_prefix (str): 存储提取帧的对象前缀
        client: Ark模型客户端，用于视觉内容分析
    
    Returns:
        list: 包含视频转录和视觉内容描述的文本列表
    """
    video_id = uuid.uuid4().hex[:8]  # 生成唯一标识符
    video_file, audio_file = download_video(video_url, video_id)
    
    if not video_file or not audio_file:
        logger.warning(f"无法下载视频: {video_url}")
        return [f"嵌入视频链接: {video_url}"]

    # 音频转录处理
    transcription = transcribe_audio(audio_file) if audio_file else None
    video_transcriptions = [f"视频音频转录: {transcription}"] if transcription else []

    # 视频帧提取和分析
    frames = extract_video_frames(video_file) if video_file else []
    if frames:
        # 处理所有提取的帧
        frame_urls = []
        for frame_data in frames:
            # 压缩帧并上传到对象存储
            compressed_frame = compress_image(frame_data)
            pre_signed_url = upload_image(compressed_frame, object_key_prefix)
            # 准备用于大模型的图像URL列表
            frame_urls.append({"type": "image_url", "image_url": {"url": pre_signed_url}})

        # 构建提示词，引导模型进行视频内容理解
        prompt = (
            "以下是视频的多个关键帧，按照时间顺序排列。请将这些帧视为一个连续的视频，推测视频的完整内容，包括场景变化、人物行为、可能的对话和动作细节。"
            "尽可能多地保留细节，描述视频中的所有信息（例如时间、地点、人物、对话、事件等），不要生成摘要，而是提供详细的逐帧描述和推测内容。"
            "不要生成任何不真实的内容"
        )
        messages = [{"role": "user", "content": [{"type": "text", "text": prompt}] + frame_urls}]
        
        # 调用大模型进行视频帧分析
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

    # 清理临时文件
    if video_file and os.path.exists(video_file):
        os.remove(video_file)
    if audio_file and os.path.exists(audio_file):
        os.remove(audio_file)

    return video_transcriptions