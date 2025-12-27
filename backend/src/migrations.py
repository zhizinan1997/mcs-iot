"""
数据库迁移模块

在后端启动时自动检查并执行必要的数据库 Schema 升级
确保用户升级 Docker 后数据库结构能自动更新
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


# 定义所有迁移
# 每个迁移是一个元组: (版本号, 描述, SQL语句列表)
MIGRATIONS: List[Tuple[int, str, List[str]]] = [
    (
        1,
        "添加 users.permissions 字段用于子账号权限管理",
        [
            """
            ALTER TABLE users 
            ADD COLUMN IF NOT EXISTS permissions TEXT DEFAULT '{}';
            """,
        ]
    ),
    # 后续迁移可以在这里添加
    # (
    #     2,
    #     "描述",
    #     ["SQL 语句"]
    # ),
]


async def ensure_migration_table(conn) -> None:
    """确保迁移记录表存在"""
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            description TEXT,
            applied_at TIMESTAMP DEFAULT NOW()
        );
    """)


async def get_applied_versions(conn) -> set:
    """获取已应用的迁移版本"""
    rows = await conn.fetch("SELECT version FROM schema_migrations")
    return {row['version'] for row in rows}


async def apply_migration(conn, version: int, description: str, sqls: List[str]) -> bool:
    """应用单个迁移"""
    try:
        async with conn.transaction():
            for sql in sqls:
                await conn.execute(sql)
            
            await conn.execute(
                "INSERT INTO schema_migrations (version, description) VALUES ($1, $2)",
                version, description
            )
        
        logger.info(f"✓ 迁移 #{version} 应用成功: {description}")
        return True
    except Exception as e:
        logger.error(f"✗ 迁移 #{version} 失败: {e}")
        return False


async def run_migrations(pool) -> None:
    """
    运行所有待执行的数据库迁移
    
    在后端启动时调用此函数，自动检查并应用新的 Schema 变更
    """
    if not pool:
        logger.warning("数据库连接池未初始化，跳过迁移")
        return
    
    async with pool.acquire() as conn:
        # 确保迁移表存在
        await ensure_migration_table(conn)
        
        # 获取已应用的版本
        applied = await get_applied_versions(conn)
        
        # 筛选待应用的迁移
        pending = [(v, d, s) for v, d, s in MIGRATIONS if v not in applied]
        
        if not pending:
            logger.info("数据库 Schema 已是最新版本")
            return
        
        logger.info(f"发现 {len(pending)} 个待执行的数据库迁移")
        
        # 按版本号排序执行
        pending.sort(key=lambda x: x[0])
        
        success_count = 0
        for version, description, sqls in pending:
            if await apply_migration(conn, version, description, sqls):
                success_count += 1
            else:
                logger.error(f"迁移在版本 #{version} 处停止")
                break
        
        logger.info(f"数据库迁移完成: {success_count}/{len(pending)} 个迁移已应用")
