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

> 两个 tar.gz 已在仓库根目录，可直接 `docker load`（无需网络）。
> 轻量镜像第四轮测试后由 Qwen3-0.6B 换装为 **Qwen3.5-0.8B**：实测 Qwen3-0.6B 对成语/口语英→中存在漏译倾向（Q4→BF16 均无法消除，属模型行为），而 Qwen3.5-0.8B 在同一测试集上零漏译。详见 [results/analysis.md](results/analysis.md) 第四轮。
> 注意：Qwen3.5 是 SSM+注意力混合架构，SSM 状态常驻内存与并发槽位成正比，**必须保持 `PARALLEL=1`**（镜像已内置）后再按需调大。

## 快速开始

### 在线部署（有网服务器）

```bash
docker run -d --name ai-translate -p 8080:8080 --restart unless-stopped \
  ai-translate:hy-mt2-1.8b
# 浏览器打开 http://<服务器IP>:8080
```

或用 compose：

```bash
cd docker && docker compose up -d
```

### 离线部署（无网服务器）

```bash
# ① 把仓库根目录的 tar.gz 拷贝到离线服务器（U盘/内网）
# ② 一键导入并启动（轻量版把镜像名换成 ai-translate:qwen35-0.8b）
docker load < ai-translate-hy-mt2-1.8b.tar.gz
docker run -d --name ai-translate -p 8080:8080 --restart unless-stopped \
  ai-translate:hy-mt2-1.8b
```

> 镜像内已包含模型与运行时，加载后完全离线运行，无任何外部依赖。
> **已部署容器单独更新前端页面**：`docker cp web/index.html ai-translate:/app/web/ && docker cp web/chat.html ai-translate:/app/web/`，刷新浏览器即生效，无需重启容器或重载镜像。

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

两条等价的构建路径：

1. **标准 docker build**（任意有 docker 的机器）：`docker build -f docker/Dockerfile -t ai-translate:hy-mt2-1.8b .`
2. **离线组装** `scripts/assemble_image.py`：不依赖容器引擎，直接把 ubuntu-base 官方 rootfs + 静态 llama-server + 模型组装成 `docker load` 兼容的镜像 tar（本仓库交付的 tar.gz 即由它产出）

> 为什么会有路径 2：llama.cpp 需要现场编译，而有些构建环境（如本项目的 WSL 沙箱）无法安装 docker/无 root 权限，此脚本绕过容器引擎直接产出标准镜像，产物与 docker build 功能一致。
> **原理、换模型、重新评测与踩坑记录，见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。**

## 从源码构建

```bash
# 主镜像（Hy-MT2）
docker build -f docker/Dockerfile -t ai-translate:hy-mt2-1.8b .

# 轻量镜像（Qwen3.5-0.8B）
docker build -f docker/Dockerfile.light -t ai-translate:qwen35-0.8b .

# 或离线组装（无需 docker）
MODEL_SRC=models/Hy-MT2-1.8B-Q4_K_M.gguf python3 scripts/assemble_image.py . out.tar "ai-translate:hy-mt2-1.8b"
```

构建依赖：ubuntu:24.04（编译 llama.cpp，静态链接）+ debian:bookworm-slim（运行时）。
llama.cpp 编译选项：`-DGGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_FMA=ON`——不绑定构建机 CPU 型号，要求目标 CPU 支持 AVX2/FMA（2013 年后的 x86_64 均支持）。

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
