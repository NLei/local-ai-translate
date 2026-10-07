# 中英翻译模型评测报告

为「llama.cpp + Docker 离线翻译服务」选型所做。测试集为 80 句（中→英、英→中各 40 句，覆盖日常对话 / 技术文档 / 成语习语 / 长难句 / 网络口语五类），人工逐句质量评估 + 漏译自动统计。硬件、方法与复现命令见文末附录；主要模型逐句译文对照见 [compare.md](compare.md)。

## 一、全部测试模型一览

| 模型 | 量化级别 | 模型体积 | 架构 | 许可证 | 来源 |
|---|---|---|---|---|---|
| Haidass-Translate-143M | Q8_0 | 188 MB | qwen3 | Apache-2.0 | [umeiko/Haidass-Translate-143M-GGUF](https://huggingface.co/umeiko/Haidass-Translate-143M-GGUF) |
| Qwen3-0.6B | UD-IQ1_S | 215 MB | qwen3 | Apache-2.0 | [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF) |
| Gemma 3 270M IT | Q4_K_M | 253 MB | gemma3 | Gemma Terms | [unsloth/gemma-3-270m-it-GGUF](https://huggingface.co/unsloth/gemma-3-270m-it-GGUF) |
| Qwen3-0.6B | UD-IQ2_M | 269 MB | qwen3 | Apache-2.0 | [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF) |
| Qwen3-0.6B | UD-IQ3_XXS | 282 MB | qwen3 | Apache-2.0 | [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF) |
| Qwen3-0.6B | Q3_K_M | 347 MB | qwen3 | Apache-2.0 | [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF) |
| Qwen3-0.6B | Q4_K_M | 397 MB | qwen3 | Apache-2.0 | [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF) |
| Hy-MT2-1.8B | 1.25Bit（AngelSlim STQ） | 462 MB | hunyuan-dense | Apache-2.0 | [tencent/Hy-MT2-1.8B-1.25Bit-GGUF](https://huggingface.co/tencent/Hy-MT2-1.8B-1.25Bit-GGUF) |
| Hy-MT2-1.8B | 2Bit（AngelSlim STQ） | 601 MB | hunyuan-dense | Apache-2.0 | [Tencent-Hunyuan/Hy-MT2-1.8B-2Bit-GGUF](https://modelscope.cn/models/Tencent-Hunyuan/Hy-MT2-1.8B-2Bit-GGUF) |
| Qwen2.5-0.5B-Instruct | Q4_K_M | 491 MB | qwen2 | Apache-2.0 | [Qwen/Qwen2.5-0.5B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct-GGUF) |
| Qwen3-0.6B | Q6_K | 495 MB | qwen3 | Apache-2.0 | [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF) |
| Hy-MT2-1.8B | IQ1_M（自量化） | 511 MB | hunyuan-dense | Apache-2.0 | bf16 权重自 [tencent/Hy-MT2-1.8B](https://huggingface.co/tencent/Hy-MT2-1.8B)，自行量化 |
| Qwen3.5-0.8B | Q4_K_M | 533 MB | qwen35（SSM+注意力混合） | Apache-2.0 | [unsloth/Qwen3.5-0.8B-GGUF](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF) |
| Qwen3-0.6B | Q8_0 | 639 MB | qwen3 | Apache-2.0 | [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF) |
| Qwen3.5-0.8B | Q6_K | 639 MB | qwen35（SSM+注意力混合） | Apache-2.0 | [unsloth/Qwen3.5-0.8B-GGUF](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF) |
| Hy-MT2-1.8B | IQ2_M（自量化） | 666 MB | hunyuan-dense | Apache-2.0 | 同上，自行量化 |
| MiniCPM5-1B | Q4_K_M | 688 MB | llama | Apache-2.0 | [openbmb/MiniCPM5-1B-GGUF](https://huggingface.co/openbmb/MiniCPM5-1B-GGUF) |
| Hy-MT2-1.8B | IQ3_XXS（自量化） | 733 MB | hunyuan-dense | Apache-2.0 | 同上，自行量化 |
| Hy-MT2-1.8B | Q3_K_S（自量化） | 831 MB | hunyuan-dense | Apache-2.0 | 同上，自行量化 |
| Hy-MT2-1.8B | Q4_K_M | 1133 MB | hunyuan-dense | Apache-2.0 | [tencent/Hy-MT2-1.8B-GGUF](https://huggingface.co/tencent/Hy-MT2-1.8B-GGUF)（官方） |
| Qwen3-0.6B | BF16 | 1198 MB | qwen3 | Apache-2.0 | [unsloth/Qwen3-0.6B-GGUF](https://huggingface.co/unsloth/Qwen3-0.6B-GGUF) |

## 二、综合排名（按测试效果排序）

综合水平 = 译文质量（成语/口语/长难句保真度）+ 可用性（漏译、幻觉、停止行为）。内存为 llama-server 实测 RSS（条件见注¹）。

| 排名 | 模型（量化） | 测试效果 | 交付/用途 | 模型体积 | 运行内存 | 速度 |
|---|---|---|---|---|---|---|
| 1 | **Hy-MT2-1.8B**（Q4_K_M） | **质量全面最佳**：零漏译零幻觉，成语处理最好（破釜沉舟→go all out、piece of cake→易如反掌、not rocket science→高深学问），长难句稳定 | ✅ 主镜像 `ai-translate:hy-mt2-1.8b` | 1133 MB（镜像 1.07 GB） | 2329 MB | 18.2 tok/s |
| 2 | **Qwen3.5-0.8B**（Q4_K_M） | **零漏译**；英→中口语优于 Qwen3-0.6B（hang in there→加油、broke→资金紧张）；中→英成语弱于 Hy-MT2 | ✅ 轻量镜像 `ai-translate:qwen35-0.8b` | 533 MB（镜像 529 MB） | 857 MB¹ | 22.4 tok/s |
| 3 | Qwen3.5-0.8B（Q6_K） | 与第 2 名同为零漏译，保真度更高但更大更慢 | 可用（未交付） | 639 MB | 4181 MB¹ | 19.4 tok/s |
| 4 | Qwen3-0.6B（Q6_K） | 良好；漏译降到 2 处 | 可用（无交付价值） | 495 MB | 1354 MB | 33.5 tok/s |
| 5 | Qwen3-0.6B（BF16） | 仍有 3 处漏译——**证明漏译与量化无关，是模型固有行为** | 归因实验 | 1198 MB | 2035 MB | 19.2 tok/s |
| 6 | Qwen3-0.6B（Q4_K_M） | 良好但 4 处漏译（英→中成语/口语整句原样返回） | 已被第 2 名取代 | 397 MB | 1472 MB | 40.1 tok/s |
| 7 | Qwen3-0.6B（Q8_0） | 5 处漏译，比 Q4 还多（波动属采样噪声） | 归因实验 | 639 MB | 1503 MB | 28.8 tok/s |
| 8 | Qwen3-0.6B（Q3_K_M） | 基本可用，网络用语开始失准；比 Q4_K_M 只省 50MB | 无交付价值 | 347 MB | 1310 MB | 43.4 tok/s |
| 9 | Qwen2.5-0.5B（Q4_K_M） | 英→中口语尚可；中→英严重失败（拉丁语乱码、中文残留译文） | ❌ 淘汰 | 491 MB | 646 MB | 39.9 tok/s |
| 10 | MiniCPM5-1B（Q4_K_M） | 译文尚可但不突出（成语失守）；**译完不停**，单句生成 119~530 token 元评论，平均 4.26s/句 | ❌ 淘汰 | 688 MB | 1569 MB | 41.9 tok/s |
| 11 | Qwen3-0.6B（UD-IQ3_XXS） | "译文："前缀泄漏、8 处漏译/空输出 | ❌ 淘汰 | 282 MB | 1134 MB | 31.1 tok/s |
| 12 | Qwen3-0.6B（UD-IQ2_M） | 崩坏：30 处漏译/元话语，错译 | ❌ 淘汰 | 269 MB | 1658 MB | 35.4 tok/s |
| 13 | Haidass-Translate-143M（Q8_0） | 速度最快但大量幻觉（虚构对话、重复循环），逐句评估 16/40 完全不可用 | ❌ 淘汰 | 188 MB | 486 MB | 98.3 tok/s |
| 14 | Gemma 3 270M IT（Q4_K_M） | **开箱不能翻译**：36 处原样返回/拒绝/破碎输出；外部实验（Benjamin Marie）同样结论——需裁词表+微调后才可用于单一方向 | ❌ 淘汰 | 253 MB | 494 MB | 66.2 tok/s |
| 15 | Qwen3-0.6B（UD-IQ1_S） | 输出乱码 | ❌ 淘汰 | 215 MB | — | — |
| 16 | Hy-MT2-1.8B（Q3_K_S，自量化） | 译文正确但 **EOS 损坏**：译完不停、重复生成（greedy/min_p/rep 均无法修复） | ❌ 淘汰 | 831 MB | — | — |
| 17 | Hy-MT2-1.8B（IQ3_XXS，自量化） | 同上 | ❌ 淘汰 | 733 MB | — | — |
| 18 | Hy-MT2-1.8B（IQ2_M，自量化） | 同上 | ❌ 淘汰 | 666 MB | — | — |
| 19 | Hy-MT2-1.8B（IQ1_M，自量化） | 输出乱码 | ❌ 淘汰 | 511 MB | — | — |
| 20 | Hy-MT2-1.8B（1.25Bit 官方） | **无法加载**：依赖的 llama.cpp STQ 内核（PR #22836）未合并；将补丁打到 master 后张量偏移仍不匹配；且补丁仅有 ARM NEON 内核，x86 只有标量回退 | ❌ 不可用于生产 | 462 MB | — | — |
| 21 | Hy-MT2-1.8B（2Bit 官方） | **无法加载，与 1.25Bit 同源**：主线 llama.cpp 缺 STQ 内核直接失败；补丁版同样报张量偏移不匹配（203248672 ≠ 203572256） | ❌ 不可用于生产 | 601 MB | — | — |

¹ 内存测量条件：llama-server `-c 4096`、默认槽位（4）、`-t 6`，WSL2 12 核。Qwen3.5 为 SSM 混合架构，SSM 循环状态与槽位成正比——**生产必须 `PARALLEL=1`**，此时 Qwen3.5-0.8B Q4_K_M 实测 857 MB。

## 三、关键结论

- **质量天花板是 Hy-MT2-1.8B Q4_K_M**（翻译专用蒸馏，Apache-2.0），技术文档场景优势比日常翻译更大（9.2 vs 6.7/6.0，见第六节）；**零漏译 + 轻量是 Qwen3.5-0.8B Q4_K_M**。两者构成本服务的双镜像交付。
- **Qwen3-0.6B 的漏译与量化无关**：Q4/Q6/Q8/BF16 漏译数在 2~5 间波动（属采样噪声），是模型对成语/口语英→中的固有回避行为，加大量化保真度解决不了。
- **0.6~1.8B 级别的质量悬崖在 4-bit 附近**：Hy-MT2 降到 3-bit 即 EOS 损坏（译完不停），Qwen3 降到 2-bit 语义崩坏（30 处漏译/元话语）。官方只为 Hy-MT2 发布 Q4/Q6/Q8 三个档位与此吻合。
- **官方 1.25Bit（440MB）与 2Bit（601MB）目前均不可用于生产**，同一三重原因见排名 20/21。若未来 STQ 内核合并且官方重新对齐 GGUF，它们值得重新评测。
- **通用小模型打不过翻译专用蒸馏**：MiniCPM5-1B（1B 级通用 SOTA）、Haidass-143M（翻译微调）、Gemma 3 270M 均不敌 1.8B 翻译专用模型。
- **超轻量档（<400MB）存在缺口**：现成模型无一人能胜任，唯一路径是用中英平行语料微调小模型（参考 Marie 对 Gemma 3 270M 的做法），属独立项目。

## 四、交付物

| 镜像 | 模型 | 压缩包 | 部署 |
|---|---|---|---|
| `ai-translate:hy-mt2-1.8b` | Hy-MT2-1.8B Q4_K_M | `ai-translate-hy-mt2-1.8b.tar.gz`（1.07 GB） | `docker load` 后 `docker run -d -p 8080:8080 ai-translate:hy-mt2-1.8b` |
| `ai-translate:qwen35-0.8b` | Qwen3.5-0.8B Q4_K_M | `ai-translate-qwen35-0.8b.tar.gz`（529 MB） | 同上，镜像名替换；**保持 `PARALLEL=1`** |

单进程同时提供：翻译 WebUI（`/`）、OpenAI 兼容 API（`/v1/chat/completions`）、健康检查（`/health`）。全部离线运行。使用说明见 [README.md](../README.md)。

## 五、通用 LLM 基础能力测试（翻译之外的复用调查）

调查目的：能否复用同一个模型顺手做简单的代码生成、文档总结、数据整理。测试任务：① 生成 IPv4 校验函数 + 自测断言（实际运行验证）；② 词频统计脚本（实际运行比对结果）；③ 约 700 字文档总结（≤150 字，按 5 个关键事实覆盖率评分）；④ 20 行杂乱联系人整理为规范 CSV（行数/电话格式/N/A 填充自动检查）。Qwen3-0.6B 与 Qwen3.5-0.8B 各测非思考/思考两种模式（思考模式 token 预算 ×4）。

| 模型（模式） | 代码：IPv4 校验 | 代码：词频统计 | 文档总结（要点覆盖） | 数据整理 20 行 | 综合评价 |
|---|---|---|---|---|---|
| Hy-MT2-1.8B（非思考，无思考模式） | ❌ 运行报错 | ❌ 输出把整段文字连成一串 | ✅ 5/5 要点，数字全对，但 246 字超出限制 | ❌ 19 行、未填 N/A | 翻译专用模型，通用能力弱（预期内），唯总结可看 |
| Qwen3-0.6B（非思考） | ❌ 语法错误 | ❌ 未转小写、计数错 | ✅ 5/5 要点（228 字） | ❌ 19 行、1 行缺列 | 总结可看，代码/整理不可靠 |
| Qwen3-0.6B（思考） | ❌ 逻辑错误（把非法 IP 断言为合法） | ❌ 忘写 import re | ✅ 4/5 要点（142 字） | ❌ 18 行 | 思考模式无补益，反多耗预算 |
| Qwen3.5-0.8B（非思考） | ❌ 1 个断言失败 | ❌ 按字符而非单词统计 | ✅ 5/5 要点（173 字，转述精准） | ⚠️ 电话/城市基本正确但表头缺失、19 行 | 三者中综合最强 |
| Qwen3.5-0.8B（思考） | ✅ **断言全部通过** | ⚠️ 计数全对但未按要求排序 | ❌ 推理耗尽预算（4681 字），正文为空 | ⚠️ N/A 正确填充 2 处，表头缺失、19 行 | 唯一能写对代码的配置，但代价是延迟 5~10 倍 |

**结论与建议**：

- **文档总结可以放心复用**：三个模型的总结能力都过关（要点覆盖 4~5/5），其中 Hy-MT2-1.8B 与 Qwen3.5-0.8B 的总结质量最好；用非思考模式即可。
- **代码生成与数据整理不可复用**：0.6~1.8B 模型在这两类需要严格指令遵循的任务上失败率过高（20 行数据整理无一全对；代码任务仅 Qwen3.5 思考模式通过 1 个）。若确有此类需求，建议走 API 大模型或升级到 ≥4B 的模型（Qwen3.5-4B 未测，按规模推算会有明显改善，但体积 ~2.5GB 起跳，超出本服务"轻量复用"范畴）。
- **思考模式在 0.6~0.8B 上的性价比低**：推理链消耗大量 token 预算（翻译服务的上下文余量会被挤占），延迟放大 5~10 倍，仅在代码类任务上带来一次质的改善。翻译场景维持关闭（镜像已内置关闭）。
- 测试脚本与原始输出：`scripts/test_general.py`、`results/general-capability.json`。

## 六、技术文档翻译实测（英→中，最贴近实际用途）

实际使用场景以查阅英文技术文档为主，日常句子翻得好不代表技术文档翻得好。选材：kernel.org 内核文档 [Documentation/PCI/pci.rst](https://www.kernel.org/doc/Documentation/PCI/pci.rst)（How To Write Linux PCI Drivers）三段代表性内容，转为 Markdown：① 驱动结构（8+7 条初始化/卸载列表，API 名密集）；② 启用设备（含 note/warning 警示块与 OS BUG 评论）；③ MMIO 与 Write Posting（含俚语 "HW weenies"、"bit banging" 和 C 代码块）。统一提示词要求保留 Markdown 结构、代码与 API 名不译、术语用业界通用译法。评分维度：术语准确 / 完整性 / 格式保持 / 忠实度，各段 10 分制。

| 模型 | 段① 驱动结构 | 段② 启用设备 | 段③ MMIO | 平均 | 典型问题（原句 → 译文） |
|---|---|---|---|---|---|
| **Hy-MT2-1.8B** | 9.5 | 9 | 9 | **9.2** | 无硬伤。小瑕疵：master abort 译作"主机中断"（应为"主设备中止"）；"Mem-Wr-Inval 是需要的但不是必需的"略拗口 |
| Qwen3.5-0.8B | 8 | 6.5 | 5.5 | **6.7** | 警告块关键句错译（丢失 `pci_request_resources()`，语义颠倒）；bit banging→"位炸弹/位乱序"；"I/O 端口空间保证写事务在到达设备之前完成"（语义译反）；"PCI 主从所有平台上的 PCI 主中断"（破碎句） |
| Qwen3-0.6B | 5 | 7 | 6 | **6.0** | CardBus→"卡串"、Express-Card→"表达卡"（虚构译名）；coherent→"对称"；Write Posting→"写入消息/写入提交"；把 "HW weenies"（硬件老手）译成"硬件单元"（歪曲）；ifdefs→"if 语句" |

**结论**：

- **技术文档场景 Hy-MT2 优势比日常翻译更大**（9.2 vs 6.7/6.0，日常翻译约为 9 vs 7 水平）。分水岭在两处：一是术语保真——MMIO/DMA/coherent（相干）/bus master（总线主设备）/write posting（写发布）这类词译错会直接误导理解，Qwen3.5 与 Qwen3-0.6B 都出现把产品名（CardBus/Express-Card）和关键概念（write posting）译飞的情况；二是警告/注释块的语义完整性——技术文档的价值恰恰在这些"废话少但关键"的段落，Qwen3.5 曾把"应先 request_resources 再 enable_device"的顺序建议译成语义颠倒的句子。
- **自查技术文档用主镜像（Hy-MT2-1.8B）**。轻量镜像（Qwen3.5-0.8B）适合日常与一般性内容，翻内核级技术文档会出现影响理解的硬伤。
- 三模型的代码块都完整保留（含注释翻译），Markdown 结构无一损坏——格式保持是三个模型共同的强项，差距全在术语与忠实度。
- 测试材料与全部译文：`scripts/techdoc_passages.md`、`results/techdoc.json`、`results/techdoc-review.md`（原文与译文对照）。

## 附录：测试方法与复现

- **测试集**：80 句 = 中→英 40 + 英→中 40，每方向含日常对话 8、技术文档 8、成语习语 8、长难句 8、网络口语 8（`scripts/sentences.zh.txt` / `sentences.en.txt`）。
- **运行时**：llama.cpp master `d7a695e`（2026-10-06），纯 CPU `-t 6`，上下文 4096；采样参数取自各模型官方推荐（Hy-MT2：temp 0.7 / top_p 0.6 / top_k 20 / rep 1.05；Qwen3/3.5：temp 0.7 / top_p 0.8，`--chat-template-kwargs {"enable_thinking":false}` 关思考；Gemma3：temp 1.0 / top_p 0.95 / top_k 64；Haidass：greedy + rep 1.1）。
- **评测方式**：`scripts/bench_translate.py` 逐个启动 llama-server 跑全量句子，记录译文、延迟、生成速度、RSS；漏译按"空输出 / 原样返回 / 拒绝与元话语"三类自动判定；质量排名辅以人工逐句评估（[compare.md](compare.md)）。技术文档实测用 `scripts/test_techdoc.py`（原文与全部译文对照见 [techdoc-review.md](techdoc-review.md)）。
- **复现**：
  ```bash
  python3 scripts/bench_translate.py                # 全量评测
  python3 scripts/bench_translate.py --limit 3      # 快速验证
  python3 scripts/test_stopping.py <port> <标注>    # 停止行为对照
  ```
- **自量化复现**（Hy-MT2 低位宽）：bf16 权重 4.1GB → `convert_hf_to_gguf.py`（约 2 分钟）→ `llama-imatrix`（中英校准文本，约 4 分钟）→ `llama-quantize --imatrix`（每档 1~2 分钟）；Python 3.12 + torch CPU + gguf/transformers，无需 root。
