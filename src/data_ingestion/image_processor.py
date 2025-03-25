from PIL import Image
from io import BytesIO
from tos import TosClientV2, HttpMethodType
import requests
import uuid
import os
from loguru import logger
from src.config import config

logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

tos_client = TosClientV2(
    ak=os.getenv('VOLC_ACCESSKEY'),
    sk=os.getenv('VOLC_SECRETKEY'),
    endpoint=config['tos']['endpoint'],
    region=config['tos']['region']
)

def compress_image(image_data, target_size=300 * 1024):
    """压缩图像到目标大小（单位：字节）"""
    try:
        img = Image.open(BytesIO(image_data))
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        output = BytesIO()
        current_size = len(image_data)
        image_quality = int(float(target_size / current_size) * 100) if current_size > target_size else 85
        format = 'JPEG' if img.mode == 'RGB' else 'PNG'
        img.save(output, format=format, optimize=True, quality=image_quality)
        while output.tell() > target_size and image_quality > 10:
            output.seek(0)
            output.truncate()
            image_quality -= 10
            img.save(output, format=format, optimize=True, quality=image_quality)
        return output.getvalue()
    except Exception as e:
        logger.error(f"图像压缩失败: {e}")
        return image_data

def upload_image(image_data, object_key_prefix):
    """上传图像到 TOS 并返回预签名 URL"""
    unique_key = f"{object_key_prefix}{uuid.uuid4()}.jpeg"
    try:
        tos_client.put_object(config['tos']['bucket_name'], unique_key, content=image_data)
        pre_signed_url = tos_client.pre_signed_url(
            HttpMethodType.Http_Method_Get, config['tos']['bucket_name'], unique_key, expires=3600
        )
        return pre_signed_url.signed_url
    except Exception as e:
        logger.error(f"上传 TOS 失败: {e}")
        raise

def process_images(image_urls, object_key_prefix):
    """处理并上传所有图像，返回描述"""
    image_descriptions = []
    for img_url in image_urls:  # 处理所有图片
        try:
            img_response = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            img_response.raise_for_status()
            img_data = img_response.content
            compressed_img = compress_image(img_data)
            pre_signed_url = upload_image(compressed_img, object_key_prefix)
            image_descriptions.append(f"图像URL: {pre_signed_url}")
            logger.debug(f"上传图像: {pre_signed_url[:50]}...")
        except Exception as e:
            logger.error(f"处理图像失败: {img_url}, 错误: {e}")
    return image_descriptions