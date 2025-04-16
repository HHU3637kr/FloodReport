from fastapi import APIRouter, HTTPException
from pydantic import ValidationError
from loguru import logger
from src.ui.api.models import LinkInput
from src.ui.api.utils import extract_tasks, start_extract_task, kb_manager

router = APIRouter()

@router.post("")
async def extract_links(link_input: LinkInput):
    """从链接提取文本、图片和视频信息，并保存到指定知识库"""
    try:
        if not kb_manager.get(link_input.db_name):
            raise HTTPException(status_code=404, detail="指定的知识库不存在")

        logger.info(f"收到链接提取请求: {link_input.urls}, 目标知识库: {link_input.db_name}")

        # 创建任务状态对象并启动任务
        task = start_extract_task(link_input.urls, link_input.db_name)
        
        # 立即返回任务ID和状态
        return {
            "status": "success", 
            "message": "链接提取任务已启动",
            "task_id": task.task_id
        }
    except HTTPException:
        raise
    except ValidationError as e:
        logger.error(f"链接格式验证失败: {str(e)}")
        raise HTTPException(status_code=400, detail=f"链接格式不正确: {str(e)}")
    except Exception as e:
        logger.error(f"链接提取失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/progress/{task_id}")
async def get_extract_progress(task_id: str):
    """获取提取任务的进度"""
    if task_id not in extract_tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = extract_tasks[task_id]
    return task.to_dict()


@router.get("/tasks")
async def list_extract_tasks(limit: int = 10):
    """列出最近的提取任务"""
    # 按开始时间倒序排序
    sorted_tasks = sorted(
        extract_tasks.values(), 
        key=lambda t: t.start_time,
        reverse=True
    )[:limit]
    
    return {
        "status": "success",
        "data": [task.to_dict() for task in sorted_tasks]
    }


@router.get("/logs/{task_id}")
async def get_extract_logs(task_id: str, limit: int = 50):
    """获取提取任务的日志记录"""
    try:
        if task_id not in extract_tasks:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        # 从日志文件中读取最近的日志
        log_lines = []
        try:
            # 打开日志文件，读取最近的记录
            with open("logs/rag_process.log", "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                # 获取最后limit行
                log_lines = all_lines[-limit:]
                
                # 如果有特定的任务ID，筛选包含该ID的日志
                if task_id:
                    filtered_lines = []
                    for line in log_lines:
                        if task_id in line or any(keyword in line for keyword in ["提取", "extract", "链接", "索引", "知识库"]):
                            filtered_lines.append(line.strip())
                    log_lines = filtered_lines or log_lines
        except Exception as e:
            logger.error(f"读取日志文件失败: {str(e)}")
            log_lines = [f"无法读取日志文件: {str(e)}"]
        
        return {
            "status": "success",
            "data": log_lines
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取日志记录失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取日志记录失败: {str(e)}") 