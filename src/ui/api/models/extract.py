from pydantic import BaseModel, validator
from typing import List, Dict
from datetime import datetime
import uuid

class LinkInput(BaseModel):
    urls: List[str]
    db_name: str

    @validator('urls')
    def clean_urls(cls, urls):
        if not urls:
            raise ValueError("至少需要提供一个URL")
            
        cleaned_urls = []
        errors = []
        
        for i, url in enumerate(urls):
            url = url.strip()
            if not url:
                continue
                
            if url.startswith('@'):
                url = url[1:]
                
            if not url.startswith(('http://', 'https://')):
                errors.append(f"链接 #{i+1} '{url}' 格式无效，必须以http://或https://开头")
                continue
                
            cleaned_urls.append(url)
        
        if errors:
            raise ValueError(', '.join(errors))
            
        if not cleaned_urls:
            raise ValueError("没有有效的URL")
            
        return cleaned_urls


class TaskStatus:
    def __init__(self, urls: List[str], db_name: str):
        self.task_id = f"task_{uuid.uuid4().hex[:8]}"
        self.db_name = db_name
        self.urls = urls
        self.total = len(urls)
        self.current = 0
        self.current_url = ""
        self.status = "准备中" # 准备中, 提取中, 提取完成, 构建索引中, 完成, 失败
        self.start_time = datetime.now().isoformat()
        self.end_time = None
        self.error = None
        self.results = []

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "db_name": self.db_name,
            "total": self.total,
            "current": self.current,
            "current_url": self.current_url,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "error": self.error
        } 