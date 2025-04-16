from fastapi import Request, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from src.ui.api.utils.user_utils import user_manager
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """从令牌中获取当前用户"""
    if not token:
        logger.warning("API请求未提供认证令牌")
        raise HTTPException(
            status_code=401,
            detail="未提供认证令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        user = user_manager.get_user_from_token(token)
        if not user:
            logger.warning(f"无效或过期的令牌: {token[:10]}...")
            raise HTTPException(
                status_code=401,
                detail="无效令牌或令牌已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user
    except Exception as e:
        logger.error(f"验证用户令牌时发生错误: {str(e)}")
        raise HTTPException(
            status_code=401,
            detail="认证过程中发生错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_optional_user(token: Optional[str] = Depends(oauth2_scheme)):
    """获取可选的当前用户（用于非强制认证的路由）"""
    if not token:
        return None
    
    try:
        return user_manager.get_user_from_token(token)
    except Exception as e:
        logger.error(f"获取可选用户时发生错误: {str(e)}")
        return None

class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件类"""
    
    async def dispatch(self, request: Request, call_next):
        """处理请求"""
        try:
            # 获取认证头
            auth_header = request.headers.get("Authorization")
            
            # 不处理登录和公共API
            if request.url.path in ["/api/auth/login", "/api/auth/register", "/health"]:
                return await call_next(request)
            
            # 处理认证
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]
                user = user_manager.get_user_from_token(token)
                if user:
                    # 将用户信息添加到请求状态
                    request.state.user = user
                    return await call_next(request)
            
            # 继续处理请求，让路由处理程序决定是否需要认证
            return await call_next(request)
        except Exception as e:
            logger.error(f"认证中间件处理请求时发生错误: {str(e)}")
            # 继续处理请求，让路由处理程序处理错误
            return await call_next(request) 