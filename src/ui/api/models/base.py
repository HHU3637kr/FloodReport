from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class QueryInput(BaseModel):
    query: str
    k: int = 5
    category: Optional[str] = None
    alpha: Optional[float] = 0.7  # 向量相似度权重
    issuing_unit: Optional[str] = None  # 添加发布单位字段
    report_date: Optional[str] = None   # 添加报告日期字段
    save_history: Optional[bool] = False # 是否保存到历史记录

    @validator('issuing_unit', pre=True, always=True)
    def validate_issuing_unit(cls, issuing_unit):
        if issuing_unit is not None and not isinstance(issuing_unit, str):
            raise ValueError("发布单位必须是字符串类型")
        if issuing_unit is not None and isinstance(issuing_unit, str) and not issuing_unit.strip():
            return None
        return issuing_unit.strip() if issuing_unit else None

    @validator('report_date', pre=True, always=True)
    def validate_report_date(cls, report_date):
        if report_date is not None and not isinstance(report_date, str):
            raise ValueError("报告日期必须是字符串类型")
        if report_date is not None and isinstance(report_date, str):
            if not report_date.strip():
                return None
            try:
                datetime.strptime(report_date, "%Y年%m月%d日")
            except ValueError:
                raise ValueError("报告日期格式必须为 'YYYY年MM月DD日'")
        return report_date

    @validator('k')
    def validate_k(cls, k):
        if k <= 0:
            raise ValueError("k必须大于0")
        return k

    @validator('alpha')
    def validate_alpha(cls, alpha):
        if alpha is not None and (alpha < 0 or alpha > 1):
            raise ValueError("alpha必须在0到1之间")
        return alpha


class Message(BaseModel):
    role: str  # "user" 或 "assistant"
    content: str
    timestamp: Optional[str] = None


class ChatInput(BaseModel):
    query: str
    kb_id: str
    k: Optional[int] = 5
    chat_history: Optional[List[Message]] = []


class ChatHistoryEntry(BaseModel):
    id: str
    title: str
    messages: List[Message]
    created_at: str
    updated_at: str
    kb_id: str


class ExtractedContent(BaseModel):
    url: str
    title: str
    content: str
    extracted_time: str
    structured_data: Dict


class DeleteContentInput(BaseModel):
    url: str


class BuildIndexInput(BaseModel):
    """构建索引输入模型"""
    kb_id: str
    index_id: Optional[str] = None


class ReportInput(BaseModel):
    """报告生成输入模型"""
    query: str
    issuing_unit: Optional[str] = None
    report_date: Optional[str] = None
    
    @validator('issuing_unit', pre=True, always=True)
    def validate_issuing_unit(cls, issuing_unit):
        if issuing_unit is not None and not isinstance(issuing_unit, str):
            raise ValueError("发布单位必须是字符串类型")
        if issuing_unit is not None and isinstance(issuing_unit, str) and not issuing_unit.strip():
            return None
        return issuing_unit.strip() if issuing_unit else None

    @validator('report_date', pre=True, always=True)
    def validate_report_date(cls, report_date):
        if report_date is not None and not isinstance(report_date, str):
            raise ValueError("报告日期必须是字符串类型")
        if report_date is not None and isinstance(report_date, str):
            if not report_date.strip():
                return None
            try:
                datetime.strptime(report_date, "%Y年%m月%d日")
            except ValueError:
                raise ValueError("报告日期格式必须为 'YYYY年MM月DD日'")
        return report_date 