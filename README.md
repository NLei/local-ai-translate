# AI 翻译服务（ai-translate）

本地大模型驱动的中英互译服务：**WebUI + 对话页 + OpenAI 兼容 API + 离线 Docker 一键部署**。
形态对标 [MTranServer](https://github.com/xxnuo/MTranServer)，但内核是 LLM（非传统统计机翻），译文自然流畅。

```
┌────────────────────────────────────────────┐
│                ai-translate                │
│                                            │
│  /                    → 翻译 WebUI          │
│  /chat.html           → 对话 WebUI          │
│  /v1/chat/completions → OpenAI 兼容 API     │
│  /health              → 健康检查            │
│                                            │
│  llama-server (CPU, AVX2) + 内置 GGUF 模型  │
└────────────────────────────────────────────┘
```

一个容器进程同时提供上述全部能力，无 Python/Node/nginx 依赖，完全离线运行。
实现原理、两条构建路径与踩坑记录见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## 模型选型

| 镜像 tag | 模型 | 镜像压缩包 | 运行内存 | 速度(6线程基准) | 定位 |
|---|---|---|---|---|---|
| `ai-translate:hy-mt2-1.8b` | Hy-MT2-1.8B Q4_K_M | **1.07 GB** (`ai-translate-hy-mt2-1.8b.tar.gz`) | ~2.4 GB | 18 tok/s | **主推**：质量全面最佳，技术文档尤甚 |
| `ai-translate:qwen35-0.8b` | Qwen3.5-0.8B Q4_K_M | **529 MB** (`ai-translate-qwen35-0.8b.tar.gz`) | ~0.9 GB | 22 tok/s | 轻量：零漏译，低配服务器 |

> 两个 tar.gz 从本仓库 **Releases** 页下载（或按「构建与产物」自行构建），`docker load` 后离线可用。
> 轻量镜像第四轮测试后由 Qwen3-0.6B 换装为 **Qwen3.5-0.8B**：实测 Qwen3-0.6B 对成语/口语英→中存在漏译倾向（Q4→BF16 均无法消除，属模型行为），而 Qwen3.5-0.8B 在同一测试集上零漏译。详见 [results/analysis.md](results/analysis.md) 第四轮。
> 注意：Qwen3.5 是 SSM+注意力混合架构，SSM 状态常驻内存与并发槽位成正比，**必须保持 `PARALLEL=1`**（镜像已内置）后再按需调大。

## 快速开始

### 方式一：使用 Releases 镜像包（推荐，无需编译）

镜像未发布到任何公共镜像仓库，**必须先从 Releases 下载 tar.gz 并 `docker load` 导入本地**，之后才能 `docker run`（直接 `docker run` 一个不存在的 tag 会报 pull access denied）。

**主镜像**（Hy-MT2-1.8B，质量最佳，1.07GB）：

```bash
docker load < ai-translate-hy-mt2-1.8b.tar.gz
docker run -d --name ai-translate -p 8080:8080 --restart unless-stopped \
  ai-translate:hy-mt2-1.8b
curl http://localhost:8080/health     # {"status":"ok"}，浏览器打开 http://localhost:8080
```

**轻量镜像**（Qwen3.5-0.8B，零漏译，529MB；如果与主镜像并存需要换个端口和容器名）：

```bash
docker load < ai-translate-qwen35-0.8b.tar.gz
docker run -d --name ai-translate-light -p 8081:8080 --restart unless-stopped \
  ai-translate:qwen35-0.8b
# 浏览器打开 http://localhost:8081
```

两个容器同时跑时注意内存：主镜像约 2.4GB + 轻量镜像约 0.9GB。

> 镜像导入后完全离线运行。compose 用户：镜像 load 进本地后即可 `cd docker && docker compose up -d`（compose 文件不含 build 配置，不会自动拉取或构建）。
> **已部署容器单独更新前端页面**：`docker cp web/index.html ai-translate:/app/web/ && docker cp web/chat.html ai-translate:/app/web/`，刷新浏览器即生效。

### 方式二：Clone 源码，自行下载模型与依赖后构建

```bash
# ① 克隆项目，拉取 llama.cpp 源码（固定 commit，保证可复现）
git clone https://github.com/<你的用户名>/ai-translate.git
cd ai-translate
./scripts/fetch_llama_cpp.sh

# ② 编译静态 llama-server（约 3~5 分钟；需 cmake 3.14+ 与 gcc/g++，AVX2 支持详见下文）
cmake -B llama.cpp-repo/build -S llama.cpp-repo \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
  -DGGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_AVX512=OFF \
  -DLLAMA_CURL=OFF -DLLAMA_BUILD_TESTS=OFF -DLLAMA_BUILD_EXAMPLES=OFF -DLLAMA_BUILD_SERVER=ON
cmake --build llama.cpp-repo/build --target llama-server -j"$(nproc)"

# ③ 下载模型权重（约 1.7GB；ModelScope 优先、失败自动回退 hf-mirror，支持断点续传）
./scripts/download_models.sh

# ④ 生成镜像（二选一）并导入
docker build -f docker/Dockerfile -t ai-translate:hy-mt2-1.8b .       # 需要 docker
# 或无需 docker（离线组装，原理见 docs/DEVELOPMENT.md）：
python3 scripts/assemble_image.py . out.tar "ai-translate:hy-mt2-1.8b"
docker load < out.tar

# ⑤ 运行
docker run -d --name ai-translate -p 8080:8080 --restart unless-stopped \
  ai-translate:hy-mt2-1.8b
```

轻量镜像：步骤④ 换用 `docker/Dockerfile.light`（或组装时 `MODEL_SRC=models/Qwen3.5-0.8B-Q4_K_M.gguf`），tag 用 `ai-translate:qwen35-0.8b`。
说明：编译选项不绑定构建机 CPU 型号，要求目标 CPU 支持 AVX2/FMA（2013 年后的 x86_64 均支持）；base rootfs（约 30MB）首次组装时自动从 cdimage.ubuntu.com 下载，无外网的构建环境见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## WebUI

浏览器访问 `http://<IP>:8080`：

- 双栏翻译布局、中→英 / 英→中 / **自动检测**（按 CJK 字符占比判断方向）
- 流式输出、Enter 翻译、Shift+Enter 换行、Esc 停止、一键复制
- **主题切换**（右上角 🌓：自动跟随系统 / 浅色 / 深色）
- **设置（右上角 ⚙）**：API 密钥（服务端启用 `API_KEY` 时填写）、**系统提示词**（可自定义人设与术语要求，留空则不发送）
- 均保存在浏览器本地

### 对话页 `/chat.html`

简易 ChatGPT 式界面（翻译页右上角 💬 进入）：对话气泡、多轮上下文（自动携带最近 20 轮）、流式输出、思考过程折叠显示；⚙ 可调 temperature / top_p / top_k / repeat_penalty / max_tokens / 系统提示词；对话历史保存在浏览器本地，🧹 开始新对话。

## API

OpenAI 兼容（`/v1/chat/completions`），任何支持自定义 OpenAI 接口的客户端/插件都能直接接。

```bash
curl http://127.0.0.1:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [
      {"role": "user", "content": "将以下文本翻译为 `英文`，注意只需要输出翻译后的结果，不要额外解释：\n今天天气不错，我们出去走走吧。"}
    ],
    "temperature": 0.7, "top_p": 0.6, "top_k": 20, "repeat_penalty": 1.05
  }'
```

流式调用加 `"stream": true`。

### 接入沉浸式翻译（浏览器插件）

设置 → 添加自定义 AI 翻译接口：

- API 地址：`http://<服务器IP>:8080/v1/chat/completions`
- 模型名：`model`（任意），API Key：留空（或与 `API_KEY` 一致）
- 自定义提示词（中→英）：

```
将以下文本翻译为 `英文`，注意只需要输出翻译后的结果，不要额外解释：
{{text}}
```

（英→中同理，把 `英文` 换成 `中文`）

## API 密钥

| 场景 | 是否需要 |
|---|---|
| 本机 / 可信内网自用 | ❌ 不需要，保持默认无鉴权最省事 |
| 服务暴露到公网 / 有他人可访问的内网 | ✅ 强烈建议 |
| 防止任意网页静默调用你的 API（llama-server 默认 CORS 全开） | ✅ 建议配合使用 |

**生成**（任选其一，key 就是自定义随机字符串，无格式要求）：

```bash
openssl rand -hex 32
python3 -c "import secrets; print('sk-' + secrets.token_hex(24))"
```

**服务端启用**（环境变量方式，需重建容器）：

```bash
docker rm -f ai-translate
docker run -d --name ai-translate -p 8080:8080 --restart unless-stopped \
  -e API_KEY=sk-你的随机串 \
  ai-translate:hy-mt2-1.8b
```

**客户端配置**：

- WebUI / 对话页：右上角 ⚙ → 填同一个 key（存浏览器 localStorage，之后自动携带）
- curl：`-H "Authorization: Bearer sk-你的随机串"`
- 验证：无 key 请求 `/v1/models` 应返回 401，带 key 应返回 200（`/health` 不受保护，属刻意设计）

**安全备注**：key 随 HTTP 明文传输，公网使用建议前置 nginx/caddy 做 HTTPS；`/v1/chat/completions` 与 `/v1/models` 受保护，`/health` 不受保护。

## 环境变量

| 变量 | 默认 | 说明 |
|---|---|---|
| `PORT` | `8080` | 监听端口 |
| `CTX` | `8192` | 上下文长度（翻译长文档可调大） |
| `THREADS` | `0`(自动) | CPU 线程数 |
| `PARALLEL` | `1` | 并发路数（占用 `CTX`×N 总槽位；Qwen3.5 混合架构的 SSM 状态与槽位成正比，保持 1） |
| `API_KEY` | 空 | 启用 Bearer 鉴权 |
| `NOTHINK` | 空 | 设为 `1` 时给 Qwen3 系模型注入"关闭思考模式"参数 |
| `EXTRA_SERVER_ARGS` | 空 | 透传给 llama-server 的额外参数（不含空格，如 `--cors-origins=http://x.y`） |
| `MODEL` | `/app/model.gguf` | 模型路径（可挂载替换 GGUF） |

## 常见问题与运维

**Q：浏览器里其他网页能不能偷偷调用我的 API？**
llama-server 默认 CORS 全开（实测任意 Origin 回显），配合无鉴权时理论上可以。收紧方式：设置 `API_KEY`（第三方网页拿不到 key 即 401），和/或 `EXTRA_SERVER_ARGS=--cors-origins=http://你的页面域名`。WebUI 自身与 API 同源，永远不受影响。

**Q：翻译页是 HTTPS 时调不通 HTTP 的 API？**
这是浏览器的"混合内容"限制，不是跨域。解法：给服务套 HTTPS 反代（nginx/caddy），或页面也用 HTTP。

**Q：WSL 里 `systemctl start docker` 报 "System has not been booted with systemd"？**
WSL 默认无 systemd。两选一：① 在 `/etc/wsl.conf` 写入 `[boot]` 段 `systemd=true`，Windows PowerShell 执行 `wsl --shutdown` 后重开；② 不启用 systemd 就直接 `sudo dockerd > /tmp/dockerd.log 2>&1 &` 手动拉起。若 unit 显示 masked：`sudo systemctl unmask docker docker.socket` 后再 enable。

**Q：容器生命周期怎么管理？**
`docker stop ai-translate` 优雅停止（`--restart unless-stopped` 策略下手动停止后不会随守护进程自动拉起）；`docker start` 恢复；`docker rm -f` 彻底删除（服务无状态，模型在镜像里，无损失）。

**Q：镜像能上传到镜像仓库吗？**
可以。阿里云 ACR 个人版 / 腾讯云 TCR / Docker Hub 均 `docker tag` + `docker push`；完全无外网的机房可自建 `registry:2`。离线分发用 tar.gz + `docker load` 最简单。

**Q：运行中如何更换模型？**
`-v /path/to/other.gguf:/app/model.gguf` 挂载替换后 `docker restart ai-translate`。注意不同家族模型所需的思考模式参数不同（见 `NOTHINK` 与 `EXTRA_SERVER_ARGS`）。

## 构建与产物

两条等价的构建路径（完整命令见上方「方式二」，原理与踩坑记录见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)）：

