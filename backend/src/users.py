"""
MCS-IOT 用户与子账号管理模块 (User & Permissions Management)

该文件负责系统内的多用户管理及其细粒度的功能权限分配。
主要功能包括：
1. 实现子账号的增删改查 (CRUD) 接口，并确保只有管理员 (Admin) 权限可操作。
2. 定义系统内部各模块的权限控制点（Dashboard, 设备, 报警, AI 等），支持管理员为不同子账号分配不同的可视及操作范围。
3. 维护默认权限配置，简化新用户的初始化流程。
4. 提供密码修改及账号启用/禁用功能。

结构：
- DEFAULT_PERMISSIONS & PERMISSION_LABELS: 权限系统的配置常量。
- User Models: UserCreate, UserUpdate, UserResponse 对应不同场景的数据交换格式。
- Auth Logic: require_admin 装饰器，实现强权限控制。
- API Handlers: list_users, create_user 等管理逻辑接口。
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


# =============================================================================
# 管理员账号密码修改 (Admin Password Management)
# 注意: 此路由必须在 /{user_id} 路由之前定义，否则会被错误匹配
# =============================================================================

class AdminPasswordChange(BaseModel):
    """管理员密码修改请求"""
    current_password: str = Field(..., min_length=1, description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=64, description="新密码")


async def _update_deploy_info_password(new_password: str):
    """
    更新 DEPLOY_INFO.md 文件中的管理员密码记录
    
    文件中的格式:
    ### 后台管理员
    | 项目 | 值 |
    |------|-----|
    | 登录地址 | https://... |
    | 用户名 | admin |
    | 密码 | `admin123` |
    """
    import os
    import re
    import logging
    
    logger = logging.getLogger(__name__)
    
    possible_paths = [
        "/app/scripts/DEPLOY_INFO.md",
        "/opt/mcs-iot/scripts/DEPLOY_INFO.md",
        "./scripts/DEPLOY_INFO.md"
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 匹配 ### 后台管理员 区块中的密码行
                # 格式: | 密码 | `xxx` |
                pattern = r'(### 后台管理员.*?\| 密码 \| )`[^`]+`( \|)'
                replacement = rf'\1`{new_password}`\2'
                updated_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
                
                if updated_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(updated_content)
                    logger.info(f"Updated admin password in {path}")
                else:
                    logger.warning(f"Password pattern not matched in {path}")
                
                break
            except Exception as e:
                logger.warning(f"Failed to update DEPLOY_INFO.md: {e}")


@router.put("/admin/password")
async def change_admin_password(
    data: AdminPasswordChange,
    db=Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    修改管理员密码
    
    - 需要验证当前密码
    - 成功后同步更新 DEPLOY_INFO.md 文件中的密码记录
    """
    async with db.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, password_hash FROM users WHERE username = 'admin'"
        )
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="管理员账号不存在"
            )
        
        if not pwd_context.verify(data.current_password, row["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="当前密码错误"
            )
        
        new_hash = pwd_context.hash(data.new_password)
        await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE username = 'admin'",
            new_hash
        )
        
        await _update_deploy_info_password(data.new_password)
        
        return {"message": "管理员密码修改成功"}


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
