#!/usr/bin/env bash
# 拉取项目所依赖的 llama.cpp 源码到 llama.cpp-repo/（固定 commit，保证可复现）。
# 交付的镜像由该 commit（d7a695e，2026-10-06）编译；升级前先跑一轮评测，见 docs/DEVELOPMENT.md 第六节。
set -euo pipefail

PINNED="d7a695ef679138c13d86359b84c1731d36213d32"
DEST="$(cd "$(dirname "$0")/.." && pwd)/llama.cpp-repo"

if [ -d "$DEST/.git" ]; then
    echo "llama.cpp-repo 已存在。如需更新：git -C $DEST fetch && git -C $DEST checkout $PINNED"
    exit 0
fi

git clone --filter=blob:none https://github.com/ggml-org/llama.cpp "$DEST"
git -C "$DEST" checkout "$PINNED"
echo "llama.cpp 已检出到 $DEST ($PINNED)"
