from PIL import Image
from io import BytesIO
from tos import TosClientV2, HttpMethodType
import requests
import uuid
import os
from loguru import logger
from src.config import config

# 配置日志记录器，设置日志文件路径和格式
logger.add("logs/rag_process.log", rotation="1 MB", format="{time} {level} {message}")

# 初始化火山引擎对象存储客户端，用于存储处理后的图像
tos_client = TosClientV2(
    ak=os.getenv('VOLC_ACCESSKEY'),       # 从环境变量获取访问密钥
    sk=os.getenv('VOLC_SECRETKEY'),       # 从环境变量获取密钥
    endpoint=config['tos']['endpoint'],   # 从配置文件获取端点
    region=config['tos']['region']        # 从配置文件获取区域
)

def compress_image(image_data, target_size=300 * 1024):
    """
    压缩图像到目标大小
    
    根据目标大小计算压缩质量，并在不损失太多质量的情况下减小图像体积
    
    Args:
        image_data (bytes): 原始图像的二进制数据
        target_size (int): 目标文件大小（字节）, 默认300KB
        
    Returns:
        bytes: 压缩后的图像二进制数据
        
    Note:
        如果原图小于目标大小，仍会使用85%质量进行压缩以获得更好的大小优化
    """
    try:
        img = Image.open(BytesIO(image_data))
        # 确保图像为RGB或RGBA模式，以便正确保存
        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGB')
        
        output = BytesIO()
        current_size = len(image_data)  # 获取原始大小
        
        # 根据原始大小和目标大小计算初始压缩质量
        image_quality = int(float(target_size / current_size) * 100) if current_size > target_size else 85
        
        # 根据图像模式选择不同的保存格式
        format = 'JPEG' if img.mode == 'RGB' else 'PNG'
        
        # 保存图像，使用计算的质量参数
        img.save(output, format=format, optimize=True, quality=image_quality)
        
        # 如果第一次压缩仍然超过目标大小，逐步降低质量直到满足要求
        while output.tell() > target_size and image_quality > 10:
            output.seek(0)
            output.truncate()
            image_quality -= 10
            img.save(output, format=format, optimize=True, quality=image_quality)
            
        return output.getvalue()
    except Exception as e:
        logger.error(f"图像压缩失败: {e}")
        # 压缩失败时返回原始图像数据
        return image_data

def upload_image(image_data, object_key_prefix):
    """
    上传图像到火山引擎对象存储并返回预签名URL
    
    为每个图像生成唯一的键名，上传到TOS，并创建一个临时访问URL
    
    Args:
        image_data (bytes): 要上传的图像数据
        object_key_prefix (str): 对象键名前缀, 用于组织存储结构
        
    Returns:
        str: 包含上传图像的预签名URL，有效期为1小时
        
    Raises:
        Exception: 上传过程中发生错误时
    """
    # 创建唯一对象键，确保不会覆盖已有文件
    unique_key = f"{object_key_prefix}{uuid.uuid4()}.jpeg"
    try:
        # 将图像上传到对象存储
        tos_client.put_object(config['tos']['bucket_name'], unique_key, content=image_data)
        
        # 创建一个有1小时有效期的预签名URL
        pre_signed_url = tos_client.pre_signed_url(
            HttpMethodType.Http_Method_Get, config['tos']['bucket_name'], unique_key, expires=3600
        )
        return pre_signed_url.signed_url
    except Exception as e:
        logger.error(f"上传 TOS 失败: {e}")
        raise

def process_images(image_urls, object_key_prefix):
    """
    批量处理和上传图像，并返回图像描述
    
    下载、压缩并上传多个图像URLs，并生成统一格式的描述
    
    Args:
        image_urls (list): 图像URL列表
        object_key_prefix (str): 对象存储的键名前缀
        
    Returns:
        list: 处理后的图像描述列表，每个描述包含图像的预签名URL
    """
    image_descriptions = []
    for img_url in image_urls:  # 处理所有图片
        try:
            # 下载图像
            img_response = requests.get(img_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            img_response.raise_for_status()
            img_data = img_response.content
            
            # 压缩图像
            compressed_img = compress_image(img_data)
            
            # 上传到对象存储并获取预签名URL
            pre_signed_url = upload_image(compressed_img, object_key_prefix)
            
            # 添加到图像描述列表
            image_descriptions.append(f"图像URL: {pre_signed_url}")
            logger.debug(f"上传图像: {pre_signed_url[:50]}...")
        except Exception as e:
            logger.error(f"处理图像失败: {img_url}, 错误: {e}")
    
    return image_descriptions