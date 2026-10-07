#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""通用 LLM 基础能力测试：代码生成（2，运行验证）、文档总结（1）、数据整理（1）。
对支持思考模式的模型分别测非思考/思考两种模式。
结果写入 results/general-capability.json 与 results/general.md。
"""
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS_DIR = os.path.join(BASE, "models")
RESULTS_DIR = os.path.join(BASE, "results")
SCRIPTS = os.path.join(BASE, "scripts")
LLAMA_SERVER = os.environ.get("LLAMA_SERVER", os.path.join(BASE, "llama.cpp-repo", "build", "bin", "llama-server"))
THINK_RE = re.compile(r"<think>(.*?)</think>", re.DOTALL)

NO_THINK_KW = ["--chat-template-kwargs", '{"enable_thinking": false}']


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

SUMMARY_DOC = read(os.path.join(SCRIPTS, "summary_source.txt"))
CONTACTS = read(os.path.join(SCRIPTS, "contacts_raw.txt")).strip()
WORDFREQ = read(os.path.join(SCRIPTS, "wordfreq_input.txt"))

# ---- 任务定义 ---------------------------------------------------------------
CODE_IP = {
    "id": "code-ipv4",
    "name": "代码生成：IPv4 校验函数 + 自测断言",
    "prompt": ("用 Python 写一个函数 is_valid_ipv4(s)，判断字符串是否是合法的 IPv4 地址："
               "正好四段、每段是 0-255 的十进制数字、不允许前导零（如 01 非法）。"
               "只输出代码，不要解释；代码末尾用 assert 写 6 个测试（至少 2 个非法用例，例如 '256.1.1.1'、'192.168.01.1'），"
               "全部通过后打印 OK。"),
    "max_tokens": 1024,
}
CODE_FREQ = {
    "id": "code-wordfreq",
    "name": "代码生成：词频统计脚本",
    "prompt": ("写一个 Python 脚本：读取当前目录下的 input.txt（UTF-8），把文本按非字母数字字符切分成单词并转为小写，"
               "统计词频，按出现次数降序输出前 5 个，每行格式为 `单词 次数`（次数相同按字母序）。只输出代码，不要解释。"),
    "max_tokens": 1024,
}
SUMMARY = {
    "id": "doc-summary",
    "name": "文档总结（约 700 字 → ≤150 字）",
    "prompt": ("用不超过 150 字总结下面这份文档的要点，覆盖关键事实，只输出总结：\n\n" + SUMMARY_DOC),
    "max_tokens": 640,
    "expect_facts": ["2026 年 8 月 28 日", "400 毫秒", "70 台", "2027 年 3 月 31 日", "1.8 秒"],
}
DATA_CLEAN = {
    "id": "data-contacts",
    "name": "数据整理：20 行杂乱联系人 → CSV",
    "prompt": ("把下面的联系人记录整理成 CSV 文本，表头为 姓名,电话,城市；"
               "电话去掉空格、连字符等分隔符，保留 11 位数字；城市缺失填 N/A；保持原有顺序，不要去重。只输出 CSV 内容。\n\n" + CONTACTS),
    "max_tokens": 1024,
}
TASKS = [CODE_IP, CODE_FREQ, SUMMARY, DATA_CLEAN]

# ---- 模型配置 ---------------------------------------------------------------
BASE_QWEN_ARGS = ["--jinja"]
MODELS = {
    "Hy-MT2-1.8B": [
        {"mode": "非思考", "server_args": ["--jinja"], "sampling": {"temperature": 0}, "no_system": True},
    ],
    "Qwen3-0.6B": [
        {"mode": "非思考", "server_args": BASE_QWEN_ARGS + NO_THINK_KW, "sampling": {"temperature": 0}},
        {"mode": "思考", "server_args": BASE_QWEN_ARGS, "sampling": {"temperature": 0.6, "top_p": 0.95}},
    ],
    "Qwen3.5-0.8B": [
        {"mode": "非思考", "server_args": BASE_QWEN_ARGS + NO_THINK_KW, "sampling": {"temperature": 0}},
        {"mode": "思考", "server_args": BASE_QWEN_ARGS, "sampling": {"temperature": 0.6, "top_p": 0.95}},
    ],
}
GGUF = {
    "Hy-MT2-1.8B": "Hy-MT2-1.8B-Q4_K_M.gguf",
    "Qwen3-0.6B": "Qwen3-0.6B-Q4_K_M.gguf",
    "Qwen3.5-0.8B": "Qwen3.5-0.8B-Q4_K_M.gguf",
}
SYSTEM = "你是一个乐于助人的AI助手。"


def http_json(url, payload=None, timeout=300):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


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


def chat(port, prompt, sampling, max_tokens):
    body = {"messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}],
            "max_tokens": max_tokens}
    body.update(sampling)
    with urllib.request.urlopen(urllib.request.Request(
            "http://127.0.0.1:%d/v1/chat/completions" % port,
            data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}), timeout=600) as r:
        d = json.loads(r.read().decode())
    msg = d["choices"][0]["message"]
    reasoning = getattr(msg, "get", lambda *_: None)("reasoning_content") if isinstance(msg, dict) else None
    return msg.get("content") or "", reasoning or ""


def extract_code(text):
    m = re.findall(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
    return (m[0] if m else text).strip()


def check_code_ip(text, tmpdir):
    code = extract_code(text)
    path = os.path.join(tmpdir, "ipv4.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code + "\n")
    p = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=30, cwd=tmpdir)
    if p.returncode == 0:
        ok_print = "OK" in p.stdout
        return True, "断言全部通过" + ("" if ok_print else "（逻辑正确但漏了打印 OK）")
    return False, "exit=%d stderr=%r" % (p.returncode, p.stderr.strip()[-200:])


def check_code_freq(text, tmpdir):
    code = extract_code(text)
    path = os.path.join(tmpdir, "wordfreq.py")
    with open(path, "w", encoding="utf-8") as f:
        f.write(code + "\n")
    with open(os.path.join(tmpdir, "input.txt"), "w", encoding="utf-8") as f:
        f.write(WORDFREQ)
    p = subprocess.run([sys.executable, path], capture_output=True, text=True, timeout=30, cwd=tmpdir)
    if p.returncode != 0:
        return False, "exit=%d stderr=%r" % (p.returncode, p.stderr.strip()[-200:])
    # 参考实现
    words = [w.lower() for w in re.split(r"[^a-z0-9]+", WORDFREQ.lower()) if w]
    from collections import Counter
    top = sorted(Counter(words).items(), key=lambda kv: (-kv[1], kv[0]))[:5]
    expect = "\n".join("%s %d" % (w, c) for w, c in top)
    got = "\n".join(l.strip() for l in p.stdout.strip().splitlines()[:5]).lower()
    return got == expect.lower(), "期望=%r 实际=%r" % (expect.replace("\n", " | "), p.stdout.strip().replace("\n", " | ")[:120])


def check_summary(text, _):
    norm = re.sub(r"\s+", "", text)
    facts = [f for f in SUMMARY["expect_facts"] if re.sub(r"\s+", "", f) in norm]
    return len(facts), "命中关键事实 %d/5: %s | 长度 %d 字" % (len(facts), facts, len(text.strip()))


def check_contacts(text, _):
    lines = [l for l in text.strip().splitlines() if l.strip()]
    errors = []
    if not lines or not lines[0].replace(" ", "").startswith("姓名,电话,城市"):
        errors.append("表头缺失/错误")
    rows = lines[1:] if lines else []
    if len(rows) != 20:
        errors.append("行数=%d≠20" % len(rows))
    na = 0
    for i, l in enumerate(rows):
        parts = [c.strip() for c in l.split(",")]
        if len(parts) != 3:
            errors.append("行%d列数=%d" % (i + 1, len(parts))); continue
        if not re.fullmatch(r"\d{11}", parts[1]):
            errors.append("行%d电话=%r" % (i + 1, parts[1]))
        if parts[2] == "N/A":
            na += 1
    ok = not errors
    return ok, ("N/A=%d " % na) + ("; ".join(errors[:4]) if errors else "全部通过")


CHECKERS = {"code-ipv4": check_code_ip, "code-wordfreq": check_code_freq,
            "doc-summary": check_summary, "data-contacts": check_contacts}


def run_config(key, mode_cfg, port):
    cmd = [LLAMA_SERVER, "-m", os.path.join(MODELS_DIR, GGUF[key]),
           "--host", "127.0.0.1", "--port", str(port), "-c", "8192", "-t", "6", "--jinja"] + mode_cfg["server_args"]
    if mode_cfg.get("no_system"):
        pass
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    try:
        if not wait_health(port, proc):
            return {"error": "启动失败"}
        out = {}
        tmpdir = os.path.join(RESULTS_DIR, "general-tmp")
        os.makedirs(tmpdir, exist_ok=True)
        for task in TASKS:
            t0 = time.time()
            budget = task["max_tokens"] * (4 if mode_cfg["mode"] == "思考" else 1)
            try:
                content, reasoning = chat(port, task["prompt"], mode_cfg["sampling"], budget)
            except Exception as e:
                out[task["id"]] = {"name": task["name"], "error": str(e)}
                continue
            wall = time.time() - t0
            res = CHECKERS[task["id"]](content, tmpdir)
            score, detail = (res if isinstance(res, tuple) else (None, str(res)))
            out[task["id"]] = {
                "name": task["name"], "score": score, "detail": detail,
                "wall": round(wall, 1),
                "has_think": bool(THINK_RE.search(content or "")),
                "reasoning_len": len(reasoning or ""),
                "output": (content or "")[:8000],
            }
            print("  %-13s %-8s %6.1fs  %s %s" % (task["id"], mode_cfg["mode"], wall, score, detail[:80]), flush=True)
        return out
    finally:
        proc.send_signal(signal.SIGTERM)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main():
    only = sys.argv[1].split(",") if len(sys.argv) > 1 else list(MODELS)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    all_results = {}
    path = os.path.join(RESULTS_DIR, "general-capability.json")
    if os.path.exists(path):
        all_results = json.load(open(path, encoding="utf-8"))
    port = 8580
    for key in only:
        for mode_cfg in MODELS[key]:
            label = "%s/%s" % (key, mode_cfg["mode"])
            print("[%s] 启动" % label, flush=True)
            all_results.setdefault(key, {})[mode_cfg["mode"]] = run_config(key, mode_cfg, port)
            port += 1
            with open(path, "w", encoding="utf-8") as f:
                json.dump(all_results, f, ensure_ascii=False, indent=1)
    print("结果已写入", path)


if __name__ == "__main__":
    main()
