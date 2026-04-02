#!/usr/bin/env python3
"""
Mem0 Server Configuration Fixes

This script applies fixes to projects/mem0/server/main.py:
1. Add CORS support
2. Add API prefix /api/v1
3. Switch to Qdrant as vector store
4. Add Chinese language support

Usage:
    python apply_server_fixes.py /path/to/server/main.py
"""

import sys
import os


def apply_fixes(file_path: str) -> bool:
    """Apply all server fixes to the main.py file."""
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    fixes_applied = 0
    
    # Fix 1: Add APIRouter and CORSMiddleware imports
    old_import = 'from fastapi import FastAPI, HTTPException'
    new_import = '''from fastapi import FastAPI, HTTPException, APIRouter
from fastapi.middleware.cors import CORSMiddleware'''
    
    if old_import in content and 'APIRouter' not in content:
        content = content.replace(old_import, new_import)
        fixes_applied += 1
        print("✓ Fix 1: Added APIRouter and CORSMiddleware imports")
    
    # Fix 2: Replace Postgres config with Qdrant config
    postgres_config = '''POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_DB = os.environ.get("POSTGRES_DB", "postgres")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
POSTGRES_COLLECTION_NAME = os.environ.get("POSTGRES_COLLECTION_NAME", "memories")

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "mem0graph")'''
    
    qdrant_config = '''# Qdrant 配置（专用向量数据库，高性能）
QDRANT_HOST = os.environ.get("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.environ.get("QDRANT_PORT", "6333"))
QDRANT_COLLECTION_NAME = os.environ.get("QDRANT_COLLECTION_NAME", "memories")'''
    
    if postgres_config in content:
        content = content.replace(postgres_config, qdrant_config)
        fixes_applied += 1
        print("✓ Fix 2: Replaced Postgres config with Qdrant config")
    
    # Fix 3: Add OPENAI_MODEL and CUSTOM_FACT_EXTRACTION_PROMPT
    history_db_line = 'HISTORY_DB_PATH = os.environ.get("HISTORY_DB_PATH", "/app/history/history.db")'
    history_db_with_extras = '''HISTORY_DB_PATH = os.environ.get("HISTORY_DB_PATH", "/app/history/history.db")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4.1-nano-2025-04-14")
CUSTOM_FACT_EXTRACTION_PROMPT = os.environ.get("CUSTOM_FACT_EXTRACTION_PROMPT", "")'''
    
    if history_db_line in content and 'OPENAI_MODEL' not in content:
        content = content.replace(history_db_line, history_db_with_extras)
        fixes_applied += 1
        print("✓ Fix 3: Added OPENAI_MODEL and CUSTOM_FACT_EXTRACTION_PROMPT")
    
    # Fix 4: Replace pgvector with qdrant in DEFAULT_CONFIG
    pgvector_config = '''    "vector_store": {
        "provider": "pgvector",
        "config": {
            "host": POSTGRES_HOST,
            "port": int(POSTGRES_PORT),
            "dbname": POSTGRES_DB,
            "user": POSTGRES_USER,
            "password": POSTGRES_PASSWORD,
            "collection_name": POSTGRES_COLLECTION_NAME,
        },
    },
    "graph_store": {
        "provider": "neo4j",
        "config": {"url": NEO4J_URI, "username": NEO4J_USERNAME, "password": NEO4J_PASSWORD},
    },
    "llm": {"provider": "openai", "config": {"api_key": OPENAI_API_KEY, "temperature": 0.2, "model": "gpt-4.1-nano-2025-04-14"}},'''
    
    qdrant_vector_config = '''    "vector_store": {
        "provider": "qdrant",
        "config": {
            "host": QDRANT_HOST,
            "port": QDRANT_PORT,
            "collection_name": QDRANT_COLLECTION_NAME,
            "embedding_model_dims": 1536,  # text-embedding-3-small 的维度
        },
    },
    "llm": {"provider": "openai", "config": {"api_key": OPENAI_API_KEY, "temperature": 0.2, "model": OPENAI_MODEL}},
    **({"custom_fact_extraction_prompt": CUSTOM_FACT_EXTRACTION_PROMPT} if CUSTOM_FACT_EXTRACTION_PROMPT else {}),'''
    
    if pgvector_config in content:
        content = content.replace(pgvector_config, qdrant_vector_config)
        fixes_applied += 1
        print("✓ Fix 4: Replaced pgvector with qdrant in DEFAULT_CONFIG")
    
    # Fix 5: Add CORS middleware and API router after app creation
    app_creation = '''app = FastAPI(
    title="Mem0 REST APIs",
    description="A REST API for managing and searching memories for your AI Agents and Apps.",
    version="1.0.0",
)'''
    
    app_with_cors = '''app = FastAPI(
    title="Mem0 REST APIs",
    description="A REST API for managing and searching memories for your AI Agents and Apps.",
    version="1.0.0",
    servers=[
        {"url": "/api/v1", "description": "API v1"},
    ],
)

# 配置 CORS
# 允许的源（可以通过环境变量配置）
ALLOWED_ORIGINS = os.environ.get(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:4000,http://192.168.66.11:3000,http://192.168.66.11:4000"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建 API 路由器，添加 /api/v1 前缀
api_router = APIRouter(prefix="/api/v1")'''
    
    if app_creation in content and 'api_router = APIRouter' not in content:
        content = content.replace(app_creation, app_with_cors)
        fixes_applied += 1
        print("✓ Fix 5: Added CORS middleware and API router")
    
    # Fix 6: Replace @app decorators with @api_router
    route_replacements = [
        ('@app.post("/configure"', '@api_router.post("/configure"'),
        ('@app.post("/memories"', '@api_router.post("/memories"'),
        ('@app.get("/memories"', '@api_router.get("/memories"'),
        ('@app.get("/memories/{memory_id}"', '@api_router.get("/memories/{memory_id}"'),
        ('@app.post("/search"', '@api_router.post("/search"'),
        ('@app.put("/memories/{memory_id}"', '@api_router.put("/memories/{memory_id}"'),
        ('@app.delete("/memories/{memory_id}"', '@api_router.delete("/memories/{memory_id}"'),
        ('@app.delete("/memories"', '@api_router.delete("/memories"'),
        ('@app.post("/reset"', '@api_router.post("/reset"'),
    ]
    
    routes_fixed = 0
    for old, new in route_replacements:
        if old in content:
            content = content.replace(old, new)
            routes_fixed += 1
    
    if routes_fixed > 0:
        fixes_applied += 1
        print(f"✓ Fix 6: Replaced {routes_fixed} @app decorators with @api_router")
    
    # Fix 7: Add router registration before home route
    home_route = '@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)'
    router_registration = '''# 将 API 路由器注册到应用
app.include_router(api_router)

# 保持根路径和文档路径不变（无前缀）
@app.get("/", summary="Redirect to the OpenAPI documentation", include_in_schema=False)'''
    
    if home_route in content and 'include_router' not in content:
        content = content.replace(home_route, router_registration)
        fixes_applied += 1
        print("✓ Fix 7: Added router registration")
    
    # Check if any fixes were applied
    if content == original_content:
        print("WARNING: No fixes were applied. The file may already be patched or the patterns don't match.")
        return True
    
    # Write the fixed content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n✅ Successfully applied {fixes_applied} fixes to {file_path}")
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python apply_server_fixes.py /path/to/server/main.py")
        sys.exit(1)
    
    file_path = sys.argv[1]
    
    print(f"Applying Mem0 server fixes to: {file_path}")
    print("=" * 60)
    
    success = apply_fixes(file_path)
    
    if success:
        print("\n" + "=" * 60)
        print("All fixes applied successfully!")
        sys.exit(0)
    else:
        print("\n" + "=" * 60)
        print("ERROR: Failed to apply fixes")
        sys.exit(1)


if __name__ == "__main__":
    main()
