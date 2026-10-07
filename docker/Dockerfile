# 中英互译 AI 翻译服务 —— llama-server(CPU) + 内置 WebUI + OpenAI 兼容 API
# 构建: docker build -f docker/Dockerfile -t ai-translate:1.0 .
# 默认打包 Hy-MT2-1.8B (Q4_K_M)；通过 --build-arg MODEL_FILE=xxx.gguf 换模型

# ---------- 构建阶段：编译 llama-server（CPU, AVX2 可移植） ----------
FROM ubuntu:24.04 AS builder
RUN apt-get update \
 && apt-get install -y --no-install-recommends cmake g++ \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY llama.cpp-repo/ ./
# GGML_NATIVE=OFF + 显式 AVX2/FMA：不绑定构建机 CPU 型号，任何 2013 年后的 x86_64 都能跑
# BUILD_SHARED_LIBS=OFF：产出单个静态 llama-server，运行时零 .so 依赖
RUN cmake -B build -DCMAKE_BUILD_TYPE=Release \
      -DBUILD_SHARED_LIBS=OFF \
      -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_AVX512=OFF \
      -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON \
 && cmake --build build --target llama-server -j"$(nproc)"

# ---------- 运行阶段：debian-slim + 二进制 + 模型 + 静态网页 ----------
FROM debian:bookworm-slim
RUN apt-get update \
 && apt-get install -y --no-install-recommends libgomp1 \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -m -u 1000 app
COPY --from=builder /src/build/bin/llama-server /app/llama-server
COPY web/ /app/web/
COPY docker/entrypoint.sh /app/entrypoint.sh
ARG MODEL_FILE=Hy-MT2-1.8B-Q4_K_M.gguf
COPY models/${MODEL_FILE} /app/model.gguf

ENV PORT=8080 CTX=8192
USER 1000
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
