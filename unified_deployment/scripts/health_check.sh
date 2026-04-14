#!/bin/bash
echo "Checking CozyMemory Stack Health..."

# 1. Check Postgres
docker exec cozy_postgres pg_isready -U postgres
if [ $? -eq 0 ]; then echo "✅ Postgres: READY"; else echo "❌ Postgres: FAILED"; fi

# 2. Check Mem0 API
curl -s --head http://localhost:8888/api/v1/ | grep "200\|404" > /dev/null
if [ $? -eq 0 ]; then echo "✅ Mem0 API: READY"; else echo "❌ Mem0 API: FAILED"; fi

# 3. Check Memobase API
curl -s --head http://localhost:8019/ | grep "200" > /dev/null
if [ $? -eq 0 ]; then echo "✅ Memobase API: READY"; else echo "❌ Memobase API: FAILED"; fi

# 4. Check Cognee API
curl -s --head http://localhost:8000/ | grep "200" > /dev/null
if [ $? -eq 0 ]; then echo "✅ Cognee API: READY"; else echo "❌ Cognee API: FAILED"; fi

echo "Health check complete."
