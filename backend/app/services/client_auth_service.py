"""
客户端认证服务
"""
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from jose import jwt, JWTError
from fastapi import HTTPException

from ..database.models.client_models import ClientUser
from ..database.connection import get_database_manager

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT配置
SECRET_KEY = "your-secret-key-here"  # 与主认证模块保持一致
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8小时，避免频繁过期


class ClientAuthService:
    """客户端认证服务"""
    
    def __init__(self):
        self.db_manager = get_database_manager()
    
    def get_password_hash(self, password: str) -> str:
        """生成密码哈希"""
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """验证密码"""
        return pwd_context.verify(plain_password, hashed_password)
    
    def create_access_token(self, data: dict) -> str:
        """创建访问令牌"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """验证令牌"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str = payload.get("sub")
            if username is None:
                raise HTTPException(status_code=401, detail="无效的认证令牌")

            # 检查是否为系统用户
            user_type = payload.get("user_type")
            if user_type == "system":
                # 系统用户，直接返回payload
                return payload

            return payload
        except JWTError:
            raise HTTPException(status_code=401, detail="无效的认证令牌")
    
    def authenticate_user(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        """验证用户凭据"""
        with self.db_manager.get_session('client') as session:
            user = session.query(ClientUser).filter(
                ClientUser.username == username,
                ClientUser.is_active == True
            ).first()

            if not user:
                return None

            if not self.verify_password(password, user.password_hash):
                return None

            # 更新最后访问时间
            user.last_access_at = datetime.utcnow()
            session.commit()

            # 返回用户数据字典而不是对象
            return {
                'id': user.id,
                'client_id': user.client_id,
                'username': user.username,
                'nickname': user.nickname,
                'quota_limit': user.quota_limit,
                'quota_used': user.quota_used,
                'is_active': user.is_active,
                'last_access_at': user.last_access_at,
                'created_at': user.created_at,
                'updated_at': user.updated_at
            }
    
    def create_user(self, username: str, password: str, nickname: str = None, 
                   quota_limit: int = 50) -> ClientUser:
        """创建新用户"""
        with self.db_manager.get_session('client') as session:
            # 检查用户名是否已存在
            existing_user = session.query(ClientUser).filter(
                ClientUser.username == username
            ).first()
            
            if existing_user:
                raise HTTPException(status_code=400, detail="用户名已存在")
            
            # 创建新用户
            client_id = str(uuid.uuid4())
            password_hash = self.get_password_hash(password)
            
            new_user = ClientUser(
                client_id=client_id,
                username=username,
                password_hash=password_hash,
                nickname=nickname or username,
                quota_limit=quota_limit,
                quota_used=0,
                is_active=True
            )
            
            session.add(new_user)
            session.commit()
            session.refresh(new_user)

            # 创建一个新的用户对象，避免会话绑定问题
            user_data = {
                'id': new_user.id,
                'client_id': new_user.client_id,
                'username': new_user.username,
                'nickname': new_user.nickname,
                'quota_limit': new_user.quota_limit,
                'quota_used': new_user.quota_used,
                'is_active': new_user.is_active,
                'created_at': new_user.created_at,
                'updated_at': new_user.updated_at
            }

            # 创建一个分离的用户对象
            detached_user = ClientUser(**user_data)
            return detached_user
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """根据用户名获取用户"""
        with self.db_manager.get_session('client') as session:
            user = session.query(ClientUser).filter(
                ClientUser.username == username,
                ClientUser.is_active == True
            ).first()

            if not user:
                return None

            # 返回用户数据字典
            return {
                'id': user.id,
                'client_id': user.client_id,
                'username': user.username,
                'nickname': user.nickname,
                'quota_limit': user.quota_limit,
                'quota_used': user.quota_used,
                'is_active': user.is_active,
                'last_access_at': user.last_access_at,
                'created_at': user.created_at,
                'updated_at': user.updated_at
            }
    
    def get_user_by_client_id(self, client_id: str) -> Optional[ClientUser]:
        """根据客户端ID获取用户"""
        with self.db_manager.get_session('client') as session:
            return session.query(ClientUser).filter(
                ClientUser.client_id == client_id,
                ClientUser.is_active == True
            ).first()
    
    def update_user_quota(self, username: str, quota_used: int = None, 
                         quota_limit: int = None) -> bool:
        """更新用户配额"""
        with self.db_manager.get_session('client') as session:
            user = session.query(ClientUser).filter(
                ClientUser.username == username,
                ClientUser.is_active == True
            ).first()
            
            if not user:
                return False
            
            if quota_used is not None:
                user.quota_used = quota_used
            
            if quota_limit is not None:
                user.quota_limit = quota_limit
            
            session.commit()
            return True
    
    def check_quota(self, username: str) -> Dict[str, Any]:
        """检查用户配额"""
        with self.db_manager.get_session('client') as session:
            user = session.query(ClientUser).filter(
                ClientUser.username == username,
                ClientUser.is_active == True
            ).first()

            if not user:
                raise HTTPException(status_code=404, detail="用户不存在")

            # 检查是否需要重置配额（每日重置）
            today = datetime.now().date()
            if user.quota_reset_date != today:
                user.quota_used = 0
                user.quota_reset_date = today
                session.commit()

            return {
                'quota_limit': user.quota_limit,
                'quota_used': user.quota_used,
                'quota_remaining': user.quota_limit - user.quota_used,
                'quota_reset_date': user.quota_reset_date.isoformat() if user.quota_reset_date else None
            }
    
    def increment_quota_usage(self, username: str, amount: int = 1) -> bool:
        """增加配额使用量"""
        with self.db_manager.get_session('client') as session:
            user = session.query(ClientUser).filter(
                ClientUser.username == username,
                ClientUser.is_active == True
            ).first()
            
            if not user:
                return False
            
            # 检查配额
            quota_info = self.check_quota(username)
            if quota_info['quota_remaining'] < amount:
                raise HTTPException(status_code=429, detail="配额不足")
            
            user.quota_used += amount
            session.commit()
            return True


# 全局实例
_client_auth_service = None

def get_client_auth_service() -> ClientAuthService:
    """获取客户端认证服务实例"""
    global _client_auth_service
    if _client_auth_service is None:
        _client_auth_service = ClientAuthService()
    return _client_auth_service
