#!/bin/bash
# 生成 gRPC Python 代码

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

PROTO_DIR="$PROJECT_ROOT/proto"
OUT_DIR="$PROJECT_ROOT/src/cozymemory/grpc_server"

mkdir -p "$OUT_DIR"

python -m grpc_tools.protoc \
  -I"$PROTO_DIR" \
  --python_out="$OUT_DIR" \
  --grpc_python_out="$OUT_DIR" \
  "$PROTO_DIR/common.proto" \
  "$PROTO_DIR/conversation.proto" \
  "$PROTO_DIR/profile.proto" \
  "$PROTO_DIR/knowledge.proto"

echo "gRPC code generated in $OUT_DIR"