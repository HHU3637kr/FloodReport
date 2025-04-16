import threading
import asyncio
from loguru import logger
from src.data_ingestion.link_fetcher_main import process_links
from src.knowledge_management.vector_store import VectorStore
from src.ui.api.models.extract import TaskStatus

# 存储任务状态的字典
extract_tasks = {}

def run_extract_task(task, urls, db_name):
    """在后台线程中运行链接提取任务"""
    try:
        task.status = "提取中"
        
        # 定义进度回调函数
        def update_progress(index, url, status):
            task.current = index + 1  # 调整为1-based索引
            task.current_url = url
            task.status = "提取中" # 保持状态为"提取中"直到全部完成
            if status == "错误":
                logger.error(f"处理链接 {url} 失败")
            elif status == "失败":
                logger.warning(f"处理链接 {url} 无法获取有效内容")
            elif status == "完成":
                logger.info(f"处理链接 {url} 完成")
                # 检查是否所有URL都处理完成
                if task.current >= task.total:
                    task.status = "完成"
        
        # 调用process_links并传入回调函数
        results = process_links(urls, db_name, callback=update_progress)
        task.results = results
        
        # 这里移除了自动构建索引的步骤
        # 只提取文本并保存为文件，不建立索引
        
        # 完成任务
        task.current = task.total
        task.status = "完成"
        task.end_time = task.start_time = task.start_time
    except Exception as e:
        task.status = "失败"
        task.error = str(e)
        task.end_time = task.start_time = task.start_time
        logger.error(f"链接提取任务失败: {str(e)}", exc_info=True)

def build_index_for_task(db_name):
    """为任务构建索引"""
    try:
        vector_store = VectorStore(db_name=db_name)
        vector_store.load_texts()
        vector_store.build_index()
        vector_store.save_index()
        return True
    except Exception as e:
        logger.error(f"构建索引失败: {str(e)}", exc_info=True)
        return False

def start_extract_task(urls, db_name):
    """创建并启动提取任务"""
    task = TaskStatus(urls, db_name)
    extract_tasks[task.task_id] = task
    
    # 启动后台线程进行处理
    process_thread = threading.Thread(
        target=run_extract_task,
        args=(task, urls, db_name),
        daemon=True
    )
    process_thread.start()
    
    return task 