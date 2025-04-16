from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.ui.api.routers.knowledge_base_router import router as knowledge_base_router
from src.ui.api.routers.search_router import router as search_router
from src.ui.api.routers.extract_router import router as extract_router
from src.ui.api.routers.report_router import router as report_router
from src.ui.api.routers.chat_router import router as chat_router
from src.ui.api.routers.system_router import router as system_router
from src.ui.api.routers.index_router import router as index_router
from src.ui.api.routers.auth_router import router as auth_router
from src.ui.api.middlewares.auth_middleware import AuthMiddleware

# 创建FastAPI实例
app = FastAPI(title="防汛应急报告生成系统API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加认证中间件
app.add_middleware(AuthMiddleware)

# 注册路由器
app.include_router(auth_router, prefix="/api/auth", tags=["用户认证"])
app.include_router(knowledge_base_router, prefix="/api/knowledge-base", tags=["知识库管理"])
app.include_router(search_router, prefix="/api/knowledge-base", tags=["搜索"])
app.include_router(extract_router, prefix="/extract", tags=["内容提取"])
app.include_router(report_router, prefix="/api/knowledge-base", tags=["报告管理"])
app.include_router(chat_router, prefix="/api/knowledge-base", tags=["聊天管理"])
app.include_router(system_router, prefix="/system", tags=["系统管理"])
app.include_router(index_router, prefix="/api/knowledge-base", tags=["索引管理"])

# 健康检查接口
@app.get("/health")
async def health_check():
    """API健康检查"""
    return {"status": "ok", "version": "1.0.0"} 