"""
子账号管理 API
提供用户 CRUD 操作和权限管理
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from passlib.context import CryptContext
import json
from datetime import datetime

from .deps import get_db
from .auth import get_current_user, User

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 默认权限配置 (新用户默认只有基础权限)
DEFAULT_PERMISSIONS = {
    "dashboard": True,
    "devices": False,
    "instruments": False,
    "alarms": True,
    "logs": False,
    "ai": False,
    "license": False,
    "archive": False,
    "health": False,
    "config": False,
    "screen": True
}

# 权限标签映射 (用于前端显示)
PERMISSION_LABELS = {
    "dashboard": "仪表盘",
    "devices": "设备管理",
    "instruments": "仪表管理",
    "alarms": "报警记录",
    "logs": "服务器日志",
    "ai": "AI接口",
    "license": "授权管理",
    "archive": "数据归档",
    "health": "系统自检",
    "config": "系统配置",
    "screen": "可视化大屏"
}


class UserCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=32)
    password: str = Field(..., min_length=6, max_length=64)
    permissions: Dict[str, bool] = Field(default_factory=lambda: DEFAULT_PERMISSIONS.copy())
    email: Optional[str] = None
    phone: Optional[str] = None


class UserUpdate(BaseModel):
    permissions: Optional[Dict[str, bool]] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    new_password: str = Field(..., min_length=6, max_length=64)


class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    email: Optional[str]
    phone: Optional[str]
    permissions: Dict[str, bool]
    is_active: bool
    last_login: Optional[datetime]
    created_at: datetime


def require_admin(current_user: User = Depends(get_current_user)):
    """只允许管理员访问"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="只有管理员可以管理子账号"
        )
    return current_user


@router.get("")
async def list_users(
    db=Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取所有子账号列表"""
    async with db.acquire() as conn:
        rows = await conn.fetch("""
            SELECT id, username, role, email, phone, permissions, 
                   is_active, last_login, created_at
            FROM users
            WHERE role != 'admin'
            ORDER BY created_at DESC
        """)
        
        users = []
        for row in rows:
            permissions = {}
            if row["permissions"]:
                try:
                    permissions = json.loads(row["permissions"])
                except:
                    permissions = DEFAULT_PERMISSIONS.copy()
            else:
                permissions = DEFAULT_PERMISSIONS.copy()
            
            users.append({
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "email": row["email"],
                "phone": row["phone"],
                "permissions": permissions,
                "is_active": row["is_active"],
                "last_login": row["last_login"],
                "created_at": row["created_at"]
            })
        
        return {"users": users, "total": len(users)}


@router.get("/permissions")
async def get_permission_options(current_user: User = Depends(require_admin)):
    """获取可用的权限选项列表"""
    return {
        "permissions": [
            {"key": k, "label": v} 
            for k, v in PERMISSION_LABELS.items()
        ],
        "defaults": DEFAULT_PERMISSIONS
    }


@router.post("")
async def create_user(
    data: UserCreate,
    db=Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """创建子账号"""
    async with db.acquire() as conn:
        # 检查用户名是否已存在
        existing = await conn.fetchval(
            "SELECT id FROM users WHERE username = $1",
            data.username
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在"
            )
        
        # 创建用户
        password_hash = pwd_context.hash(data.password)
        permissions_json = json.dumps(data.permissions)
        
        row = await conn.fetchrow("""
            INSERT INTO users (username, password_hash, role, email, phone, permissions, is_active)
            VALUES ($1, $2, 'user', $3, $4, $5, TRUE)
            RETURNING id, username, role, email, phone, permissions, is_active, created_at
        """, data.username, password_hash, data.email, data.phone, permissions_json)
        
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "email": row["email"],
            "phone": row["phone"],
            "permissions": data.permissions,
            "is_active": row["is_active"],
            "created_at": row["created_at"],
            "message": "子账号创建成功"
        }


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db=Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """获取单个用户详情"""
    async with db.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT id, username, role, email, phone, permissions,
                   is_active, last_login, created_at
            FROM users WHERE id = $1
        """, user_id)
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        
        permissions = {}
        if row["permissions"]:
            try:
                permissions = json.loads(row["permissions"])
            except:
                permissions = DEFAULT_PERMISSIONS.copy()
        
        return {
            "id": row["id"],
            "username": row["username"],
            "role": row["role"],
            "email": row["email"],
            "phone": row["phone"],
            "permissions": permissions,
            "is_active": row["is_active"],
            "last_login": row["last_login"],
            "created_at": row["created_at"]
        }


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db=Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """更新子账号信息和权限"""
    async with db.acquire() as conn:
        # 检查用户存在且不是 admin
        row = await conn.fetchrow(
            "SELECT id, role FROM users WHERE id = $1",
            user_id
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        if row["role"] == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能修改管理员账号"
            )
        
        # 构建更新语句
        updates = []
        values = []
        idx = 1
        
        if data.permissions is not None:
            updates.append(f"permissions = ${idx}")
            values.append(json.dumps(data.permissions))
            idx += 1
        
        if data.email is not None:
            updates.append(f"email = ${idx}")
            values.append(data.email)
            idx += 1
        
        if data.phone is not None:
            updates.append(f"phone = ${idx}")
            values.append(data.phone)
            idx += 1
        
        if data.is_active is not None:
            updates.append(f"is_active = ${idx}")
            values.append(data.is_active)
            idx += 1
        
        if not updates:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="没有要更新的内容"
            )
        
        values.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = ${idx}"
        await conn.execute(query, *values)
        
        return {"message": "更新成功"}


@router.put("/{user_id}/password")
async def change_password(
    user_id: int,
    data: PasswordChange,
    db=Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """修改子账号密码"""
    async with db.acquire() as conn:
        # 检查用户存在且不是 admin
        row = await conn.fetchrow(
            "SELECT id, role FROM users WHERE id = $1",
            user_id
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        if row["role"] == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能修改管理员密码"
            )
        
        password_hash = pwd_context.hash(data.new_password)
        await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE id = $2",
            password_hash, user_id
        )
        
        return {"message": "密码修改成功"}


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db=Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """删除子账号"""
    async with db.acquire() as conn:
        # 检查用户存在且不是 admin
        row = await conn.fetchrow(
            "SELECT id, username, role FROM users WHERE id = $1",
            user_id
        )
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )
        if row["role"] == "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="不能删除管理员账号"
            )
        
        await conn.execute("DELETE FROM users WHERE id = $1", user_id)
        
        return {"message": f"用户 {row['username']} 已删除"}
