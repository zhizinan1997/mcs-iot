"""
MCS-IOT 认证与授权模块 (Authentication & Authorization)

该文件负责用户的登录验证、JWT 令牌签发及基于角色的权限管理。
主要功能包括：
1. 基于 OAuth2PasswordBearer 的身份验证流程。
2. 使用 JWT (JSON Web Tokens) 进行会话维持，支持过期自动失效。
3. 使用 bcrypt 对用户密码进行强哈希存储与校验。
4. 定义系统角色（如 admin）及其对应的默认操作权限。
5. 提供登录接口、获取当前用户信息接口，并实现非法访问过滤。

结构：
- Security Utils: 包含令牌创建、密码校验、当前用户解析等核心安全逻辑。
- Models: Token, User 等认证相关数据模型。
- login: 用户登录与认证逻辑，包括账号状态校验、权限装载。
- get_me: 获取当前登录者详细信息的受保护路由。
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from jose import jwt, JWTError
from passlib.context import CryptContext
from datetime import datetime, timedelta
from typing import Dict, Optional
import os
import json

from .deps import get_db

router = APIRouter()

# Security
SECRET_KEY = os.getenv("JWT_SECRET", "dev-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# 默认权限 (admin 拥有全部权限)
DEFAULT_ADMIN_PERMISSIONS = {
    "dashboard": True,
    "devices": True,
    "instruments": True,
    "alarms": True,
    "logs": True,
    "ai": True,
    "license": True,
    "archive": True,
    "health": True,
    "config": True,
    "screen": True
}


class Token(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class User(BaseModel):
    username: str
    role: str
    permissions: Dict[str, bool] = {}


class UserResponse(BaseModel):
    username: str
    role: str
    permissions: Dict[str, bool] = {}


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    """从 JWT token 解析当前用户信息"""
    from .deps import db_pool
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # 从数据库获取用户最新信息
    if db_pool:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT username, role, permissions, is_active FROM users WHERE username = $1",
                username
            )
            if row:
                if not row["is_active"]:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="账号已被禁用"
                    )
                
                permissions = {}
                if row["role"] == "admin":
                    permissions = DEFAULT_ADMIN_PERMISSIONS.copy()
                elif row["permissions"]:
                    try:
                        permissions = json.loads(row["permissions"])
                    except:
                        permissions = {}
                
                return User(
                    username=row["username"],
                    role=row["role"],
                    permissions=permissions
                )
    
    raise credentials_exception


@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db=Depends(get_db)):
    """
    用户登录接口
    
    安全说明:
    - 从数据库查询用户，使用参数化查询防SQL注入
    - 密码使用bcrypt哈希存储
    - 输入已自动转义，防止XSS
    """
    # 输入基础验证（防止恶意输入）
    username = form_data.username.strip()
    password = form_data.password
    
    # 用户名长度检查
    if len(username) < 1 or len(username) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名格式不正确"
        )
    
    # 从数据库查找用户
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT username, password_hash, role, permissions, is_active FROM users WHERE username = $1",
            username
        )
    
    if not row:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="账号不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not row["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账号已被禁用"
        )
    
    # 验证密码
    if not verify_password(password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 更新最后登录时间
    async with db.acquire() as conn:
        await conn.execute(
            "UPDATE users SET last_login = NOW() WHERE username = $1",
            username
        )
    
    # 解析权限
    permissions = {}
    if row["role"] == "admin":
        permissions = DEFAULT_ADMIN_PERMISSIONS.copy()
    elif row["permissions"]:
        try:
            permissions = json.loads(row["permissions"])
        except:
            permissions = {}
    
    access_token = create_access_token(data={
        "sub": row["username"],
        "role": row["role"],
        "permissions": permissions
    })
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_HOURS * 3600
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户信息"""
    return UserResponse(
        username=current_user.username,
        role=current_user.role,
        permissions=current_user.permissions
    )
