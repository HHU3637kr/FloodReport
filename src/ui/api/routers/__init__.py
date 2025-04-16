from .search_router import router as search_router
from .knowledge_base_router import router as knowledge_base_router
from .extract_router import router as extract_router
from .report_router import router as report_router
from .chat_router import router as chat_router
from .system_router import router as system_router
from .index_router import router as index_router

# 导出所有路由
__all__ = [
    "search_router",
    "knowledge_base_router",
    "extract_router",
    "report_router",
    "chat_router",
    "system_router",
    "index_router"
] 