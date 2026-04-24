# Database Migration Guide

CozyMemory 使用 Alembic 管理 `cozymemory` 平台库（PostgreSQL）的 schema 迁移。
Cognee / Memobase 各自管理各自的数据库 schema，不在此管辖范围。

## 日常操作

```bash
# 查看当前 migration 版本
alembic current

# 查看待执行的 migration
alembic history --verbose

# 升级到最新版本（部署时执行）
alembic upgrade head

# 升级到指定版本
alembic upgrade <revision>
```

## 创建新 Migration

```bash
# 自动生成（对比 models 与数据库差异）
alembic revision --autogenerate -m "add_xxx_table"

# 手动编写（空模板）
alembic revision -m "manual_data_migration"
```

生成后检查 `alembic/versions/<hash>_xxx.py`，确认 `upgrade()` 和 `downgrade()` 都正确。

## 回滚（Rollback）

```bash
# 回滚一步
alembic downgrade -1

# 回滚到指定版本
alembic downgrade <revision>

# 回滚到初始状态（危险！清空所有表）
alembic downgrade base
```

## 生产回滚流程

1. **备份数据库**
   ```bash
   pg_dump -h localhost -p 5433 -U cozymemory_user cozymemory > backup_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **确认当前版本和目标版本**
   ```bash
   alembic current    # e.g. b2c3d4e5f6a7 (head)
   alembic history    # 找到要回滚到的版本
   ```

3. **执行回滚**
   ```bash
   alembic downgrade <target_revision>
   ```

4. **回滚代码**（如果 migration 与代码变更耦合）
   ```bash
   git revert <commit>
   # 或回退到指定 tag
   git checkout v0.1.0
   ```

5. **重启服务**
   ```bash
   cd base_runtime
   sudo docker compose -f docker-compose.1panel.yml up -d --force-recreate cozymemory-api
   ```

## 当前 Migration 历史

| Revision | Description |
|----------|-------------|
| `e8718d7f606c` | Initial: organizations, developers, apps, api_keys, external_users |
| `a1b2c3d4e5f6` | App datasets mapping |
| `b2c3d4e5f6a7` | API usage tracking |

## 注意事项

- `alembic.ini` 中的 `sqlalchemy.url` 应指向 host 端口 5433（本机直连），不是容器内 5432
- 生产环境回滚前必须先备份
- 涉及 `DROP COLUMN` / `DROP TABLE` 的 downgrade 会丢失数据，需提前确认
- Migration 文件已提交 git，不要手动修改已执行的 migration