1. **标准 docker build**（任意有 docker 的机器）
2. **离线组装** `scripts/assemble_image.py`（无容器引擎环境；本仓库交付的 tar.gz 即由它产出）

## 本地开发（不用 Docker）

```bash
./llama.cpp-repo/build/bin/llama-server \
  -m models/Hy-MT2-1.8B-Q4_K_M.gguf --port 8080 --path web \
  -c 8192 -t 6 --jinja
```

## 复现评测

```bash
python3 scripts/bench_translate.py              # 全量评测
python3 scripts/bench_translate.py --limit 3    # 快速验证
```

## 目录结构

```
web/index.html          翻译 WebUI（单文件，零依赖离线可用）
web/chat.html           对话 WebUI（气泡多轮，参数可调）
docker/Dockerfile       主镜像构建（Hy-MT2-1.8B）
docker/Dockerfile.light 轻量镜像构建（Qwen3.5-0.8B）
docker/docker-compose.yml
docker/entrypoint.sh
scripts/assemble_image.py   离线镜像组装（无需 docker）
scripts/download_models.sh  模型权重下载（ModelScope 优先，自动回退）
scripts/fetch_llama_cpp.sh  拉取固定 commit 的 llama.cpp 源码
scripts/bench_translate.py  翻译质量评测
scripts/test_general.py     通用能力测试（代码/总结/数据整理）
scripts/test_techdoc.py     技术文档翻译实测
scripts/test_stopping.py    停止行为对照
scripts/sentences.{zh,en}.txt  80 句测试集
results/analysis.md     评测报告（六节：模型一览/综合排名/结论/交付物/通用能力/技术文档）
results/compare.md      主要模型逐句译文对比
results/techdoc-review.md  技术文档原文与译文对照
docs/DEVELOPMENT.md     实现说明、打包原理、换模型指南与踩坑记录
models/                 GGUF 模型文件（不入 git）
```
