from fastapi import APIRouter, HTTPException, Depends, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from loguru import logger
from src.ui.api.models.user import UserCreate, UserLogin, TokenResponse, UserResponse, UserUpdate, PasswordUpdate
from src.ui.api.utils.user_utils import user_manager
from src.ui.api.middlewares.auth_middleware import get_current_user

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """注册新用户"""
    try:
        logger.info(f"尝试注册新用户: {user_data.username}, 邮箱: {user_data.email}")
        user = user_manager.create_user(
            username=user_data.username,
            email=user_data.email,
            password=user_data.password,
            full_name=user_data.full_name
        )
        logger.info(f"用户注册成功: {user_data.username}")
        return user
    except ValueError as e:
        logger.error(f"用户注册失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"用户注册失败（系统错误）: {str(e)}")
        raise HTTPException(status_code=500, detail="注册过程中发生系统错误")

@router.post("/login", status_code=status.HTTP_200_OK)
async def login(response: Response, form_data: OAuth2PasswordRequestForm = Depends()):
    """用户登录"""
    try:
        logger.info(f"用户登录尝试: {form_data.username}")
        
        # 验证用户凭据
        user = user_manager.authenticate_user(form_data.username, form_data.password)
        if not user:
            logger.warning(f"登录失败: 用户名或密码错误 (用户名: {form_data.username})")
            raise HTTPException(
                status_code=401,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # 创建访问令牌
        access_token = user_manager.create_access_token(
            data={"sub": user["id"]}
        )
        
        # 检查令牌是否有效
        if access_token == "invalid-token-error":
            logger.error(f"生成访问令牌失败: {form_data.username}")
            raise HTTPException(status_code=500, detail="登录过程中发生系统错误")
        
        logger.info(f"用户 {form_data.username} 登录成功")
        
        # 返回登录响应
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录时发生错误: {str(e)}")
        raise HTTPException(status_code=500, detail="登录过程中发生系统错误")

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """获取当前用户信息"""
    logger.info(f"获取用户信息: {current_user.get('username')}")
    return current_user

@router.put("/me", response_model=UserResponse)
async def update_user_info(user_data: UserUpdate, current_user: dict = Depends(get_current_user)):
    """修改当前用户个人信息"""
    try:
        logger.info(f"更新用户信息: {current_user.get('username')}")
        updated_user = user_manager.update_user(
            user_id=current_user.get("id"),
            email=user_data.email,
            full_name=user_data.full_name
        )
        if not updated_user:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        logger.info(f"用户信息更新成功: {current_user.get('username')}")
        return updated_user
    except ValueError as e:
        logger.error(f"用户信息更新失败: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"用户信息更新失败（系统错误）: {str(e)}")
        raise HTTPException(status_code=500, detail="更新过程中发生系统错误")

@router.put("/me/password", status_code=status.HTTP_200_OK)
async def change_password(password_data: PasswordUpdate, current_user: dict = Depends(get_current_user)):
    """修改当前用户密码"""
    try:
        logger.info(f"更新用户密码: {current_user.get('username')}")
        success = user_manager.update_password(
            user_id=current_user.get("id"),
            current_password=password_data.current_password,
            new_password=password_data.new_password
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="当前密码错误")
        
        logger.info(f"用户密码更新成功: {current_user.get('username')}")
        return {"message": "密码更新成功"}
    except Exception as e:
        logger.error(f"用户密码更新失败: {str(e)}")
        raise HTTPException(status_code=500, detail="密码更新过程中发生系统错误")

@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout():
    """用户退出登录
    
    注意：由于使用JWT令牌，服务器端不需要特殊处理，客户端只需要删除本地存储的令牌即可
    """
    return {"message": "退出登录成功"} 