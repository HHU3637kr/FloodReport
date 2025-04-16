from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional
import re

class UserCreate(BaseModel):
    """用户创建模型"""
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    @validator('username')
    def username_alphanumeric(cls, v):
        if not re.match(r'^[a-zA-Z0-9_]+$', v):
            raise ValueError('用户名只能包含字母、数字和下划线')
        return v
    
    @validator('password')
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError('密码长度至少为6个字符')
        return v

class UserLogin(BaseModel):
    """用户登录模型"""
    username: str
    password: str
    remember_me: bool = False

class UserResponse(BaseModel):
    """用户响应模型"""
    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True

class TokenResponse(BaseModel):
    """令牌响应模型"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

class UserUpdate(BaseModel):
    """用户信息更新模型"""
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    
    @validator('email')
    def email_not_empty(cls, v):
        if v == "":
            raise ValueError('邮箱不能为空')
        return v
    
    @validator('full_name')
    def name_not_empty(cls, v):
        if v == "":
            return None
        return v

class PasswordUpdate(BaseModel):
    """密码更新模型"""
    current_password: str
    new_password: str
    
    @validator('new_password')
    def password_min_length(cls, v):
        if len(v) < 6:
            raise ValueError('新密码长度至少为6个字符')
        return v 