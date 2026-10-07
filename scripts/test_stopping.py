#!/usr/bin/env python3
"""量化档位停止行为对照实验：同一句子，不同采样参数。"""
import json
import sys
import urllib.request

port = int(sys.argv[1]) if len(sys.argv) > 1 else 8562
model_note = sys.argv[2] if len(sys.argv) > 2 else ""

CASES = {
    "greedy": {"temperature": 0},
    "官方参数": {"temperature": 0.7, "top_p": 0.6, "top_k": 20, "repeat_penalty": 1.05},
    "官方参数+min_p": {"temperature": 0.7, "top_p": 0.6, "top_k": 20, "repeat_penalty": 1.05, "min_p": 0.1},
    "官方参数+rep1.1": {"temperature": 0.7, "top_p": 0.6, "top_k": 20, "repeat_penalty": 1.1},
}
TEXT = "今天天气不错，我们出去走走吧。"

def ask(sampling):
    body = {
        "messages": [{"role": "user", "content": "将以下文本翻译为 `英文`，注意只需要输出翻译后的结果，不要额外解释：\n" + TEXT}],
        "max_tokens": 80,
    }
    body.update(sampling)
    req = urllib.request.Request("http://127.0.0.1:%d/v1/chat/completions" % port,
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        d = json.loads(r.read().decode())
    return d["choices"][0]["message"]["content"], d["usage"]["completion_tokens"]

for name, s in CASES.items():
    out, n = ask(s)
    print("[%s%s] %d tok: %r" % (model_note, name, n, out[:120]))
