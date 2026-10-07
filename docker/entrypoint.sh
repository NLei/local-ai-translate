#!/bin/sh
# 翻译服务入口：llama-server 同时提供 WebUI(/) 与 OpenAI 兼容 API(/v1/...)
set -e

# 随镜像携带的 libgomp（bookworm-slim 不自带，构建机拷入 /app/lib）
[ -d /app/lib ] && LD_LIBRARY_PATH="/app/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" && export LD_LIBRARY_PATH

PORT="${PORT:-8080}"
MODEL="${MODEL:-/app/model.gguf}"
CTX="${CTX:-8192}"
PARALLEL="${PARALLEL:-1}"
THREADS="$THREADS"
if [ -z "$THREADS" ] || [ "$THREADS" = "0" ]; then THREADS="$(nproc)"; fi

EXTRA_ARGS=""
[ -n "$API_KEY" ] && EXTRA_ARGS="$EXTRA_ARGS --api-key $API_KEY"
# Qwen3 系列关思考模式：值必须作为独立参数传（llama-server 不支持 --flag=value 粘连形式）
if [ "$NOTHINK" = "1" ]; then
  set -- "$@" --chat-template-kwargs '{"enable_thinking":false}'
fi
[ -n "$EXTRA_SERVER_ARGS" ] && EXTRA_ARGS="$EXTRA_ARGS $EXTRA_SERVER_ARGS"

exec /app/llama-server \
  -m "$MODEL" \
  --host 0.0.0.0 --port "$PORT" \
  --path /app/web \
  -c "$CTX" -t "$THREADS" --parallel "$PARALLEL" \
  --jinja \
  $EXTRA_ARGS "$@"
