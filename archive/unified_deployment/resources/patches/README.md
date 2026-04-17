# Mem0 补丁

这个目录包含对 Mem0 的补丁，用于在不修改 `projects/mem0` 目录的情况下应用自定义修改。

## 补丁方式

**使用 Python 脚本替代 diff 补丁**，因为更可靠、更易维护。

## 主要补丁脚本

### 1. apply_server_fixes.py

修改 `server/main.py`，包含 7 个修复：

| 修复 | 说明 |
|------|------|
| Fix 1 | 添加 APIRouter 和 CORSMiddleware 导入 |
| Fix 2 | 替换 Postgres 配置为 Qdrant 配置 |
| Fix 3 | 添加 OPENAI_MODEL 和 CUSTOM_FACT_EXTRACTION_PROMPT |
| Fix 4 | 替换 pgvector 为 qdrant |
| Fix 5 | 添加 CORS 中间件和 API router |
| Fix 6 | 替换 @app 装饰器为 @api_router |
| Fix 7 | 添加路由器注册 |

### 2. apply_memory_fixes.py

修复 `mem0/memory/main.py` 中的 bugs，包含 15 个修复：

| 修复 | 说明 |
|------|------|
| Fix 0 | 确保 custom_fact_extraction_prompt 包含 "json" 关键字 |
| Fix 1-2 | JSON 解析安全访问 `.get("facts", [])` |
| Fix 3-4 | 同步版本 temp_uuid_mapping 安全访问 |
| Fix 5 | 同步版本 vector_store.get None 检查 |
| Fix 6-7 | 异步版本 temp_uuid_mapping 安全访问 |
| Fix 8 | 异步版本 vector_store.get None 检查 |
| Fix 9-13 | payload 安全访问 `.get()` |

## Dockerfile 使用

```dockerfile
COPY deployment/mem0/patches/apply_server_fixes.py /tmp/apply_server_fixes.py
COPY deployment/mem0/patches/apply_memory_fixes.py /tmp/apply_memory_fixes.py
RUN echo "Applying server fixes..." && \
    python3 /tmp/apply_server_fixes.py /app/main.py && \
    echo "Applying memory fixes..." && \
    MEM0_PATH=$(python3 -c "import mem0.memory.main; import os; print(os.path.dirname(mem0.memory.main.__file__))") && \
    python3 /tmp/apply_memory_fixes.py "$MEM0_PATH/main.py" && \
    echo "All fixes applied successfully!"
```

## 本地测试

```bash
cd /path/to/CozyMem0

# 测试 server 补丁
cp projects/mem0/server/main.py /tmp/test_server.py
python3 deployment/mem0/patches/apply_server_fixes.py /tmp/test_server.py
python3 -m py_compile /tmp/test_server.py

# 测试 memory 补丁
cp projects/mem0/mem0/memory/main.py /tmp/test_memory.py
python3 deployment/mem0/patches/apply_memory_fixes.py /tmp/test_memory.py
python3 -m py_compile /tmp/test_memory.py
```

## 其他补丁文件（备用/历史）

这些是旧的 diff 格式补丁，已被 Python 脚本替代：

| 文件 | 说明 | 状态 |
|------|------|------|
| all-in-one.patch | 合并所有 server 修改 | 已弃用，使用 apply_server_fixes.py |
| cors.patch | CORS 支持 | 已合并 |
| switch-to-qdrant.patch | 切换到 Qdrant | 已合并 |
| qdrant-only.patch | 仅 Qdrant 配置 | 已合并 |
| add-api-prefix.patch | 添加 API 前缀 | 已合并 |
| chinese-language-support.patch | 中文语言支持 | 已合并 |
| web-ui-api-prefix.patch | Web UI API 前缀 | 已合并 |

## 注意事项

1. **不要直接修改 `projects/mem0` 目录**
2. **Python 脚本比 diff 补丁更可靠**：模式匹配而非行号
3. **测试补丁**：在提交前在本地测试
4. **验证语法**：确保修改后的文件语法正确
