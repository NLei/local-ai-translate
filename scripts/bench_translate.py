#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""多模型中英翻译评测：逐个启动 llama-server，跑同一测试集，产出 JSON 与对比 Markdown。

用法:
  python3 scripts/bench_translate.py                     # 全部模型全量句
  python3 scripts/bench_translate.py --models Hy-MT2-1.8B --limit 3
"""
import argparse
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE, "models")
RESULTS_DIR = os.path.join(BASE, "results")
LLAMA_SERVER = os.environ.get("LLAMA_SERVER", os.path.join(BASE, "llama.cpp-repo", "build", "bin", "llama-server"))
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)

# 各模型配置：采样参数/提示词均取自各官方仓库推荐值
MODELS = {
    "Hy-MT2-1.8B": {
        "gguf": "Hy-MT2-1.8B-Q4_K_M.gguf",
        "server_args": ["--jinja"],
        "sampling": {"temperature": 0.7, "top_p": 0.6, "top_k": 20, "repeat_penalty": 1.05},
        "system": None,
        "prompt": {
            "zh2en": "将以下文本翻译为 `英文`，注意只需要输出翻译后的结果，不要额外解释：\n{text}",
            "en2zh": "将以下文本翻译为 `中文`，注意只需要输出翻译后的结果，不要额外解释：\n{text}",
        },
    },
    "Haidass-143M": {
        "gguf": "haidass-translate-143m-q8_0.gguf",
        # qwen3 架构默认模板会预填 think 块导致输出为空，改用普通 chatml
        "server_args": ["--chat-template", "chatml"],
        "sampling": {"temperature": 0.0, "repeat_penalty": 1.1},
        "system": None,
        "prompt": {
            "zh2en": "将以下文本翻译为英文：\n{text}",
            "en2zh": "将以下文本翻译为中文：\n{text}",
        },
    },
    "Qwen3-0.6B": {
        "gguf": "Qwen3-0.6B-Q4_K_M.gguf",
        # --reasoning-budget 0 对该模型无效（仍输出思考过程），用模板参数关闭思考模式
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "MiniCPM5-1B": {
        "gguf": "MiniCPM5-1B-Q4_K_M.gguf",
        "server_args": ["--jinja"],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Qwen3-0.6B-Q6": {
        "gguf": "Qwen3-0.6B-Q6_K.gguf",
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Qwen3-0.6B-Q8": {
        "gguf": "Qwen3-0.6B-Q8_0.gguf",
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Qwen3-0.6B-BF16": {
        "gguf": "Qwen3-0.6B-BF16.gguf",
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Qwen3.5-0.8B": {
        "gguf": "Qwen3.5-0.8B-Q4_K_M.gguf",
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Qwen3.5-0.8B-Q6": {
        "gguf": "Qwen3.5-0.8B-Q6_K.gguf",
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Gemma3-270M": {
        "gguf": "gemma-3-270m-it-Q4_K_M.gguf",
        "server_args": ["--jinja"],
        # Gemma3 官方推荐采样参数
        "sampling": {"temperature": 1.0, "top_p": 0.95, "top_k": 64},
        "system": None,
        "prompt": {
            "zh2en": "Translate the following text into English. Output only the translation without any explanation:\n{text}",
            "en2zh": "Translate the following text into Chinese. Output only the translation without any explanation:\n{text}",
        },
    },
    "Qwen3-Q3": {
        "gguf": "Qwen3-0.6B-Q3_K_M.gguf",
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Qwen3-IQ3": {
        "gguf": "Qwen3-0.6B-UD-IQ3_XXS.gguf",
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Qwen3-IQ2": {
        "gguf": "Qwen3-0.6B-UD-IQ2_M.gguf",
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Qwen3-IQ1": {
        "gguf": "Qwen3-0.6B-UD-IQ1_S.gguf",
        "server_args": ["--jinja", "--chat-template-kwargs", '{"enable_thinking": false}'],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
    "Qwen2.5-0.5B": {
        "gguf": "qwen2.5-0.5b-instruct-q4_k_m.gguf",
        "server_args": [],
        "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20},
        "system": "你是一个中英翻译引擎，只输出译文，不要任何解释。",
        "prompt": {
            "zh2en": "请将以下内容翻译成英文，只输出译文：\n{text}",
            "en2zh": "请将以下内容翻译成中文，只输出译文：\n{text}",
        },
    },
}

DIRECTIONS = ("zh2en", "en2zh")
SENT_FILES = {"zh2en": "sentences.zh.txt", "en2zh": "sentences.en.txt"}


def load_sentences(direction):
    path = os.path.join(BASE, "scripts", SENT_FILES[direction])
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def http_json(url, payload=None, timeout=300):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def wait_health(port, proc, timeout=180):
    url = "http://127.0.0.1:%d/health" % port
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def rss_mb(pid):
    try:
        with open("/proc/%d/status" % pid, encoding="utf-8") as f:
            for ln in f:
                if ln.startswith("VmRSS:"):
                    return int(ln.split()[1]) / 1024.0
    except OSError:
        pass
    return 0.0


def translate(port, text, cfg, direction):
    body = {
        "messages": [],
        "max_tokens": 1024,
    }
    if cfg["system"]:
        body["messages"].append({"role": "system", "content": cfg["system"]})
    body["messages"].append({"role": "user", "content": cfg["prompt"][direction].format(text=text)})
    body.update(cfg["sampling"])
    t0 = time.time()
    resp = http_json("http://127.0.0.1:%d/v1/chat/completions" % port, body)
    wall = time.time() - t0
    content = resp["choices"][0]["message"]["content"] or ""
    content = THINK_RE.sub("", content).strip()
    n_tok = resp.get("usage", {}).get("completion_tokens", 0)
    return content, wall, n_tok


def run_model(key, cfg, port, limit):
    gguf = os.path.join(MODELS_DIR, cfg["gguf"])
    cmd = [
        LLAMA_SERVER, "-m", gguf, "--host", "127.0.0.1", "--port", str(port),
        "-c", "4096", "-t", str(os.environ.get("BENCH_THREADS", "6")),
    ] + cfg["server_args"]
    print("[%s] 启动: %s" % (key, " ".join(os.path.basename(c) if i < 2 else c for i, c in enumerate(cmd))), flush=True)
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        if not wait_health(port, proc):
            print("[%s] 服务启动失败，跳过" % key, flush=True)
            return None
        # 预热
        translate(port, "你好，世界。", cfg, "zh2en")
        records = {d: [] for d in DIRECTIONS}
        for direction in DIRECTIONS:
            sentences = load_sentences(direction)
            if limit:
                sentences = sentences[:limit]
            for i, src in enumerate(sentences, 1):
                try:
                    out, wall, n_tok = translate(port, src, cfg, direction)
                except Exception as e:
                    out, wall, n_tok = "<ERROR: %s>" % e, 0.0, 0
                records[direction].append({"src": src, "out": out, "wall": round(wall, 3), "tok": n_tok})
                speed = ("%.1f tok/s" % (n_tok / wall)) if (n_tok and wall) else "-"
                print("  %s %2d/%d %6.2fs %10s  %s" % (direction, i, len(sentences), wall, speed, (out[:40] + "…") if len(out) > 40 else out), flush=True)
        walls = [r["wall"] for d in DIRECTIONS for r in records[d]]
        toks = [r["tok"] for d in DIRECTIONS for r in records[d]]
        summary = {
            "avg_latency_s": round(sum(walls) / len(walls), 3),
            "avg_tok_s": round(sum(toks) / sum(walls), 2) if sum(walls) else 0,
            "rss_mb": round(rss_mb(proc.pid), 1),
        }
        print("[%s] 完成: 平均 %ss, %s tok/s, RSS %sMB" % (key, summary["avg_latency_s"], summary["avg_tok_s"], summary["rss_mb"]), flush=True)
        return {"summary": summary, "records": records}
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def esc(s):
    return s.replace("|", "\\|").replace("\n", " ")


def write_compare(results, out_path):
    keys = list(results)
    lines = ["# 中英翻译评测对比", ""]
    lines += ["| 模型 | 平均延迟(s) | 生成速度(tok/s) | 内存(MB) |", "|---|---|---|---|"]
    for k in keys:
        s = results[k]["summary"]
        lines.append("| %s | %s | %s | %s |" % (k, s["avg_latency_s"], s["avg_tok_s"], s["rss_mb"]))
    for direction, label in (("zh2en", "中 → 英"), ("en2zh", "英 → 中")):
        lines += ["", "## %s" % label, ""]
        head = "| # | 源句 | " + " | ".join(keys) + " |"
        lines += [head, "|" + "---|" * (len(keys) + 2)]
        n = len(results[keys[0]]["records"][direction])
        for i in range(n):
            src = results[keys[0]]["records"][direction][i]["src"]
            row = [str(i + 1), esc(src)]
            for k in keys:
                row.append(esc(results[k]["records"][direction][i]["out"]))
            lines.append("| " + " | ".join(row) + " |")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default=",".join(MODELS), help="逗号分隔的模型 key")
    ap.add_argument("--limit", type=int, default=0, help="每方向最多测试句数，0=全部")
    ap.add_argument("--port-base", type=int, default=8551)
    args = ap.parse_args()

    os.makedirs(RESULTS_DIR, exist_ok=True)
    selected = [k for k in args.models.split(",") if k]
    for k in selected:
        if k not in MODELS:
            sys.exit("未知模型: %s (可选: %s)" % (k, ",".join(MODELS)))

    results, meta = {}, {}
    for idx, key in enumerate(selected):
        port = args.port_base + idx
        res = run_model(key, MODELS[key], port, args.limit)
        if res:
            results[key] = res
            meta[key] = {"gguf": MODELS[key]["gguf"], "server_args": MODELS[key]["server_args"],
                         "sampling": MODELS[key]["sampling"], "port": port}
            with open(os.path.join(RESULTS_DIR, "bench-%s.json" % key), "w", encoding="utf-8") as f:
                json.dump({"meta": meta[key], **res}, f, ensure_ascii=False, indent=1)

    if len(results) >= 2:
        write_compare(results, os.path.join(RESULTS_DIR, "compare.md"))
        print("对比文档: results/compare.md")
    for k in results:
        with open(os.path.join(RESULTS_DIR, "bench-%s.json" % k), "w", encoding="utf-8") as f:
            json.dump({"meta": meta[k], **results[k]}, f, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
