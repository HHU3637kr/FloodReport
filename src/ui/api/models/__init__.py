from src.ui.api.models.base import (
    QueryInput, 
    Message, 
    ChatInput, 
    ChatHistoryEntry, 
    ExtractedContent, 
    DeleteContentInput,
    BuildIndexInput,
    ReportInput
)
from src.ui.api.models.knowledge_base import KnowledgeBaseCreate, KnowledgeBaseUpdate
from src.ui.api.models.extract import LinkInput, TaskStatus
from src.ui.api.models.user import UserCreate, UserLogin, UserResponse, TokenResponse, UserUpdate, PasswordUpdate

# 将User作为UserResponse的别名导出
User = UserResponse

__all__ = [
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "User",  # 添加User别名
    "UserUpdate",
    "PasswordUpdate",
    "TokenResponse",
    "QueryInput",
    "Message",
    "ChatInput",
    "ChatHistoryEntry",
    "ExtractedContent",
    "DeleteContentInput",
    "BuildIndexInput",
    "ReportInput",
    "KnowledgeBaseCreate",
    "KnowledgeBaseUpdate",
    "LinkInput",
    "TaskStatus"
] 