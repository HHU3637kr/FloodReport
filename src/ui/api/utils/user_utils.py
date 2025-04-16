import os
import json
import uuid
import bcrypt
import jwt
from datetime import datetime, timedelta
from loguru import logger
from typing import Dict, Optional, List

# JWT配置
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24小时

class UserManager:
    """用户管理器"""
    
    def __init__(self):
        """初始化用户管理器"""
        # 用户数据存储路径
        self.users_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.abspath(__file__)))))),
            "data", "users"
        )
        # 确保用户目录存在
        os.makedirs(self.users_dir, exist_ok=True)
        self.users_file = os.path.join(self.users_dir, "users.json")
        
        # 如果用户文件不存在，创建一个空的用户列表
        if not os.path.exists(self.users_file):
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump([], f)
                
        # 如果没有管理员用户，创建一个默认管理员
        self._create_default_admin()
    
    def _create_default_admin(self):
        """创建默认管理员用户"""
        try:
            users = self._load_users()
            if not any(u.get("username") == "admin" for u in users):
                admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
                admin_user = {
                    "id": str(uuid.uuid4()),
                    "username": "admin",
                    "email": "admin@floodreport.com",
                    "full_name": "系统管理员",
                    "password": self._hash_password(admin_password),
                    "is_admin": True,
                    "is_active": True,
                    "created_at": datetime.now().isoformat()
                }
                users.append(admin_user)
                self._save_users(users)
                logger.info("已创建默认管理员用户")
        except Exception as e:
            logger.error(f"创建默认管理员用户失败: {str(e)}")
    
    def _load_users(self) -> List[Dict]:
        """加载所有用户"""
        try:
            with open(self.users_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载用户数据失败: {str(e)}")
            return []
    
    def _save_users(self, users: List[Dict]):
        """保存所有用户"""
        try:
            with open(self.users_file, "w", encoding="utf-8") as f:
                json.dump(users, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存用户数据失败: {str(e)}")
    
    def _hash_password(self, password: str) -> str:
        """加密密码"""
        try:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
            return hashed.decode('utf-8')
        except Exception as e:
            logger.error(f"密码加密失败: {str(e)}")
            # 返回一个无法验证的哈希值，以防止系统崩溃
            return "$2b$12$invalid-hash-for-error"
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        try:
            return bcrypt.checkpw(
                plain_password.encode('utf-8'), 
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"密码验证失败: {str(e)}")
            return False
    
    def create_user(self, username: str, email: str, password: str, full_name: Optional[str] = None) -> Dict:
        """创建新用户"""
        users = self._load_users()
        
        # 检查用户名是否已存在
        if any(u.get("username") == username for u in users):
            raise ValueError("用户名已存在")
        
        # 检查邮箱是否已存在
        if any(u.get("email") == email for u in users):
            raise ValueError("邮箱已存在")
        
        # 创建新用户
        new_user = {
            "id": str(uuid.uuid4()),
            "username": username,
            "email": email,
            "full_name": full_name,
            "password": self._hash_password(password),
            "is_admin": False,
            "is_active": True,
            "created_at": datetime.now().isoformat()
        }
        
        users.append(new_user)
        self._save_users(users)
        
        # 返回用户信息（不包含密码）
        user_response = new_user.copy()
        user_response.pop("password")
        return user_response
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict]:
        """验证用户凭据"""
        users = self._load_users()
        
        # 查找用户
        user = next((u for u in users if u.get("username") == username and u.get("is_active", True)), None)
        if not user:
            return None
        
        # 验证密码
        if not self._verify_password(password, user.get("password", "")):
            return None
        
        # 返回用户信息（不包含密码）
        user_response = user.copy()
        user_response.pop("password")
        return user_response
    
    def get_user(self, user_id: str) -> Optional[Dict]:
        """通过ID获取用户信息"""
        users = self._load_users()
        user = next((u for u in users if u.get("id") == user_id), None)
        
        if user:
            user_response = user.copy()
            user_response.pop("password", None)
            return user_response
        
        return None

    def update_user(self, user_id: str, email: Optional[str] = None, full_name: Optional[str] = None) -> Optional[Dict]:
        """更新用户信息"""
        users = self._load_users()
        
        # 找到用户
        user_index = next((i for i, u in enumerate(users) if u.get("id") == user_id), None)
        if user_index is None:
            logger.error(f"更新用户信息失败: 用户ID {user_id} 不存在")
            return None
        
        # 如果更新邮箱，检查是否已被其他用户使用
        if email is not None and email != users[user_index].get("email"):
            if any(u.get("email") == email and u.get("id") != user_id for u in users):
                raise ValueError("邮箱已被其他用户使用")
            users[user_index]["email"] = email
        
        # 更新全名
        if full_name is not None:
            users[user_index]["full_name"] = full_name
        
        # 更新时间戳
        users[user_index]["updated_at"] = datetime.now().isoformat()
        
        # 保存更改
        self._save_users(users)
        
        # 返回更新后的用户信息
        user_response = users[user_index].copy()
        user_response.pop("password")
        return user_response

    def update_password(self, user_id: str, current_password: str, new_password: str) -> bool:
        """更新用户密码"""
        users = self._load_users()
        
        # 找到用户
        user_index = next((i for i, u in enumerate(users) if u.get("id") == user_id), None)
        if user_index is None:
            logger.error(f"更新密码失败: 用户ID {user_id} 不存在")
            return False
        
        # 验证当前密码
        if not self._verify_password(current_password, users[user_index].get("password", "")):
            logger.warning(f"更新密码失败: 当前密码验证失败 (用户ID: {user_id})")
            return False
        
        # 更新密码
        users[user_index]["password"] = self._hash_password(new_password)
        users[user_index]["updated_at"] = datetime.now().isoformat()
        
        # 保存更改
        self._save_users(users)
        
        logger.info(f"用户ID {user_id} 密码已更新")
        return True

    def create_access_token(self, data: Dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌"""
        try:
            to_encode = data.copy()
            
            # 设置过期时间
            if expires_delta:
                expire = datetime.utcnow() + expires_delta
            else:
                expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
            to_encode.update({"exp": expire})
            
            # 使用PyJWT创建令牌
            encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
            return encoded_jwt
        except Exception as e:
            logger.error(f"创建访问令牌失败: {str(e)}")
            # 返回一个明显无效的令牌，以便前端容易识别
            return "invalid-token-error"
    
    def get_user_from_token(self, token: str) -> Optional[Dict]:
        """从令牌获取用户信息"""
        try:
            # 解码JWT令牌
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_id = payload.get("sub")
            if user_id is None:
                return None
            return self.get_user(user_id)
        except jwt.PyJWTError as e:
            logger.error(f"令牌验证失败: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"从令牌获取用户信息失败: {str(e)}")
            return None

# 初始化用户管理器
user_manager = UserManager() 