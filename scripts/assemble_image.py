#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""手动组装 docker 镜像 tar（docker load 兼容格式）。

为什么不用 docker build：本机无 root/无 /etc/subuid，容器引擎无法解压含外来 UID 的基础镜像层。
本脚本直接从镜像源拉取 debian:bookworm-slim 的层 blob（字节原样保留），叠加应用层，
生成 docker save 同构的 tar，任何正常权限的 docker 都能 load。
"""
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
import urllib.request

MIRROR = "https://docker.m.daocloud.io"
BASE_IMAGE = "library/debian"
BASE_TAG = "bookworm-slim"
ACCEPT = ", ".join([
    "application/vnd.docker.distribution.manifest.v2+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.oci.image.index.v1+json",
])


def http(url, headers=None):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def registry_get(path, accept):
    """带匿名 token 的 registry 请求（daocloud 等镜像源要求）。"""
    tok = json.loads(http(f"{MIRROR}/token?service=registry.docker.io&scope=repository:{BASE_IMAGE}:pull"))
    h = {"Accept": accept, "Authorization": "Bearer " + tok["token"]}
    return http(f"{MIRROR}{path}", h)


def build_additions_layer(app_dir, entries):
    """把应用文件打成层 tar（uid/gid 置 0，与真实 docker build 行为一致）。
    注意：gettarinfo 对软链会生成 SYMTYPE 条目，容器内链接目标不存在即坏链，
    因此所有源文件先 realpath 解引用为真实文件。"""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for path, arcname, exec_flag in entries:
            full = os.path.realpath(os.path.join(app_dir, path))
            ti = tf.gettarinfo(full, arcname=arcname)
            ti.uid = ti.gid = 0
            ti.uname = ti.gname = "root"
            ti.mode = 0o755 if exec_flag else 0o644
            if ti.isfile():
                with open(full, "rb") as f:
                    tf.addfile(ti, f)
            else:
                tf.addfile(ti)
    return buf.getvalue()


def assemble(tag, base_layer_path, additions_tar, out_path):
    base_diff = "sha256:" + hashlib.sha256(open(base_layer_path, "rb").read()).hexdigest()
    add_diff = "sha256:" + hashlib.sha256(additions_tar).hexdigest()
    base_id, add_id = base_diff.split(":")[1], add_diff.split(":")[1]

    cfg = {
        "architecture": "amd64",
        "os": "linux",
        "config": {
            "Env": ["PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "PORT=8080", "CTX=8192"] + [
                e for e in [os.environ.get("EXTRA_ENV")] if e],
            "Entrypoint": ["/app/entrypoint.sh"],
            "WorkingDir": "/",
            "User": "1000",
            "ExposedPorts": {"8080/tcp": {}},
        },
        "rootfs": {"type": "layers", "diff_ids": [base_diff, add_diff]},
        "history": [
            {"created_by": "ubuntu:22.04 base rootfs"},
            {"created_by": "ai-translate: llama-server + webui + model"},
        ],
    }
    cfg_bytes = json.dumps(cfg, indent=1).encode()
    cfg_name = hashlib.sha256(cfg_bytes).hexdigest() + ".json"

    manifest = [{
        "Config": cfg_name,
        "RepoTags": [tag],
        "Layers": [f"{base_id}/layer.tar", f"{add_id}/layer.tar"],
    }]
    repos_path, repo_tag = tag.split(":")
    repositories = {repos_path: {repo_tag: add_id}}

    with tarfile.open(out_path, "w") as out:
        def add_bytes(name, data, mode=0o644):
            ti = tarfile.TarInfo(name)
            ti.size = len(data)
            ti.mode = mode
            ti.uid = ti.gid = 0
            out.addfile(ti, io.BytesIO(data))

        add_bytes(cfg_name, cfg_bytes)
        add_bytes("manifest.json", json.dumps(manifest, indent=1).encode())
        add_bytes("repositories", json.dumps(repositories, indent=1).encode())
        # 基础层：blob 字节原样写入（解压后的未压缩 tar）
        with open(base_layer_path, "rb") as f:
            ti = tarfile.TarInfo(f"{base_id}/layer.tar")
            ti.size = os.path.getsize(base_layer_path)
            ti.mode = 0o644
            out.addfile(ti, f)
        add_bytes(f"{add_id}/layer.tar", additions_tar)
    print("镜像已生成: %s (%.0f MB)" % (out_path, os.path.getsize(out_path) / 1e6))
    print("diff_ids:", base_diff[:20], add_diff[:20])


def fetch_base(workdir, tarball):
    """把基础 rootfs tarball 解压为未压缩层 tar（ubuntu-base 官方 rootfs，无需 registry）。"""
    raw = gzip.decompress(open(tarball, "rb").read())
    p = os.path.join(workdir, "base-layer.tar")
    with open(p, "wb") as f:
        f.write(raw)
    print("基础层已就绪 %s (%.0f MB)" % (p, len(raw) / 1e6))
    return p


def pick_server_bin(app_dir):
    """定位编译产物：优先静态版（llama-server-static），兼容普通构建命名；可用 LLAMA_SERVER_BIN 覆盖。"""
    if os.environ.get("LLAMA_SERVER_BIN"):
        return os.environ["LLAMA_SERVER_BIN"]
    for cand in ("llama.cpp-repo/build/bin/llama-server-static",
                 "llama.cpp-repo/build/bin/llama-server"):
        if os.path.isfile(os.path.join(app_dir, cand)):
            return cand
    raise FileNotFoundError("未找到 llama-server：请先按 README「方式二」编译，或用 LLAMA_SERVER_BIN 环境变量指定路径")


if __name__ == "__main__":
    app = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    out = sys.argv[2] if len(sys.argv) > 2 else "/tmp/ai-translate.tar"
    work = "/tmp/ai-translate-build"
    os.makedirs(work, exist_ok=True)
    base_tarball = os.environ.get("BASE_TARBALL", "/tmp/ai-translate-build/ubuntu-base.tar.gz")
    base_layer = fetch_base(work, base_tarball)
    entries = [
        (pick_server_bin(app), "app/llama-server", True),
        ("web/index.html", "app/web/index.html", False),
        ("web/chat.html", "app/web/chat.html", False),
        ("docker/entrypoint.sh", "app/entrypoint.sh", True),
        (os.environ.get("LIBGOMP", "/lib/x86_64-linux-gnu/libgomp.so.1"), "app/lib/libgomp.so.1", False),
        (os.environ.get("MODEL_SRC"), "app/model.gguf", False),
    ]
    add = build_additions_layer(app, entries)
    assemble(sys.argv[3] if len(sys.argv) > 3 else "ai-translate:local", base_layer, add, out)
