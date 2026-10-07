# 实现说明与复现指南（DEVELOPMENT）

本文面向要**复现、换模型、重新评测或二次开发**本项目的读者。使用向说明见 [../README.md](../README.md)，评测数据见 [../results/analysis.md](../results/analysis.md)。

## 一、项目原理

```
                    ┌──────────────────────────────────────────┐
 浏览器/插件/curl ──▶│ llama-server（单进程）                    │
                    │  · 静态托管 web/（--path，含翻译页+对话页）│
                    │  · OpenAI 兼容 API（/v1/chat/completions）│
                    │  · GGUF 推理（CPU，GGML_AVX2）            │
                    │  · 可选鉴权（--api-key）、CORS 控制        │
                    └──────────────────────────────────────────┘
```

三个关键决策：

1. **llama.cpp + GGUF**：纯 CPU 推理、无 Python 依赖、OpenAI 兼容 API 开箱即用，且 `--path` 参数让同一个进程直接托管静态网页——WebUI 不需要 nginx/Node，这是镜像能做小的根本原因。
2. **WebUI 是纯静态单文件**（`web/index.html`、`web/chat.html`，原生 HTML/CSS/JS）：同源调用 `/v1/chat/completions`（SSE 流式），无构建步骤、无 CDN 依赖、离线可用；`docker cp` 单文件即可热更新。
3. **镜像 = 精简基础系统 + 一个静态二进制 + 模型权重**：运行时只有 llama-server（约 15MB 静态编译）+ libgomp（随镜像携带），加上模型 GGUF 构成全部体积。

## 二、仓库结构

```
llama.cpp-repo/            llama.cpp 源码（shallow clone；本地构建与 docker build 共用）
models/                    GGUF 权重（不入 git）
web/                       两个 WebUI 单文件
docker/Dockerfile          主镜像（Hy-MT2-1.8B），两阶段构建
docker/Dockerfile.light    轻量镜像（Qwen3.5-0.8B）
docker/Dockerfile.dockerignore / .light.dockerignore   白名单式上下文控制
docker/entrypoint.sh       容器入口（环境变量 → llama-server 参数）
docker/docker-compose.yml
scripts/assemble_image.py  离线镜像组装（无 docker 时的构建路径 B）
scripts/bench_translate.py 翻译质量评测（多模型 × 句集，产出 JSON + 对比表）
scripts/test_general.py    通用能力测试（代码运行验证/总结/数据整理）
scripts/test_techdoc.py    技术文档翻译实测（kernel.org PCI 文档节选）
scripts/test_stopping.py   量化后停止行为对照实验
scripts/imatrix-calibration.txt  量化校准文本
scripts/techdoc_passages.md      技术文档测试夹具（Markdown 化的三段节选）
docs/DEVELOPMENT.md        本文档
results/                   评测报告与原始数据
```

## 三、两条镜像构建路径

### 路径 A：标准 docker build

`docker/Dockerfile` 两阶段：`ubuntu:24.04` 编译 llama.cpp（`BUILD_SHARED_LIBS=OFF` 产出单文件 llama-server，`GGML_NATIVE=OFF -DGGML_AVX2=ON -DGGML_FMA=ON` 保证目标机可移植）→ `debian:bookworm-slim` + `libgomp1` + 二进制 + web + 模型。轻量版 `Dockerfile.light` 仅默认 `ARG MODEL_FILE` 与 `NOTHINK=1` 不同；各自配套 `*.dockerignore` 白名单只带所需模型进上下文。

### 路径 B：离线组装（`scripts/assemble_image.py`）

**为什么存在**：llama.cpp 必须现场编译，但某些构建环境（无 root、无 systemd 的 WSL 沙箱、极简容器）装不了 docker。该脚本绕过容器引擎，直接产出 `docker load` 兼容的标准镜像 tar。

**docker 镜像 tar 的格式要点**（schema v2 save 格式）：

```
manifest.json                     # [{"Config": "<sha256>.json", "RepoTags": [...], "Layers": ["<id1>/layer.tar", "<id2>/layer.tar"]}]
<sha256>.json                     # image config：Env/Entrypoint/User/rootfs.diff_ids
<base_id>/layer.tar               # 基础 rootfs 层（未压缩）
<add_id>/layer.tar                # 应用层（uid/gid 置 0 的常规文件）
```

