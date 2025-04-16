from pydantic import BaseModel
from typing import List, Dict, Optional, Any

class QueryInput(BaseModel):
    """查询输入模型"""
    query: str
    category: Optional[str] = None
    k: int = 5
    alpha: float = 0.7
    report_date: Optional[str] = None
    issuing_unit: Optional[str] = None
    save_history: bool = True
    
class DeleteContentInput(BaseModel):
    """删除内容输入模型"""
    url: str

class BuildIndexInput(BaseModel):
    """构建索引输入模型"""
    kb_id: str
    index_id: Optional[str] = None 