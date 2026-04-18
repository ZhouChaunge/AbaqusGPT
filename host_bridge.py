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

# ── 安全黑名单（Windows 命令）────────────────────────────────────────────────
_BLOCKED_PATTERNS = [
    "format c:",
    "del /f /s /q c:\\",
    "rd /s /q c:\\",
    "rmdir /s /q c:\\",
    "reg delete hklm",
    "bcdedit",
    "shutdown /r",
    "shutdown /s",
    "net user administrator",
    "powershell -enc",          # 隐藏编码执行
    "invoke-expression",
    "iex(",
]

# 只允许来自本机和 Docker 网段的请求（可以按需扩展）
_ALLOWED_ORIGINS = ["http://localhost:3000", "http://127.0.0.1:3000",
                    "http://172.18.0.0/16", "http://172.17.0.0/16"]

HOST = "0.0.0.0"
PORT = 8081

# ── FastAPI 应用 ──────────────────────────────────────────────────────────────
app = FastAPI(title="AbaqusGPT Host Bridge", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Docker 内网调用，允许所有
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
    cmd_lower = cmd.lower().strip()
    return cmd_lower.startswith("start /b ") or cmd_lower.startswith("start /b\t")


@app.post("/execute", response_model=ExecResult)
def execute(req: ExecRequest):
    """在 Windows 宿主机上执行命令，返回 stdout/stderr。"""
    cmd = req.command.strip()
    if not cmd:
        raise HTTPException(status_code=400, detail="命令不能为空")

    # 安全检查
    cmd_lower = cmd.lower()
    for pattern in _BLOCKED_PATTERNS:
        if pattern in cmd_lower:
            raise HTTPException(status_code=403, detail=f"命令被安全策略拒绝: {pattern}")

    # 工作目录
    cwd = req.cwd.strip() or None
    if cwd and not Path(cwd).exists():
        raise HTTPException(status_code=400, detail=f"工作目录不存在: {cwd}")

    timeout = max(5, min(req.timeout, 600))   # 5s ~ 10min

    t0 = time.time()

    # ── 后台命令：用 Popen 立即返回，不等待完成 ──
    if _is_background_command(cmd):
        try:
            # 去掉 start /b 前缀，直接用 Popen 以 DETACHED 方式启动
            actual_cmd = cmd[len("start /b "):].strip()
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
    print(f"  监听地址: http://0.0.0.0:{PORT}")
    print(f"  Docker 内访问: http://host.docker.internal:{PORT}")
    print("  按 Ctrl+C 停止")
    print("=" * 60)
    uvicorn.run(app, host=HOST, port=PORT, log_level="info")
