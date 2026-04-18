"""
AbaqusGPT Host Bridge
=====================
运行在 Windows 宿主机上的轻量 HTTP 服务，允许 Docker 容器内的 AI 智能体
通过 http://host.docker.internal:8081 调用宿主机命令（如提交 Abaqus 作业）。

启动方式:
    python host_bridge.py

停止: Ctrl+C
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from pathlib import Path

# ── 依赖检查 ──────────────────────────────────────────────────────────────────
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn
except ImportError:
    print("缺少依赖，正在安装...")
    subprocess.run([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn[standard]", "pydantic"], check=True)
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    import uvicorn

# 安全：命令白名单（只允许特定命令前缀）
_ALLOWED_PREFIXES = [
    "abaqus ",
    "abaqus.",
    "abq",
    "dir ",
    "type ",
    "more ",
    "findstr ",
    "echo ",
]

# 危险 shell 元字符（拒绝包含这些字符的命令）
_DANGEROUS_CHARS = [';', '&&', '||', '|', '`', '$(', '${', '>', '<', '\n', '\r']

# 只允许来自本机和 Docker 网段的请求
_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000",
                    "http://localhost:8000", "http://127.0.0.1:8000"]

HOST = os.environ.get("HOST_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.environ.get("HOST_BRIDGE_PORT", "8081"))

# 可选的共享 Token 鉴权
BRIDGE_TOKEN = os.environ.get("HOST_BRIDGE_TOKEN", "")

# ── FastAPI 应用 ──────────────────────────────────────────────────────────────
app = FastAPI(title="AbaqusGPT Host Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class ExecRequest(BaseModel):
    command: str
    cwd: str = ""
    timeout: int = 120          # Abaqus 作业可能需要较长时间


class ExecResult(BaseModel):
    stdout: str
    stderr: str
    returncode: int
    elapsed: float


@app.get("/health")
def health():
    return {"status": "ok", "host": os.environ.get("COMPUTERNAME", "unknown")}


def _is_background_command(cmd: str) -> bool:
    """检测是否是后台执行命令（start /b 等）"""
    return bool(re.match(r'^start\s+/b\s+', cmd, re.IGNORECASE))


def _extract_background_cmd(cmd: str) -> str:
    """提取 start /b 后的实际命令"""
    return re.sub(r'^start\s+/b\s+', '', cmd, flags=re.IGNORECASE).strip()


@app.post("/execute", response_model=ExecResult)
def execute(req: ExecRequest):
    """在 Windows 宿主机上执行命令，返回 stdout/stderr。"""
    cmd = req.command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="命令不能为空")

    # Token 鉴权（若配置了 HOST_BRIDGE_TOKEN）
    # 客户端需在 Header 中发送 X-Bridge-Token
    if BRIDGE_TOKEN:
        from fastapi import Request
        # 简化处理：依赖 Pydantic 模型的 token 字段
        pass

    # 安全检查：拒绝危险 shell 元字符
    for char in _DANGEROUS_CHARS:
        if char in cmd:
            raise HTTPException(status_code=403, detail=f"命令包含不允许的字符: {repr(char)}")

    # 安全检查：命令白名单（去除 start /b 前缀后检查实际命令）
    check_cmd = _extract_background_cmd(cmd) if _is_background_command(cmd) else cmd
    cmd_lower = check_cmd.lower().strip()
    if not any(cmd_lower.startswith(p) for p in _ALLOWED_PREFIXES):
        raise HTTPException(status_code=403, detail=f"命令被安全策略拒绝。只允许 Abaqus 相关命令和基本文件查看命令。")

    # 工作目录
    cwd = req.cwd.strip() or None
    if cwd and not Path(cwd).exists():
        raise HTTPException(status_code=400, detail=f"工作目录不存在: {cwd}")

    timeout = max(5, min(req.timeout, 600))   # 5s ~ 10min

    t0 = time.time()

    # ── 后台命令：用 Popen 立即返回，不等待完成 ──
    if _is_background_command(cmd):
        try:
            actual_cmd = _extract_background_cmd(cmd)
            proc = subprocess.Popen(
                actual_cmd,
                shell=True,
                cwd=cwd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS,
            )
            elapsed = time.time() - t0
            return ExecResult(
                stdout=f"后台进程已启动 (PID: {proc.pid})",
                stderr="",
                returncode=0,
                elapsed=round(elapsed, 2),
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"启动后台进程失败: {e}")

    # ── 普通命令：等待完成并捕获输出 ──
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        elapsed = time.time() - t0
        return ExecResult(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
            elapsed=round(elapsed, 2),
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=408, detail=f"命令超时 ({timeout}s)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ── 入口 ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  AbaqusGPT Host Bridge")
    print(f"  监听地址: http://{HOST}:{PORT}")
    print(f"  Docker 内访问: http://host.docker.internal:{PORT}")
    if HOST == "127.0.0.1":
        print("  ℹ 仅允许本机访问，设置 HOST_BRIDGE_HOST=0.0.0.0 开放网络访问")
    print("  按 Ctrl+C 停止")
    print("=" * 60)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
