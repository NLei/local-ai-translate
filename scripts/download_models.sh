#!/usr/bin/env bash
# 下载交付镜像所需的两个 GGUF 模型（约 1.7GB）到 models/ 目录。
# 默认走 ModelScope（国内快），失败自动回退 hf-mirror.com；支持断点续传，可重复执行。
set -uo pipefail

DIR="$(cd "$(dirname "$0")/.." && pwd)/models"
mkdir -p "$DIR"

# repo（ModelScope/unsloth 与 hf 同名）| 文件名
MODELS=(
  "Tencent-Hunyuan/Hy-MT2-1.8B-GGUF|Hy-MT2-1.8B-Q4_K_M.gguf"
  "unsloth/Qwen3.5-0.8B-GGUF|Qwen3.5-0.8B-Q4_K_M.gguf"
)

fetch() { # $1=repo $2=file $3=源(ms|hf)
  local url
  case "$3" in
    ms) url="https://modelscope.cn/models/$1/resolve/master/$2" ;;
    hf) url="https://hf-mirror.com/$1/resolve/main/$2" ;;
  esac
  curl -sL -C - --connect-timeout 20 --retry 4 --retry-delay 3 -o "$DIR/$2" "$url"
}

for spec in "${MODELS[@]}"; do
  repo="${spec%%|*}"; file="${spec##*|}"
  if [ -s "$DIR/$file" ]; then echo "已存在，跳过: $file"; continue; fi
  echo "下载 $file ..."
  fetch "$repo" "$file" ms || fetch "$repo" "$file" hf
  [ -s "$DIR/$file" ] && echo "  OK ($(du -h "$DIR/$file" | cut -f1))" || echo "  失败，请检查网络后重跑本脚本（已下载部分会续传）"
done

echo "=== models/ 当前内容 ==="
ls -lh "$DIR"
