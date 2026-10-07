#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技术文档翻译实测：kernel.org PCI 文档节选（Markdown），候选模型英→中。"""
import json
import os
import re
import signal
import subprocess
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE, "models")
RESULTS_DIR = os.path.join(BASE, "results")
LLAMA_SERVER = os.environ.get("LLAMA_SERVER", os.path.join(BASE, "llama.cpp-repo", "build", "bin", "llama-server"))
NO_THINK_KW = ["--chat-template-kwargs", '{"enable_thinking": false}']
SYSTEM = "你是一个专业的技术文档翻译引擎，只输出译文。"
USER_TMPL = ("将以下 Markdown 技术文档翻译成中文。要求：保留 Markdown 结构（标题、列表、代码块、引用）；"
             "代码、函数名、API 名、宏名保持英文原样；术语使用业界通用译法；只输出译文。\n\n{md}")

PASSAGES = re.split(r"===== PASSAGE \d+ =====\n", open(os.path.join(SCRIPTS := os.path.join(BASE, "scripts"),
             "techdoc_passages.md"), encoding="utf-8").read())[1:]

MODELS = {
    "Hy-MT2-1.8B": {"gguf": "Hy-MT2-1.8B-Q4_K_M.gguf", "server_args": ["--jinja"],
                    "sampling": {"temperature": 0.7, "top_p": 0.6, "top_k": 20, "repeat_penalty": 1.05}},
    "Qwen3.5-0.8B": {"gguf": "Qwen3.5-0.8B-Q4_K_M.gguf", "server_args": ["--jinja"] + NO_THINK_KW,
                     "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20}},
    "Qwen3-0.6B": {"gguf": "Qwen3-0.6B-Q4_K_M.gguf", "server_args": ["--jinja"] + NO_THINK_KW,
                   "sampling": {"temperature": 0.7, "top_p": 0.8, "top_k": 20}},
}


def wait_health(port, proc, timeout=180):
    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            with urllib.request.urlopen("http://127.0.0.1:%d/health" % port, timeout=2) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False


def run_model(key, cfg, port):
    cmd = [LLAMA_SERVER, "-m", os.path.join(MODELS_DIR, cfg["gguf"]), "--host", "127.0.0.1",
           "--port", str(port), "-c", "8192", "-t", "6", "--jinja"] + cfg["server_args"]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    out = {}
    try:
        if not wait_health(port, proc):
            return {"error": "启动失败"}
        for i, md in enumerate(PASSAGES, 1):
            body = {"messages": [{"role": "system", "content": SYSTEM},
                                 {"role": "user", "content": USER_TMPL.format(md=md)}],
                    "max_tokens": 3000}
            body.update(cfg["sampling"])
            t0 = time.time()
            with urllib.request.urlopen(urllib.request.Request(
                    "http://127.0.0.1:%d/v1/chat/completions" % port,
                    data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}),
                    timeout=600) as r:
                d = json.loads(r.read().decode())
            content = (d["choices"][0]["message"].get("content") or "").strip()
            out["passage%d" % i] = {
                "wall": round(time.time() - t0, 1),
                "tokens": d.get("usage", {}).get("completion_tokens", 0),
                "text": content,
            }
            print("  passage%d %5.1fs %4d tok  %d 字" % (i, out["passage%d" % i]["wall"],
                  out["passage%d" % i]["tokens"], len(content)), flush=True)
        return out
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    port = 8590
    results = {}
    for key, cfg in MODELS.items():
        print("[%s]" % key, flush=True)
        results[key] = run_model(key, cfg, port)
        port += 1
    with open(os.path.join(RESULTS_DIR, "techdoc.json"), "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    # 汇总 markdown，便于人工评审
    with open(os.path.join(RESULTS_DIR, "techdoc-review.md"), "w", encoding="utf-8") as f:
        for i in range(1, len(PASSAGES) + 1):
            f.write("# PASSAGE %d 原文\n\n" % i)
            f.write(PASSAGES[i - 1])
            f.write("\n\n")
            for key in MODELS:
                f.write("## %s\n\n" % key)
                f.write(results[key].get("passage%d" % i, {}).get("text", "(失败)"))
                f.write("\n\n---\n\n")
    print("已生成 results/techdoc.json 与 results/techdoc-review.md")


if __name__ == "__main__":
    main()