- `config.rootfs.diff_ids` = 每层**未压缩** tar 内容的 sha256；`docker load` 会据此校验
- config 文件名 = 其自身内容的 sha256
- 应用层 tar 用 Python `tarfile` 生成，所有条目 `uid/gid=0`、模式 644/755——与真实 `docker build` 行为一致
- 基础层直接采用 [ubuntu-base](https://cdimage.ubuntu.com/ubuntu-base/releases/22.04/release/) 官方 rootfs tarball 的字节（**不落盘解压**，外来 UID 只存在于 tar 元数据中，无损）

用法：

```bash
MODEL_SRC=models/Hy-MT2-1.8B-Q4_K_M.gguf \
EXTRA_ENV='NOTHINK=1' \          # 可选：注入容器环境变量（如 Qwen3 关思考）
BASE_TARBALL=/tmp/ai-translate-build/ubuntu-base.tar.gz \
python3 scripts/assemble_image.py <项目根> <输出.tar> "ai-translate:hy-mt2-1.8b"
```

### 构建后验证：unshare + chroot（等价容器环境）

镜像没经过真实 docker run 之前，用这条链路验证（与容器行为等效，历史教训见踩坑 #5）：

```bash
# ① 从镜像 tar 解出全部层到 RFS 目录（等价 docker load 的解压）
# ② 用户命名空间里以"伪 root"进入
unshare --user --map-root-user --mount bash -c '
  mount -t proc proc /RFS/proc
  chroot /RFS /bin/sh -c "export PORT=8081; exec /app/entrypoint.sh"'
# ③ 宿主侧 curl /health 与 /v1/chat/completions
```

## 四、换模型指南

### 1. 下载（国内网络实测顺序）

1. **ModelScope**：`https://modelscope.cn/api/v1/models/<org>/<repo>/repo/files` 查文件，`/resolve/master/<file>` 下载，速度最快
2. **hf-mirror.com**：API 与 resolve 路径同 huggingface，部分仓库匿名 token 被拒时换 ModelScope
3. huggingface.co 直连：本环境超时，不指望

下载后校验 GGUF 头（magic/architecture/chat_template），仓库里 `models/` 下有现成样例。

### 2. 各模型所需启动参数（重要）

| 模型家族 | llama-server 参数 | 说明 |
|---|---|---|
| Hy-MT2 / Hy-MT1.5（hunyuan-dense） | `--jinja` + 官方采样 temp 0.7 / top_p 0.6 / top_k 20 / rep 1.05 | 提示词用官方模板"将以下文本翻译为 \`语言\`…" |
| Qwen3-0.6B（qwen3） | `--jinja --chat-template-kwargs '{"enable_thinking": false}'` | `--reasoning-budget 0` **无效**，必须用模板参数；漏配会输出思考过程 |
| Haidass-143M（qwen3 架构） | `--chat-template chatml` | 默认模板下正文为空，改普通 chatml 即可 |
| Qwen3.5-0.8B（qwen35，SSM 混合） | `--jinja` + 上面的 enable_thinking 关闭 + **`--parallel 1`** | SSM 状态随槽位翻倍内存（默认 4 槽 RSS 4.3GB → 1 槽 857MB） |
| Qwen2.5 / MiniCPM5 / Gemma3 | 默认或 `--jinja` | Gemma3 采样用 temp 1.0 / top_p 0.95 / top_k 64 |

### 3. 切换方式

- **换 GGUF 不换家族**：`-v /path/new.gguf:/app/model.gguf` 挂载 + `docker restart`
- **交付新镜像**：改 `assemble_image.py` 调用时的 `MODEL_SRC` 与 tag，或 `Dockerfile` 的 `--build-arg MODEL_FILE=xxx.gguf`（注意同步对应 `*.dockerignore` 白名单）

### 4. 内存/速度参考（12 核 WSL2 基线）

| 模型 | 体积 | RSS(-c 4096 默认槽位) | 速度 |
|---|---|---|---|
| Hy-MT2-1.8B Q4_K_M | 1133 MB | 2329 MB | 18.2 tok/s |
| Qwen3.5-0.8B Q4_K_M | 533 MB | 4298 MB（**PARALLEL=1 → 857 MB**） | 22.4 tok/s |
| Qwen3-0.6B Q4_K_M | 397 MB | 1472 MB | 40.1 tok/s |
| Haidass-143M Q8_0 | 188 MB | 486 MB | 98.3 tok/s |

## 五、重新评测 / 增加测试

```bash
# 翻译质量（80 句 × 2 方向；--models 选子集，--limit 快速跑）
python3 scripts/bench_translate.py --models Hy-MT2-1.8B,Qwen3.5-0.8B

# 漏译统计口径：空输出 / 原样返回 / 拒绝与元话语（analysis.md 第二节同口径）
# 通用能力（代码运行验证 + 总结 + 数据整理）
python3 scripts/test_general.py
# 技术文档翻译（替换 scripts/techdoc_passages.md 的节选即可换题材）
python3 scripts/test_techdoc.py
# 量化后停止行为对照（EOS 是否损坏）
python3 scripts/test_stopping.py <端口> <标注>
```

加新句集/新任务：句集是纯文本每行一句；判分器在 `test_general.py` 的 `CHECKERS`。**注意两个口径坑**：① 关键词匹配要先归一化空格、容忍模型转述（"P95 降 4 倍" vs "400 毫秒"）；② 思考模式要给足 token 预算（×4），否则正文为空被误判为失败。

## 六、更新工具

- **升级 llama.cpp**：`git pull` 后按第三节重编。当前仓库工作区打过 STQ 实验补丁（见踩坑 #7），**重新构建交付物前先 `git checkout -- .` 复原到干净 master**，并记录所用的 commit（交付物对应 `d7a695e`，2026-10-06）。升级后先确认新模型架构已支持（`grep -r 架构名 src/llama-arch.cpp`）。
- **升级 Python/依赖**：量化转换用 python-build-standalone 3.12（`~/opt/py312`），依赖 torch CPU + gguf + transformers，见 `pip install` 记录；`--index-url https://download.pytorch.org/whl/cpu` 避免拉到数 GB 的 CUDA 轮子。
- **更新基础镜像/模型**：改 `BASE_TARBALL` 或 `MODEL_SRC` 即可，流程不变。

## 七、踩坑记录（按发现顺序，都是实际踩过的）

### 网络

1. **huggingface.co 直连超时** → 用 hf-mirror.com；hf-mirror 匿名 token 对部分仓库返回 DENIED、且限流抖动 → **ModelScope 兜底**（注意跨源断点续传前确认文件一致）。
2. **GitHub release 断点续传可能损坏文件**（curl -C - 恢复后 tar 报 unexpected EOF）→ 删除重下并 `gzip -t` 校验；`mirror.ghproxy.com` 实测不稳定；github.com/git 克隆间歇超时（index-pack failed）→ 改用 api.github.com 拉补丁或 codeload tarball，仍不通就多试几次。
3. 可用性实测（2026-10）：pypi.org / download.pytorch.org / download.docker.com / cdimage.ubuntu.com / bootstrap.pypa.io ✅；pypi.tuna、dockerproxy ✗。

### llama.cpp 与模型

4. **Qwen3 关思考模式**：`--reasoning-budget 0` 单独用无效；`--chat-template-kwargs` 的 JSON 值**必须作为独立参数传递**——llama-server 不支持 `--flag=value` 粘连写法（报 invalid argument），含空格的 JSON 经环境变量透传会被 shell 拆词 → entrypoint 用 `NOTHINK=1` + `set --` 以带引号整体传递。
5. **qwen3 架构的微调小模型**（Haidass）：默认聊天模板预填 think 块导致正文为空，改 `--chat-template chatml` 解决。
6. **Hy-MT2 官方 1.25Bit / 2Bit GGUF 无法加载**：依赖未合并的 STQ 内核（PR #22836，仅 ARM NEON）；把补丁打到 master 编译成功后仍报张量偏移不匹配——官方产物与 PR 代码的块布局版本不一致。这两个文件在内核合并且官方重新导出前不可用。
7. **3-bit 以下量化 EOS 损坏**：Hy-MT2 自量化 IQ3_XXS/IQ2_M/Q3_K_S 译文正确但译完不停（四种采样参数救不回）；Qwen3-0.6B IQ1_S 输出乱码。**Q4_K_M 是可用下限**，官方只发 Q4/Q6/Q8 与此吻合。
8. llama.cpp 的 Hunyuan（hunyuan-dense）与 qwen35（SSM 混合）架构主线均已支持；SSM 架构的 RSS 与 `--parallel` 槽位数成正比。

### 无 root 环境跑容器（本沙箱的三道墙）

9. docker.io 包**只带 systemd 单元**，WSL 无 systemd 时 `service` 也起不来（无 init.d 脚本）→ rootless dockerd 尝试。
10. rootless 三道墙：① rootlesskit v1/v2 均需 `newuidmap`（setuid，无 sudo 装不了）；② containerd 要写 `/run/containerd`（`unshare --mount` 里手动 `mount -t tmpfs none /run` 可解）；③ **解层时对基础镜像里的外来 UID/GID 做 lchown 失败**（无 subuid 无解）——这是死墙，rootless docker 放弃。
11. 解法：**手动组装镜像**（路径 B）+ **unshare+chroot 验证**（第三节）。普通用户的 WSL 要正经用 docker：`/etc/wsl.conf` 启用 systemd，或装 Windows 版 Docker Desktop。

### 打包

12. **tarfile.gettarinfo 不解引用软链**：宿主机的 `libgomp.so.1` 是软链，打出的层里是 SYMTYPE 条目（目标指向宿主机路径），容器内即坏链——现象为容器 exit 127 "libgomp.so.1: cannot open shared object file"。修复：源文件先 `os.path.realpath` 解引用。**教训：chroot 验证要用真实镜像层内容，手工 cp 会掩盖此类问题。**
13. docker save 格式三处校验点：diff_id 对未压缩层求 sha256、config 文件名即其 sha256、manifest 的 Layers 路径与 tar 条目一致。漏一处 `docker load` 即失败。
14. 静态链接 llama-server（`BUILD_SHARED_LIBS=OFF`）仍动态依赖 `libgomp/libstdc++/libgcc_s`：前两者镜像内携带或 apt 安装，`libstdc++/libgcc_s` ubuntu-base 22.04 自带。

### Shell / 流程

15. **`pkill -f <模式>` 会匹配到自身所在的后台命令行**导致任务自杀 → 用 `pkill -x 进程名`。
16. **管道吞退出码**：`cmd 2>&1 | tail -5 && echo OK` 永远成功 → `set -o pipefail`。
17. 后台任务的 PATH 不继承交互式配置 → 脚本内用绝对路径（如 `~/opt/bin/cmake`）。
18. 嵌套引号传 JSON 命令行参数会被多层 shell 撕碎（实测 `{"a_b":1}` 变成 `{a-b:1}`）→ 写成文件执行，或 entrypoint 里 `set --` 整体传参。
19. `/tmp` 下的大文件（基础镜像、模型）清理前确认不再需要——本项目的 base tarball、verify-rootfs 被反复重建过三次。

### 评测方法

20. 漏译自动判定三类口径（空输出/原样返回/元话语）**抓不住"错误翻译"**（如拉丁语乱码、语义颠倒），必须配合人工逐句评估。
21. 关键词匹配先 `re.sub(r"\s+","")` 归一化，且容忍转述——"P95 降 4 倍"和"400 毫秒"是同一个事实。
22. 思考模式 token 预算不足时正文为空，会被误判"能力为零"；实测 1024 预算下推理就耗尽，需 ×4。

## 八、发布到 GitHub 与已知限制

### 发布清单（什么进 git、什么不进）

`.gitignore` 已配置，规则与理由：

| 排除项 | 理由 |
|---|---|
| `models/`（18GB GGUF） | 第三方权重，官方源可下载；git 不适合 4GB 级文件 |
| `llama.cpp-repo/`（425MB） | 第三方源码副本 + 本地构建产物；用 `scripts/fetch_llama_cpp.sh` 按固定 commit 拉取（交付镜像由 d7a695e 编译），仓库工作区另有 STQ 实验补丁未复原，不应发布 |
| `*.tar.gz`（镜像包） | 构建产物；分发走 GitHub Releases（单文件上限 2GB，两个包都放得下）或镜像仓库 |
| `hf-hy-mt2/`、`.zcode/`、`.vscode/`、`results/general-tmp/` | 本地工作状态与工具配置 |
| `scripts/pci.rst`（GPL-2.0 原文） | 第三方 GPL 文档不与 MIT 仓库混发；仓库内只保留转写的测试夹具 `techdoc_passages.md`，原文按链接重新下载 |

**提交前检查**：`grep -rn "本机用户名与主机名" --exclude-dir=llama.cpp-repo --exclude-dir=models .` 应无结果（本机路径已在发布前清洗）；`git status` 里不应出现任何 >50MB 的文件。

### 镜像包发布到 GitHub Releases

tar.gz 属于构建产物，不进 git，但适合作为 Release 附件分发（单文件上限 2GB，两个包均符合）：

- **网页操作**：仓库页 → Releases → Draft a new release → 填 tag（如 `v1.0.0`）与标题 → 拖入 `ai-translate-hy-mt2-1.8b.tar.gz` 与 `ai-translate-qwen35-0.8b.tar.gz` → Publish
- **gh CLI**（需先 `gh auth login`）：

```bash
gh release create v1.0.0 \
  ai-translate-hy-mt2-1.8b.tar.gz \
  ai-translate-qwen35-0.8b.tar.gz \
  --title "ai-translate v1.0.0" \
  --notes "主镜像（Hy-MT2-1.8B，质量最佳）与轻量镜像（Qwen3.5-0.8B，零漏译）。docker load 后离线运行，见 README。"
```

更新版本时创建新 tag 即可，旧附件自动保留历史。

### 已知限制与后续方向

- 镜像 x86_64 + AVX2 假设：目标 CPU 过老需重编 baseline（`-DGGML_AVX2=OFF`）。
- 单进程并发：`--parallel N` 提升吞吐但挤占上下文与（Qwen3.5）内存，当前默认 1。
- 未做 HTTPS/多实例/负载均衡：按需前置反向代理。
- 超轻量档（<400MB）无现成可用模型：需中英平行语料微调小模型（参考 Marie 对 Gemma 3 270M 的做法）。
- 官方 Hy-MT2 1.25Bit/2Bit 待 STQ 内核合并且官方重导 GGUF 后重测。
