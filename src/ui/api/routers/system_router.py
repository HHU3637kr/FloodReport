from fastapi import APIRouter, HTTPException, Depends
import os
import glob
import platform
import json
from loguru import logger
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel
from src.ui.api.utils import kb_manager
from src.config import load_config, config
from src.ui.api.middlewares.auth_middleware import get_current_user
from src.ui.api.models import User

router = APIRouter()

# 模型设置模型
class ModelSettingsSchema(BaseModel):
    understanding: Dict[str, str]
    embedding: Dict[str, str]
    generation: Dict[str, str]

class ModelSettingsRequest(BaseModel):
    settings: ModelSettingsSchema
    use_custom_keys: bool

@router.get("/system-status")
async def get_system_status():
    """获取系统状态"""
    try:
        # 获取知识库信息
        knowledge_bases = kb_manager.list_all()
        kb_count = len(knowledge_bases)

        # 获取文本文件数量
        text_count = 0
        for kb in knowledge_bases:
            kb_id = kb["id"]
            texts_dir = os.path.join(kb_manager.get_kb_path(kb_id), "raw_texts")
            if os.path.exists(texts_dir):
                text_count += len(glob.glob(os.path.join(texts_dir, "**", "*.txt"), recursive=True))

        # 系统信息
        system_info = {
            "os": platform.system(),
            "version": platform.version(),
            "architecture": platform.machine()
        }

        # 获取日志
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        log_file = os.path.join(project_root, "logs", "rag_process.log")
        logs = []
        
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    logs = f.readlines()[-10:]  # 获取最后10行日志
            except Exception as e:
                logger.error(f"读取日志文件失败: {str(e)}")
                logs = ["无法读取日志文件"]
        else:
            logs = ["日志文件不存在"]

        return {
            "status": "success",
            "stats": {
                "knowledgeBaseCount": kb_count,
                "textCount": text_count,
                "systemInfo": system_info,
                "lastUpdate": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            },
            "logs": logs
        }
    except Exception as e:
        logger.error(f"获取系统状态失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 用户的自定义设置文件路径
def get_user_settings_path(user_id: str) -> str:
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    settings_dir = os.path.join(project_root, "data", "user_settings")
    # 确保目录存在
    os.makedirs(settings_dir, exist_ok=True)
    return os.path.join(settings_dir, f"{user_id}_model_settings.json")

@router.get("/model-settings")
async def get_model_settings(current_user: User = Depends(get_current_user)):
    """获取模型API设置"""
    try:
        # 默认使用系统配置
        settings = {
            "understanding": {
                "provider": config['model']['understanding']['provider'],
                "api_key": "",  # 不返回实际的API密钥
                "model_name": config['model']['understanding']['model_name'],
            },
            "embedding": {
                "provider": config['model']['embedding']['provider'],
                "api_key": "",  # 不返回实际的API密钥
                "model_name": config['model']['embedding']['model_name'],
            },
            "generation": {
                "provider": config['model']['generation']['provider'],
                "api_key": "",  # 不返回实际的API密钥
                "model_name": config['model']['generation']['model_name'],
            }
        }
        
        use_custom_keys = False
        # 获取用户ID，支持current_user为对象或字典的情况
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        if not user_id:
            logger.warning("无法获取用户ID，将使用默认设置")
            return {
                "settings": settings,
                "use_custom_keys": use_custom_keys
            }
            
        settings_path = get_user_settings_path(user_id)
        
        # 如果用户有自定义设置，加载它
        if os.path.exists(settings_path):
            try:
                with open(settings_path, 'r', encoding='utf-8') as f:
                    user_settings = json.load(f)
                    use_custom_keys = user_settings.get('use_custom_keys', False)
                    
                    if use_custom_keys and 'settings' in user_settings:
                        settings = user_settings['settings']
            except Exception as e:
                logger.error(f"读取用户设置失败: {str(e)}")
        
        return {
            "settings": settings,
            "use_custom_keys": use_custom_keys
        }
    except Exception as e:
        logger.error(f"获取模型设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/model-settings")
async def update_model_settings(
    settings_request: ModelSettingsRequest,
    current_user: User = Depends(get_current_user)
):
    """更新模型API设置"""
    try:
        # 获取用户ID，支持current_user为对象或字典的情况
        user_id = current_user.id if hasattr(current_user, 'id') else current_user.get('id')
        if not user_id:
            logger.warning("无法获取用户ID，无法保存设置")
            raise HTTPException(status_code=400, detail="无法获取用户ID")
            
        settings_path = get_user_settings_path(user_id)
        
        # 保存用户设置
        with open(settings_path, 'w', encoding='utf-8') as f:
            json.dump({
                "settings": {
                    "understanding": {
                        "provider": settings_request.settings.understanding.get("provider", ""),
                        "api_key": settings_request.settings.understanding.get("api_key", ""),
                        "model_name": settings_request.settings.understanding.get("model_name", ""),
                    },
                    "embedding": {
                        "provider": settings_request.settings.embedding.get("provider", ""),
                        "api_key": settings_request.settings.embedding.get("api_key", ""),
                        "model_name": settings_request.settings.embedding.get("model_name", ""),
                    },
                    "generation": {
                        "provider": settings_request.settings.generation.get("provider", ""),
                        "api_key": settings_request.settings.generation.get("api_key", ""),
                        "model_name": settings_request.settings.generation.get("model_name", ""),
                    }
                },
                "use_custom_keys": settings_request.use_custom_keys
            }, f, indent=2)
        
        return {"status": "success", "message": "设置已更新"}
    except Exception as e:
        logger.error(f"更新模型设置失败: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e)) 