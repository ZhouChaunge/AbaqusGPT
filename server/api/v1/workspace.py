"""
Abaqus Workspace Monitoring API - 实时工作目录监控与命令执行

支持功能：
1. 设置/打开工作目录
2. 实时监控目录中的文件变化
3. 读取和解析各类 Abaqus 输出文件
4. 执行 Abaqus 命令（提交计算、查看状态等）
5. 综合分析多文件状态
"""

import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

# Abaqus 相关文件扩展名及其描述
ABAQUS_FILE_TYPES = {
    ".inp": {"name": "输入文件", "category": "input", "priority": 1},
    ".msg": {"name": "消息文件", "category": "output", "priority": 2},
    ".sta": {"name": "状态文件", "category": "output", "priority": 3},
    ".dat": {"name": "数据文件", "category": "output", "priority": 4},
    ".log": {"name": "日志文件", "category": "output", "priority": 5},
    ".odb": {"name": "输出数据库", "category": "result", "priority": 6},
    ".com": {"name": "通信文件", "category": "runtime", "priority": 7},
    ".prt": {"name": "部件文件", "category": "runtime", "priority": 8},
    ".res": {"name": "重启文件", "category": "result", "priority": 9},
    ".sim": {"name": "仿真文件", "category": "runtime", "priority": 10},
    ".lck": {"name": "锁定文件", "category": "runtime", "priority": 11},
    ".023": {"name": "临时文件", "category": "temp", "priority": 99},
}

router = APIRouter()

# In-memory storage for active workspaces and watchers
active_workspaces: dict[str, dict] = {}
websocket_connections: list[WebSocket] = []


class WorkspaceConfig(BaseModel):
    """工作目录配置"""
    path: str = Field(..., description="工作目录的绝对路径")
    watch: bool = Field(True, description="是否启用实时监控")


class FileInfo(BaseModel):
    """文件信息"""
    name: str
    path: str
    extension: str
    size: int
    modified: datetime
    category: str
    type_name: str
    is_running: bool = False  # 是否正在被写入


class JobStatus(BaseModel):
    """Abaqus 作业状态"""
    job_name: str
    status: str  # pending, running, completed, error, aborted
    progress: Optional[float] = None  # 0-100
    current_step: Optional[int] = None
    current_increment: Optional[int] = None
    errors: list[str] = []
    warnings: list[str] = []
    last_message: Optional[str] = None


class WorkspaceStatus(BaseModel):
    """工作目录状态"""
    path: str
    exists: bool
    files: list[FileInfo]
    jobs: list[JobStatus]
    total_files: int
    abaqus_files: int
    last_update: datetime


class CommandRequest(BaseModel):
    """命令执行请求"""
    command: str = Field(..., description="要执行的命令")
    working_dir: Optional[str] = Field(None, description="工作目录")
    timeout: int = Field(300, description="超时时间(秒)")


class CommandResponse(BaseModel):
    """命令执行响应"""
    success: bool
    command: str
    stdout: str
    stderr: str
    return_code: int
    duration: float


class AnalysisRequest(BaseModel):
    """分析请求"""
    workspace_path: str
    job_name: Optional[str] = None
    include_suggestions: bool = True


class AnalysisResponse(BaseModel):
    """综合分析响应"""
    job_name: str
    status: str
    convergence_status: str
    errors: list[dict]
    warnings: list[dict]
    progress: dict
    suggestions: list[str]
    file_summary: dict


def get_file_info(file_path: Path) -> FileInfo:
    """获取文件详细信息"""
    stat = file_path.stat()
    ext = file_path.suffix.lower()
    type_info = ABAQUS_FILE_TYPES.get(ext, {"name": "其他文件", "category": "other", "priority": 100})

    # 检查文件是否正在被写入（通过锁定文件判断）
    is_running = False
    if ext in [".msg", ".sta", ".dat"]:
        lock_file = file_path.with_suffix(".lck")
        if lock_file.exists():
            is_running = True

    return FileInfo(
        name=file_path.name,
        path=str(file_path),
        extension=ext,
        size=stat.st_size,
        modified=datetime.fromtimestamp(stat.st_mtime),
        category=type_info["category"],
        type_name=type_info["name"],
        is_running=is_running,
    )


def scan_workspace(workspace_path: str) -> WorkspaceStatus:
    """扫描工作目录"""
    path = Path(workspace_path)

    if not path.exists():
        return WorkspaceStatus(
            path=workspace_path,
            exists=False,
            files=[],
            jobs=[],
            total_files=0,
            abaqus_files=0,
            last_update=datetime.now(),
        )

    files = []
    jobs_dict: dict[str, list[FileInfo]] = defaultdict(list)

    for item in path.iterdir():
        if item.is_file():
            file_info = get_file_info(item)
            files.append(file_info)

            # 按作业名分组 (去掉扩展名)
            if file_info.extension in ABAQUS_FILE_TYPES:
                job_name = item.stem
                jobs_dict[job_name].append(file_info)

    # 分析每个作业的状态
    jobs = []
    for job_name, job_files in jobs_dict.items():
        job_status = analyze_job_status(job_name, job_files, path)
        jobs.append(job_status)

    # 按优先级排序文件
    files.sort(key=lambda f: (
        ABAQUS_FILE_TYPES.get(f.extension, {}).get("priority", 100),
        f.name
    ))

    abaqus_files = sum(1 for f in files if f.extension in ABAQUS_FILE_TYPES)

    return WorkspaceStatus(
        path=workspace_path,
        exists=True,
        files=files,
        jobs=jobs,
        total_files=len(files),
        abaqus_files=abaqus_files,
        last_update=datetime.now(),
    )


def analyze_job_status(job_name: str, files: list[FileInfo], workspace: Path) -> JobStatus:
    """分析单个作业的状态"""
    status = "unknown"
    progress = None
    current_step = None
    current_increment = None
    errors = []
    warnings = []
    last_message = None

    # 检查是否有锁定文件（正在运行）
    has_lock = any(f.extension == ".lck" for f in files)
    has_odb = any(f.extension == ".odb" for f in files)
    has_sta = any(f.extension == ".sta" for f in files)
    has_msg = any(f.extension == ".msg" for f in files)

    if has_lock:
        status = "running"
    elif has_odb and has_sta:
        status = "completed"
    elif has_sta or has_msg:
        status = "error"  # 可能是中断或错误
    else:
        status = "pending"

    # 解析 .sta 文件获取进度
    sta_file = workspace / f"{job_name}.sta"
    if sta_file.exists():
        try:
            content = sta_file.read_text(errors="ignore")
            lines = content.strip().split("\n")
            for line in reversed(lines[-20:]):
                if "STEP" in line and "INCREMENT" in line:
                    parts = line.split()
                    for i, part in enumerate(parts):
                        if part == "STEP" and i + 1 < len(parts):
                            try:
                                current_step = int(parts[i + 1])
                            except ValueError:
                                pass
                        if part == "INCREMENT" and i + 1 < len(parts):
                            try:
                                current_increment = int(parts[i + 1])
                            except ValueError:
                                pass
                    break
        except Exception:
            pass

    # 解析 .msg 文件获取错误和警告
    msg_file = workspace / f"{job_name}.msg"
    if msg_file.exists():
        try:
            content = msg_file.read_text(errors="ignore")
            lines = content.split("\n")
            for line in lines[-100:]:
                line_upper = line.upper()
                if "***ERROR" in line_upper:
                    errors.append(line.strip())
                elif "***WARNING" in line_upper:
                    warnings.append(line.strip())

            # 获取最后一条有意义的消息
            for line in reversed(lines[-20:]):
                stripped = line.strip()
                if stripped and not stripped.startswith("***"):
                    last_message = stripped[:200]
                    break

            # 检查是否有致命错误
            if any("FATAL" in e.upper() for e in errors):
                status = "error"
            elif "THE ANALYSIS HAS BEEN COMPLETED" in content.upper():
                status = "completed"
        except Exception:
            pass

    return JobStatus(
        job_name=job_name,
        status=status,
        progress=progress,
        current_step=current_step,
        current_increment=current_increment,
        errors=errors[:10],  # 最多返回10条
        warnings=warnings[:10],
        last_message=last_message,
    )


@router.post("/open")
async def open_workspace(config: WorkspaceConfig):
    """打开/设置工作目录"""
    path = Path(config.path)

    if not path.exists():
        raise HTTPException(status_code=404, detail=f"目录不存在: {config.path}")

    if not path.is_dir():
        raise HTTPException(status_code=400, detail=f"路径不是目录: {config.path}")

    # 存储工作目录配置
    workspace_id = str(path.resolve())
    active_workspaces[workspace_id] = {
        "path": workspace_id,
        "watch": config.watch,
        "opened_at": datetime.now(),
    }

    # 扫描并返回状态
    status = scan_workspace(workspace_id)

    return {
        "success": True,
        "workspace_id": workspace_id,
        "status": status,
    }


@router.get("/status")
async def get_workspace_status(path: str = Query(..., description="工作目录路径")):
    """获取工作目录当前状态"""
    status = scan_workspace(path)
    return status


@router.get("/tree")
async def get_workspace_tree(
    path: str = Query(..., description="工作目录路径"),
    max_depth: int = Query(4, description="最大递归深度"),
):
    """递归扫描工作目录，返回 VSCode 风格的目录树"""
    root = Path(path)
    if not root.exists():
        raise HTTPException(status_code=404, detail=f"目录不存在: {path}")

    def _scan_dir(dir_path: Path, depth: int) -> list[dict]:
        items: list[dict] = []
        try:
            entries = sorted(dir_path.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        except PermissionError:
            return items
        for entry in entries:
            rel = str(entry.relative_to(root)).replace("\\", "/")
            if entry.is_dir():
                children = _scan_dir(entry, depth + 1) if depth < max_depth else []
                items.append({
                    "name": entry.name,
                    "path": rel,
                    "type": "directory",
                    "children": children,
                })
            elif entry.is_file():
                try:
                    stat = entry.stat()
                    ext = entry.suffix.lower()
                    is_running = False
                    if ext in (".msg", ".sta", ".dat"):
                        is_running = entry.with_suffix(".lck").exists()
                    items.append({
                        "name": entry.name,
                        "path": rel,
                        "type": "file",
                        "size": stat.st_size,
                        "extension": ext,
                        "is_running": is_running,
                    })
                except OSError:
                    pass
        return items

    tree = _scan_dir(root, 0)
    return {"path": path, "tree": tree}


class FileOpRequest(BaseModel):
    workspace: str = Field(..., description="工作目录路径")
    path: str = Field(..., description="相对路径")
    new_name: Optional[str] = Field(None, description="新文件名（重命名时使用）")
    dest: Optional[str] = Field(None, description="目标相对路径（粘贴时使用）")


def _resolve_and_validate(workspace: str, rel_path: str) -> Path:
    """解析并验证路径在 workspace 内"""
    root = Path(workspace).resolve()
    target = (root / rel_path).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=403, detail="路径不在工作目录内")
    return target


@router.post("/file-ops/rename")
async def rename_file(req: FileOpRequest):
    """重命名文件或文件夹"""
    if not req.new_name:
        raise HTTPException(status_code=400, detail="缺少 new_name")
    target = _resolve_and_validate(req.workspace, req.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    new_path = target.parent / req.new_name
    if new_path.exists():
        raise HTTPException(status_code=409, detail=f"目标已存在: {req.new_name}")
    target.rename(new_path)
    return {"success": True, "old": req.path, "new": str(new_path.relative_to(Path(req.workspace).resolve())).replace("\\", "/")}


@router.post("/file-ops/delete")
async def delete_file(req: FileOpRequest):
    """删除文件或文件夹"""
    import shutil
    target = _resolve_and_validate(req.workspace, req.path)
    if not target.exists():
        raise HTTPException(status_code=404, detail="文件不存在")
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    return {"success": True, "deleted": req.path}


@router.post("/file-ops/copy")
async def copy_file(req: FileOpRequest):
    """复制文件或文件夹到目标路径"""
    import shutil
    if not req.dest:
        raise HTTPException(status_code=400, detail="缺少 dest")
    source = _resolve_and_validate(req.workspace, req.path)
    dest = _resolve_and_validate(req.workspace, req.dest)
    if not source.exists():
        raise HTTPException(status_code=404, detail="源文件不存在")
    # 如果 dest 是已存在的目录，则复制到其中
    if dest.is_dir():
        dest = dest / source.name
    if dest.exists():
        # 自动加后缀避免覆盖
        stem, suffix = dest.stem, dest.suffix
        i = 1
        while dest.exists():
            dest = dest.parent / f"{stem}_copy{i}{suffix}"
            i += 1
    if source.is_dir():
        shutil.copytree(source, dest)
    else:
        shutil.copy2(source, dest)
    return {"success": True, "source": req.path, "dest": str(dest.relative_to(Path(req.workspace).resolve())).replace("\\", "/")}


@router.post("/file-ops/new-file")
async def new_file(req: FileOpRequest):
    """在指定路径创建空文件"""
    target = _resolve_and_validate(req.workspace, req.path)
    if target.exists():
        raise HTTPException(status_code=409, detail="文件已存在")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.touch()
    return {"success": True, "created": req.path}


@router.post("/file-ops/new-folder")
async def new_folder(req: FileOpRequest):
    """创建新文件夹"""
    target = _resolve_and_validate(req.workspace, req.path)
    if target.exists():
        raise HTTPException(status_code=409, detail="文件夹已存在")
    target.mkdir(parents=True, exist_ok=True)
    return {"success": True, "created": req.path}


@router.get("/file/{filename:path}")
async def read_file_content(
    filename: str,
    workspace: str = Query(..., description="工作目录路径"),
    tail: int = Query(100, description="只读取最后N行，0表示全部"),
):
    """读取文件内容"""
    file_path = Path(workspace) / filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {filename}")

    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"不是文件: {filename}")

    # 检查文件大小，避免读取过大的文件
    size = file_path.stat().st_size
    if size > 10 * 1024 * 1024:  # 10MB 限制
        # 对于大文件，只读取尾部
        tail = min(tail, 500) if tail > 0 else 500

    try:
        content = file_path.read_text(errors="ignore")
        lines = content.split("\n")

        if tail > 0 and len(lines) > tail:
            lines = lines[-tail:]
            content = "\n".join(lines)
            truncated = True
        else:
            truncated = False

        return {
            "filename": filename,
            "size": size,
            "content": content,
            "line_count": len(lines),
            "truncated": truncated,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取文件失败: {str(e)}")


@router.post("/execute")
async def execute_command(request: CommandRequest):
    """执行命令（用于提交 Abaqus 作业等）"""
    start_time = datetime.now()

    # 安全检查：只允许特定命令模式
    allowed_patterns = [
        "abaqus ",
        "abq",
        "dir ",
        "ls ",
        "type ",
        "cat ",
        "head ",
        "tail ",
    ]

    command_lower = request.command.lower().strip()
    if not any(command_lower.startswith(p) for p in allowed_patterns):
        raise HTTPException(
            status_code=403,
            detail="不允许执行此命令。只支持 Abaqus 相关命令和基本文件查看命令。"
        )

    # 确定工作目录
    cwd = request.working_dir or os.getcwd()
    if not Path(cwd).exists():
        raise HTTPException(status_code=404, detail=f"工作目录不存在: {cwd}")

    try:
        # Windows 使用 cmd，Linux/Mac 使用 bash
        if sys.platform == "win32":
            result = subprocess.run(
                request.command,
                shell=True,  # nosec B602
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=request.timeout,
            )
        else:
            result = subprocess.run(
                request.command,
                shell=True,  # nosec B602
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=request.timeout,
                executable="/bin/bash",
            )

        duration = (datetime.now() - start_time).total_seconds()

        return CommandResponse(
            success=result.returncode == 0,
            command=request.command,
            stdout=result.stdout,
            stderr=result.stderr,
            return_code=result.returncode,
            duration=duration,
        )
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=408,
            detail=f"命令执行超时 ({request.timeout}秒)"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"命令执行失败: {str(e)}")


@router.post("/analyze")
async def analyze_workspace(request: AnalysisRequest):
    """综合分析工作目录中的作业状态"""
    from abaqusgpt.agents.converge_doctor import ConvergeDoctor
    from abaqusgpt.parsers.msg_parser import MsgParser
    from abaqusgpt.parsers.sta_parser import StaParser

    workspace = Path(request.workspace_path)
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="工作目录不存在")

    # 如果指定了作业名，只分析该作业
    if request.job_name:
        job_names = [request.job_name]
    else:
        # 找出所有作业（基于 .inp 或 .msg 文件）
        job_names = set()
        for f in workspace.iterdir():
            if f.suffix.lower() in [".inp", ".msg", ".sta"]:
                job_names.add(f.stem)
        job_names = list(job_names)

    if not job_names:
        return AnalysisResponse(
            job_name="",
            status="no_jobs",
            convergence_status="unknown",
            errors=[],
            warnings=[],
            progress={},
            suggestions=["未找到 Abaqus 作业文件，请确认工作目录正确"],
            file_summary={},
        )

    # 分析第一个作业（或指定的作业）
    job_name = job_names[0]

    errors = []
    warnings = []
    suggestions = []
    progress = {}
    convergence_status = "unknown"

    # 解析 .msg 文件
    msg_file = workspace / f"{job_name}.msg"
    if msg_file.exists():
        try:
            parser = MsgParser()
            msg_data = parser.parse(msg_file)
            errors.extend([{"source": "msg", "message": e} for e in msg_data.get("errors", [])])
            warnings.extend([{"source": "msg", "message": w} for w in msg_data.get("warnings", [])])
        except Exception as e:
            warnings.append({"source": "parser", "message": f"解析 .msg 文件失败: {str(e)}"})

    # 解析 .sta 文件
    sta_file = workspace / f"{job_name}.sta"
    if sta_file.exists():
        try:
            parser = StaParser()
            sta_data = parser.parse(sta_file)
            progress = {
                "current_step": sta_data.get("last_step"),
                "current_increment": sta_data.get("last_increment"),
                "total_time": sta_data.get("total_time"),
            }
            if sta_data.get("converged") is True:
                convergence_status = "converged"
            elif sta_data.get("converged") is False:
                convergence_status = "not_converged"
        except Exception as e:
            warnings.append({"source": "parser", "message": f"解析 .sta 文件失败: {str(e)}"})

    # 使用 AI 生成建议
    if request.include_suggestions and (errors or warnings):
        try:
            doctor = ConvergeDoctor()
            # 构建上下文
            context = f"作业名: {job_name}\n"
            if errors:
                context += f"错误: {errors[:5]}\n"
            if warnings:
                context += f"警告: {warnings[:5]}\n"
            context += f"收敛状态: {convergence_status}\n"
            context += f"进度: {progress}\n"

            # 获取诊断建议
            if msg_file.exists():
                diagnosis = doctor.diagnose(msg_file, verbose=False)
                suggestions.append(diagnosis)
        except Exception as e:
            suggestions.append(f"AI 分析暂时不可用: {str(e)}")

    # 确定总体状态
    if errors:
        status = "error"
    elif warnings:
        status = "warning"
    elif convergence_status == "converged":
        status = "completed"
    else:
        status = "running" if (workspace / f"{job_name}.lck").exists() else "unknown"

    # 文件摘要
    file_summary = {}
    for ext in [".inp", ".msg", ".sta", ".dat", ".odb"]:
        f = workspace / f"{job_name}{ext}"
        if f.exists():
            file_summary[ext] = {
                "exists": True,
                "size": f.stat().st_size,
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            }
        else:
            file_summary[ext] = {"exists": False}

    return AnalysisResponse(
        job_name=job_name,
        status=status,
        convergence_status=convergence_status,
        errors=errors,
        warnings=warnings,
        progress=progress,
        suggestions=suggestions,
        file_summary=file_summary,
    )


# WebSocket 实时监控
@router.websocket("/ws/watch")
async def websocket_watch(websocket: WebSocket):
    """WebSocket 端点，用于实时推送文件变化"""
    await websocket.accept()
    websocket_connections.append(websocket)

    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()

            if data.get("action") == "watch":
                workspace_path = data.get("path")
                if workspace_path:
                    # 立即发送当前状态
                    status = scan_workspace(workspace_path)
                    await websocket.send_json({
                        "type": "status",
                        "data": status.model_dump(mode="json"),
                    })

            elif data.get("action") == "refresh":
                workspace_path = data.get("path")
                if workspace_path:
                    status = scan_workspace(workspace_path)
                    await websocket.send_json({
                        "type": "status",
                        "data": status.model_dump(mode="json"),
                    })

    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        if websocket in websocket_connections:
            websocket_connections.remove(websocket)
        print(f"WebSocket error: {e}")


async def broadcast_file_change(workspace_path: str, event_type: str, file_path: str):
    """向所有连接的客户端广播文件变化"""
    message = {
        "type": "file_change",
        "data": {
            "workspace": workspace_path,
            "event": event_type,
            "file": file_path,
            "timestamp": datetime.now().isoformat(),
        }
    }

    for ws in websocket_connections:
        try:
            await ws.send_json(message)
        except Exception:
            pass


# ============================================================
# ============================================================
# ReAct Agent Tools - 工具调用基础设施
# ============================================================

# 安全黑名单（在 Docker 容器内执行，阻止最危险的命令）
_SHELL_BLOCKED = [
    'rm -rf /', 'rm -rf ~', 'dd if=/dev/zero', 'dd if=/dev/urandom',
    'mkfs', '> /dev/sda', ':(){ :|:&};:', 'chmod 000 /',
    'chown root /', 'kill -9 1', 'pkill -9 -1',
]

# OpenAI-compatible function calling schema（litellm 原生支持）
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "shell_exec",
            "description": "在 Docker Linux 容器内执行 bash 命令。适用于：grep 搜索文件内容、wc 统计行数、awk/sed 文本处理、检查环境变量等。注意：容器内没有 Abaqus，Abaqus 相关命令请用 host_exec。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的 bash 命令"},
                    "working_dir": {"type": "string", "description": "工作目录（可选，默认为当前工作区）"},
                    "timeout": {"type": "integer", "description": "超时秒数（默认15，最大60）", "default": 15},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_list",
            "description": "列出目录下的文件和子目录，显示文件名和大小。用于了解工作区结构、查找特定类型的文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "目录路径，如 /workspace 或 /workspace/001-project"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_read",
            "description": "读取文件内容。对于大文件（如 INP），先用 max_lines=50 看概览，再按需读更多。对于 MSG/LOG 文件，用 tail=true 查看最新的错误信息。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件绝对路径，如 /workspace/test.inp"},
                    "max_lines": {"type": "integer", "description": "最多读取行数（默认200）", "default": 200},
                    "tail": {"type": "boolean", "description": "true=从末尾读取（适合日志文件）；false=从开头读取", "default": False},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "find_path",
            "description": "在容器文件系统中搜索文件或目录。支持通配符如 '*.inp'、'test*'。",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "文件或目录名（支持通配符）"},
                    "search_in": {"type": "string", "description": "搜索目录（空格分隔）", "default": "/usr /opt /home /workspace /SIMULIA"},
                    "max_depth": {"type": "integer", "description": "最大搜索深度", "default": 6},
                    "type": {"type": "string", "description": "f=仅文件，d=仅目录，空=两者", "default": ""},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "host_exec",
            "description": "在 Windows 宿主机上执行命令。用于：提交 Abaqus 作业、查看 Windows 文件、运行 Abaqus 命令。Abaqus 路径：D:\\200_Scientific\\2060_SIMULIA\\002-Commands\\abaqus.bat。示例：abaqus job=test cpus=8。cwd 必须是 Windows 路径格式。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Windows cmd/powershell 命令"},
                    "cwd": {"type": "string", "description": "Windows 工作目录路径（如 E:\\Desktop\\abaqus_agent\\project）"},
                    "timeout": {"type": "integer", "description": "超时秒数（默认120，长任务最大600）", "default": 120},
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_write",
            "description": "在 /workspace 目录下创建或覆盖文件。用于生成 INP 文件、Python 脚本、修改配置等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "文件绝对路径（必须在 /workspace 下）"},
                    "content": {"type": "string", "description": "文件内容（完整内容，覆盖原文件）"},
                    "append": {"type": "boolean", "description": "true=追加模式，false=覆盖模式", "default": False},
                },
                "required": ["path", "content"],
            },
        },
    },
    # ── 领域 Agent 专业工具 / Domain Agent Tools ──
    {
        "type": "function",
        "function": {
            "name": "diagnose_convergence",
            "description": "调用 ConvergeDoctor 专业诊断收敛问题。自动解析 .msg 和 .sta 文件，匹配 200+ 已知错误模式，返回结构化诊断报告（根因分析 + 修复建议）。比手动 grep 文件更准确、更全面。",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_dir": {"type": "string", "description": "作业所在目录的绝对路径，如 /workspace/project"},
                    "job_name": {"type": "string", "description": "作业名称（不含扩展名），如 test_015"},
                },
                "required": ["job_dir", "job_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_mesh",
            "description": "调用 MeshAdvisor 分析 INP 文件中的网格质量。返回单元数量、节点数量、单元类型、网格质量评估和优化建议。适用于检查网格是否合理、是否需要加密或改换单元类型。",
            "parameters": {
                "type": "object",
                "properties": {
                    "inp_file": {"type": "string", "description": "INP 文件的绝对路径，如 /workspace/project/model.inp"},
                },
                "required": ["inp_file"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_inp",
            "description": "调用 InpGenerator 根据自然语言描述生成 Abaqus INP 文件或 Python 脚本。可生成完整的有限元模型输入文件，包含几何、材料、边界条件、加载步骤等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "模型的自然语言描述，如'20x10x5mm 钢板，底部固定，顶面 10MPa 均布压力'"},
                    "output_path": {"type": "string", "description": "输出文件路径（必须在 /workspace 下），如 /workspace/project/generated.inp"},
                    "format": {"type": "string", "description": "输出格式：inp=Abaqus 输入文件，python=Abaqus Python 脚本", "enum": ["inp", "python"], "default": "inp"},
                    "domain": {"type": "string", "description": "工程领域（可选），如 geotechnical、structural、mechanical 等"},
                },
                "required": ["description", "output_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_output",
            "description": "解析 Abaqus 输出文件（.dat/.sta），提取关键结果数据。返回步骤信息、收敛历史、问题增量步识别等结构化结果。用于理解仿真结果和检查计算是否正常。",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_dir": {"type": "string", "description": "作业所在目录的绝对路径"},
                    "job_name": {"type": "string", "description": "作业名称（不含扩展名）"},
                    "output_type": {"type": "string", "description": "要分析的输出类型", "enum": ["convergence_history", "problem_increments", "full_status"], "default": "full_status"},
                },
                "required": ["job_dir", "job_name"],
            },
        },
    },
]


async def run_tool(tool_name: str, params: dict, workspace_path: str) -> str:
    """执行一个工具并返回结果字符串。"""
    if tool_name == "shell_exec":
        command = params.get("command", "").strip()
        if not command:
            return "错误：命令为空"
        cmd_lower = command.lower()
        for blocked in _SHELL_BLOCKED:
            if blocked in cmd_lower:
                return f"安全限制：禁止执行此命令 ({blocked})"
        working_dir = params.get("working_dir", "").strip() or workspace_path
        try:
            timeout = min(int(float(params.get("timeout", 15))), 60)
        except (ValueError, TypeError):
            timeout = 15
        try:
            proc = subprocess.run(
                command, shell=True,  # nosec B602
                cwd=working_dir if Path(working_dir).exists() else workspace_path,
                capture_output=True, text=True, timeout=timeout,
                executable="/bin/bash" if sys.platform != "win32" else None,
            )
            parts = []
            if proc.stdout.strip():
                parts.append(proc.stdout.strip())
            if proc.stderr.strip():
                parts.append(f"[stderr]\n{proc.stderr.strip()}")
            parts.append(f"[返回码: {proc.returncode}]")
            return "\n".join(parts)
        except subprocess.TimeoutExpired:
            return f"命令超时 ({timeout}s)"
        except Exception as e:
            return f"执行失败: {e}"

    elif tool_name == "file_list":
        path = params.get("path", workspace_path).strip()
        try:
            p = Path(path)
            if not p.exists():
                return f"路径不存在: {path}"
            if not p.is_dir():
                return f"不是目录: {path}"
            items = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name))
            lines = []
            for item in items[:100]:
                if item.is_file():
                    s = item.stat().st_size
                    size = f"{s}B" if s < 1024 else (f"{s//1024}KB" if s < 1024*1024 else f"{s//1024//1024}MB")
                    lines.append(f"📄 {item.name} ({size})")
                else:
                    lines.append(f"📁 {item.name}/")
            total = len(list(p.iterdir()))
            result = f"目录 {path}（共 {total} 项）:\n" + "\n".join(lines)
            if total > 100:
                result += "\n... (仅显示前100项)"
            return result
        except PermissionError:
            return f"权限不足: {path}"
        except Exception as e:
            return f"列目录失败: {e}"

    elif tool_name == "file_read":
        path = params.get("path", "").strip()
        if not path:
            return "错误：path 为空"
        try:
            max_lines = int(params.get("max_lines", 200))
        except (ValueError, TypeError):
            max_lines = 200
        tail = str(params.get("tail", "false")).lower() in ("true", "1", "yes")
        try:
            content = _read_file_content(Path(path), max_lines=max_lines, tail=tail)
            return f"文件 {path}:\n{content}"
        except FileNotFoundError:
            return f"文件不存在: {path}"
        except Exception as e:
            return f"读取失败: {e}"

    elif tool_name == "find_path":
        name = params.get("name", "").strip()
        if not name:
            return "错误：name 参数为空"
        search_in = params.get("search_in", "/usr /opt /home /workspace /SIMULIA").strip()
        try:
            max_depth = int(params.get("max_depth", 6))
        except (ValueError, TypeError):
            max_depth = 6
        type_flag = params.get("type", "").strip()
        dirs = [d for d in search_in.split() if Path(d).exists()]
        if not dirs:
            return f"指定的搜索目录均不存在: {search_in}"
        type_opt = f"-type {type_flag}" if type_flag in ["f", "d"] else ""
        cmd = f"find {' '.join(dirs)} -maxdepth {max_depth} -name '{name}' {type_opt} 2>/dev/null | head -30"
        try:
            proc = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30,  # nosec B602
                executable="/bin/bash" if sys.platform != "win32" else None,
            )
            output = proc.stdout.strip()
            if not output:
                return f"未找到匹配 '{name}' 的结果（搜索范围: {search_in}）"
            return f"找到以下匹配:\n{output}"
        except Exception as e:
            return f"搜索失败: {e}"

    elif tool_name == "host_exec":
        command = params.get("command", "").strip()
        if not command:
            return "错误：command 为空"
        cwd = params.get("cwd", "").strip()
        # 自动推导 Windows cwd：如果未提供，从 Docker workspace_path 映射
        if not cwd and workspace_path:
            win_path = workspace_path.replace("/workspace", r"E:\Desktop\abaqus_agent").replace("/", "\\")
            cwd = win_path
        try:
            timeout = max(5, min(int(float(params.get("timeout", 120))), 600))
        except (ValueError, TypeError):
            timeout = 120
        import urllib.request
        bridge_url = "http://host.docker.internal:8081/execute"
        payload = json.dumps({"command": command, "cwd": cwd, "timeout": timeout}).encode()
        req = urllib.request.Request(
            bridge_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout + 5) as resp:
                result = json.loads(resp.read())
            parts = []
            if result.get("stdout", "").strip():
                parts.append(result["stdout"].strip())
            if result.get("stderr", "").strip():
                parts.append(f"[stderr]\n{result['stderr'].strip()}")
            rc = result.get("returncode", 0)
            elapsed = result.get("elapsed", 0)
            parts.append(f"[返回码: {rc} | 耗时: {elapsed}s]")
            return "\n".join(parts)
        except Exception as e:
            return (
                f"Host Bridge 不可用: {e}\n"
                "请先在宿主机上运行: python host_bridge.py"
            )

    elif tool_name == "file_write":
        path = params.get("path", "").strip()
        content = params.get("content", "")
        if not path:
            return "错误：path 为空"
        # 安全：只允许写 /workspace 内
        if not path.startswith("/workspace"):
            return f"安全限制：只允许写入 /workspace 目录下的文件，拒绝: {path}"
        append = str(params.get("append", "false")).lower() == "true"
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            mode = "a" if append else "w"
            with open(p, mode, encoding="utf-8") as f:
                f.write(content)
            size = p.stat().st_size
            action = "追加" if append else "写入"
            return f"文件{action}成功: {path} ({size} 字节)"
        except PermissionError:
            return f"权限不足: {path}"
        except Exception as e:
            return f"写入失败: {e}"

    # ── 领域 Agent 工具 / Domain Agent Tools ──
    elif tool_name == "diagnose_convergence":
        job_dir = params.get("job_dir", "").strip()
        job_name = params.get("job_name", "").strip()
        if not job_dir or not job_name:
            return "错误：job_dir 和 job_name 都是必填参数"

        from abaqusgpt.agents.converge_doctor import ConvergeDoctor
        from abaqusgpt.parsers.msg_parser import MsgParser
        from abaqusgpt.parsers.sta_parser import StaParser

        job_path = Path(job_dir)
        msg_file = job_path / f"{job_name}.msg"
        sta_file = job_path / f"{job_name}.sta"

        result_parts = {"job_name": job_name, "diagnosis": {}}

        # 解析 .msg 文件
        if msg_file.exists():
            try:
                parser = MsgParser()
                msg_data = parser.parse(msg_file)
                result_parts["msg_analysis"] = msg_data
                result_parts["msg_summary"] = parser.get_summary(msg_data)
            except Exception as e:
                result_parts["msg_error"] = str(e)
        else:
            result_parts["msg_status"] = f"文件不存在: {msg_file}"

        # 解析 .sta 文件
        if sta_file.exists():
            try:
                parser = StaParser()
                sta_data = parser.parse(sta_file)
                result_parts["sta_analysis"] = sta_data
                # 识别问题增量步
                problems = parser.identify_problem_increments(sta_data)
                if problems:
                    result_parts["problem_increments"] = problems
            except Exception as e:
                result_parts["sta_error"] = str(e)
        else:
            result_parts["sta_status"] = f"文件不存在: {sta_file}"

        # 匹配已知错误模式
        from abaqusgpt.knowledge.error_codes import ERROR_DATABASE
        matched_errors = []
        for error_text in result_parts.get("msg_analysis", {}).get("errors", []):
            for pattern, info in ERROR_DATABASE.items():
                if pattern.lower() in error_text.lower():
                    matched_errors.append({
                        "pattern": pattern,
                        "category": info.get("category", "unknown"),
                        "severity": info.get("severity", "unknown"),
                        "causes": info.get("causes", []),
                        "solutions": info.get("solutions", []),
                    })
                    break
        if matched_errors:
            result_parts["known_error_matches"] = matched_errors

        return json.dumps(result_parts, ensure_ascii=False, default=str)

    elif tool_name == "analyze_mesh":
        inp_file = params.get("inp_file", "").strip()
        if not inp_file:
            return "错误：inp_file 是必填参数"

        inp_path = Path(inp_file)
        if not inp_path.exists():
            return f"文件不存在: {inp_file}"

        from abaqusgpt.parsers.inp_parser import InpParser

        try:
            parser = InpParser()
            mesh_data = parser.parse_mesh(inp_path)

            result = {
                "file": inp_file,
                "num_elements": mesh_data.get("num_elements", 0),
                "num_nodes": mesh_data.get("num_nodes", 0),
                "element_types": mesh_data.get("element_types", []),
                "sections": mesh_data.get("sections", []),
            }

            # 基于规则的质量检查
            quality_notes = []
            elem_count = result["num_elements"]
            node_count = result["num_nodes"]
            if elem_count > 0 and node_count > 0:
                ratio = node_count / elem_count
                if ratio < 1.2:
                    quality_notes.append("节点/单元比偏低，可能使用了低阶单元")
                elif ratio > 3.0:
                    quality_notes.append("节点/单元比偏高，可能使用了高阶单元或网格较稀疏")

            for etype in result["element_types"]:
                etype_upper = etype.upper()
                if "R" in etype_upper and ("C3D" in etype_upper or "CPE" in etype_upper):
                    quality_notes.append(f"单元 {etype} 为缩减积分单元，注意沙漏模式")
                if "T" in etype_upper and "TET" not in etype_upper and "TRUSS" not in etype_upper:
                    pass  # normal

            if quality_notes:
                result["quality_notes"] = quality_notes

            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            return f"网格分析失败: {e}"

    elif tool_name == "generate_inp":
        description = params.get("description", "").strip()
        output_path = params.get("output_path", "").strip()
        fmt = params.get("format", "inp").strip()
        domain = params.get("domain", "").strip()

        if not description:
            return "错误：description 是必填参数"
        if not output_path:
            return "错误：output_path 是必填参数"
        if not output_path.startswith("/workspace"):
            return f"安全限制：输出路径必须在 /workspace 下，拒绝: {output_path}"

        from abaqusgpt.agents.inp_generator import InpGenerator

        try:
            generator = InpGenerator()
            if domain:
                description = f"[{domain} 领域] {description}"

            content = generator.generate(description, format=fmt)

            # 写入文件
            out_path = Path(output_path)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(content, encoding="utf-8")

            ext = "inp" if fmt == "inp" else "py"
            return json.dumps({
                "success": True,
                "output_path": output_path,
                "format": fmt,
                "size": out_path.stat().st_size,
                "message": f"已生成 .{ext} 文件: {output_path}",
            }, ensure_ascii=False)
        except Exception as e:
            return f"生成失败: {e}"

    elif tool_name == "analyze_output":
        job_dir = params.get("job_dir", "").strip()
        job_name = params.get("job_name", "").strip()
        output_type = params.get("output_type", "full_status").strip()

        if not job_dir or not job_name:
            return "错误：job_dir 和 job_name 都是必填参数"

        from abaqusgpt.parsers.msg_parser import MsgParser
        from abaqusgpt.parsers.sta_parser import StaParser

        job_path = Path(job_dir)
        result = {"job_name": job_name, "output_type": output_type}

        sta_file = job_path / f"{job_name}.sta"
        msg_file = job_path / f"{job_name}.msg"
        dat_file = job_path / f"{job_name}.dat"

        if output_type == "convergence_history":
            if sta_file.exists():
                try:
                    parser = StaParser()
                    sta_data = parser.parse(sta_file)
                    result["convergence_history"] = parser.get_convergence_history(sta_data)
                    result["total_increments"] = sta_data.get("total_increments", 0)
                    result["completed"] = sta_data.get("completed", False)
                except Exception as e:
                    result["error"] = str(e)
            else:
                result["error"] = f"STA 文件不存在: {sta_file}"

        elif output_type == "problem_increments":
            if sta_file.exists():
                try:
                    parser = StaParser()
                    sta_data = parser.parse(sta_file)
                    result["problem_increments"] = parser.identify_problem_increments(sta_data)
                    result["total_increments"] = sta_data.get("total_increments", 0)
                except Exception as e:
                    result["error"] = str(e)
            else:
                result["error"] = f"STA 文件不存在: {sta_file}"

        else:  # full_status
            # STA 分析
            if sta_file.exists():
                try:
                    parser = StaParser()
                    sta_data = parser.parse(sta_file)
                    result["sta"] = {
                        "total_increments": sta_data.get("total_increments", 0),
                        "completed": sta_data.get("completed", False),
                        "last_step": sta_data.get("last_step"),
                        "last_increment": sta_data.get("last_increment"),
                        "last_time": sta_data.get("last_time"),
                    }
                    problems = parser.identify_problem_increments(sta_data)
                    if problems:
                        result["problem_increments"] = problems[:10]
                except Exception as e:
                    result["sta_error"] = str(e)

            # MSG 分析
            if msg_file.exists():
                try:
                    parser = MsgParser()
                    msg_data = parser.parse(msg_file)
                    result["msg"] = {
                        "errors": msg_data.get("errors", [])[:10],
                        "warnings": msg_data.get("warnings", [])[:10],
                        "last_step": msg_data.get("last_step"),
                        "last_increment": msg_data.get("last_increment"),
                        "total_iterations": msg_data.get("total_iterations", 0),
                        "contact_issues": msg_data.get("contact_issues", [])[:5],
                        "element_issues": msg_data.get("element_issues", [])[:5],
                    }
                except Exception as e:
                    result["msg_error"] = str(e)

            # DAT 文件存在性
            result["dat_exists"] = dat_file.exists()
            if dat_file.exists():
                result["dat_size"] = dat_file.stat().st_size

            # ODB 文件存在性
            odb_file = job_path / f"{job_name}.odb"
            result["odb_exists"] = odb_file.exists()
            if odb_file.exists():
                result["odb_size"] = odb_file.stat().st_size

        return json.dumps(result, ensure_ascii=False, default=str)

    return f"未知工具: {tool_name}"


# ============================================================
# 智能体对话 API - Agent-style Chat with Workspace Context
# ============================================================

class AgentChatRequest(BaseModel):
    """智能体对话请求"""
    message: str = Field(..., description="用户消息")
    workspace_path: str = Field(..., description="工作目录路径")
    job_name: Optional[str] = Field(None, description="指定作业名（可选）")
    history: list[dict] = Field(default_factory=list, description="对话历史")
    model: str = Field("gpt-4o", description="使用的模型")


def detect_intent_and_files(message: str, workspace_path: str, job_name: Optional[str] = None) -> dict:
    """
    分析用户意图，确定需要读取哪些文件

    Returns:
        {
            "intent": str,  # analyze_inp, check_convergence, explain_errors, etc.
            "files_to_read": list[str],  # 需要读取的文件路径
            "keywords": list[str],  # 检测到的关键词
        }
    """
    message_lower = message.lower()
    workspace = Path(workspace_path)

    # 检测作业名
    detected_job = job_name
    if not detected_job:
        # 尝试从工作目录检测作业
        for f in workspace.iterdir():
            if f.suffix.lower() in [".inp", ".msg"]:
                detected_job = f.stem
                break

    intent = "general"
    files_to_read = []
    keywords = []

    # 提交作业意图：不读任何文件（直接用工具操作）
    submit_kws = ["提交", "submit", "host_exec", "job=", "运行作业", "跑作业", "重新提交", "再跑"]
    if any(kw in message_lower for kw in submit_kws):
        return {
            "intent": "submit_job",
            "files_to_read": [],
            "keywords": [kw for kw in submit_kws if kw in message_lower],
            "detected_job": detected_job,
        }

    # 关键词映射到意图和文件
    intent_patterns = {
        "analyze_inp": {
            "keywords": ["inp", "输入文件", "input", "模型", "几何", "材料", "网格", "单元", "节点", "边界", "载荷", "接触", "分析当前"],
            "files": [".inp"],
            "priority": 1,
        },
        "check_convergence": {
            "keywords": ["收敛", "converge", "发散", "diverge", "迭代", "iteration", "增量", "increment", "步骤", "step"],
            "files": [".sta", ".msg"],
            "priority": 2,
        },
        "explain_errors": {
            "keywords": ["错误", "error", "警告", "warning", "问题", "失败", "fail", "报错", "异常"],
            "files": [".msg", ".dat", ".log"],
            "priority": 3,
        },
        "check_status": {
            "keywords": ["状态", "status", "进度", "progress", "运行", "完成", "当前"],
            "files": [".sta", ".msg", ".log"],
            "priority": 4,
        },
        "analyze_mesh": {
            "keywords": ["网格", "mesh", "单元", "element", "节点", "node", "质量", "畸变", "distort"],
            "files": [".inp", ".dat"],
            "priority": 5,
        },
        "analyze_contact": {
            "keywords": ["接触", "contact", "穿透", "penetrat", "摩擦", "friction", "相互作用", "interaction"],
            "files": [".inp", ".msg", ".dat"],
            "priority": 6,
        },
        "analyze_materials": {
            "keywords": ["材料", "material", "弹性", "elastic", "塑性", "plastic", "本构", "属性"],
            "files": [".inp"],
            "priority": 7,
        },
        "analyze_output": {
            "keywords": ["输出", "output", "结果", "result", "应力", "stress", "应变", "strain", "位移", "displacement"],
            "files": [".dat", ".odb"],
            "priority": 8,
        },
    }

    # 检测意图
    matched_intents = []
    for intent_name, pattern in intent_patterns.items():
        for kw in pattern["keywords"]:
            if kw in message_lower:
                keywords.append(kw)
                matched_intents.append((pattern["priority"], intent_name, pattern["files"]))
                break

    # 选择最高优先级的意图
    if matched_intents:
        matched_intents.sort(key=lambda x: x[0])
        intent = matched_intents[0][1]
        file_exts = matched_intents[0][2]

        # 构建文件路径（INP 文件超过 200KB 时跳过，让 AI 用 file_read 工具自己读）
        if detected_job:
            for ext in file_exts:
                file_path = workspace / f"{detected_job}{ext}"
                if file_path.exists():
                    # INP 文件大于 200KB 时不预加载（避免撑爆上下文）
                    if ext == ".inp" and file_path.stat().st_size > 200 * 1024:
                        continue
                    files_to_read.append(str(file_path))

    # 如果没有检测到特定意图但提到了文件类型，直接读取
    for ext in [".inp", ".msg", ".sta", ".dat", ".log"]:
        if ext.strip(".") in message_lower or ext in message_lower:
            if detected_job:
                file_path = workspace / f"{detected_job}{ext}"
                if file_path.exists() and str(file_path) not in files_to_read:
                    files_to_read.append(str(file_path))

    return {
        "intent": intent,
        "files_to_read": files_to_read,
        "keywords": list(set(keywords)),
        "detected_job": detected_job,
    }


def _read_file_content(file_path: str, max_lines: int = 500, tail: bool = False) -> str:
    """读取文件内容，支持限制行数"""
    try:
        path = Path(file_path)
        if not path.exists():
            return f"[文件不存在: {file_path}]"

        # 检查文件大小
        file_size = path.stat().st_size
        if file_size > 5 * 1024 * 1024:  # 大于5MB
            # 只读取尾部
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                if tail:
                    lines = lines[-max_lines:]
                else:
                    lines = lines[:max_lines]
                return f"[文件较大 ({file_size // 1024} KB)，显示部分内容]\n" + "".join(lines)

        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            if len(lines) > max_lines:
                if tail:
                    lines = lines[-max_lines:]
                    return f"[显示最后 {max_lines} 行]\n" + "".join(lines)
                else:
                    return "".join(lines[:max_lines]) + f"\n[... 文件共 {len(lines)} 行，已截断 ...]"
            return "".join(lines)
    except Exception as e:
        return f"[读取文件失败: {str(e)}]"


def build_workspace_snapshot(workspace_path: str, workspace_status: Optional[WorkspaceStatus] = None) -> str:
    """构建轻量级工作区快照（只有元数据，不读文件内容）。让 AI 自己用工具读取。"""
    parts = []
    parts.append(f"工作目录: {workspace_path}")

    # 列出工作目录下的文件（仅名称和大小）
    wp = Path(workspace_path)
    if wp.exists():
        items = sorted(wp.iterdir(), key=lambda x: (x.is_file(), x.name))
        file_lines = []
        for item in items[:60]:
            if item.is_file():
                s = item.stat().st_size
                size = f"{s}B" if s < 1024 else (f"{s//1024}KB" if s < 1024*1024 else f"{s/1024/1024:.1f}MB")
                file_lines.append(f"  {item.name} ({size})")
            else:
                file_lines.append(f"  {item.name}/")
        parts.append("文件列表:\n" + "\n".join(file_lines))

    # 作业状态摘要
    if workspace_status and workspace_status.jobs:
        job_lines = []
        for job in workspace_status.jobs:
            line = f"  {job.job_name}: {job.status}"
            if job.current_step:
                line += f" (Step {job.current_step}, Inc {job.current_increment})"
            if job.errors:
                line += f", {len(job.errors)}个错误"
            if job.warnings:
                line += f", {len(job.warnings)}个警告"
            job_lines.append(line)
        parts.append("作业状态:\n" + "\n".join(job_lines))

    return "\n".join(parts)


@router.post("/chat")
async def agent_chat(request: AgentChatRequest):
    """
    智能体对话端点 — 自主 ReAct Agent

    不再预读文件。只提供工作区元数据，让 LLM 自己用工具探索和行动。
    """
    import json

    import litellm as _litellm
    from starlette.responses import StreamingResponse

    from abaqusgpt.llm.client import MODEL_MAPPING, _setup_api_keys

    workspace = Path(request.workspace_path)
    if not workspace.exists():
        raise HTTPException(status_code=404, detail="工作目录不存在")

    _setup_api_keys()

    # 获取轻量级工作区快照（只有文件列表和作业状态，不读文件内容）
    try:
        workspace_status = scan_workspace(request.workspace_path)
    except Exception:
        workspace_status = None

    workspace_snapshot = build_workspace_snapshot(request.workspace_path, workspace_status)

    model_name = request.model or 'gpt-4o'
    litellm_model = MODEL_MAPPING.get(model_name, model_name)

    # ReAct 智能体循环，通过 SSE 推送步骤和内容
    async def generate():
        try:
            import asyncio
            import json as _json
            loop = asyncio.get_event_loop()

            # ── 初始步骤事件 ──
            yield f"data: {json.dumps({'type': 'step', 'step': 'agent_init', 'message': '自主 Agent 模式'}, ensure_ascii=False)}\n\n"

            # ── 系统提示词：自主智能体 ──
            system_content = f"""你是 AbaqusGPT — 一个专业的 Abaqus 有限元分析 AI 智能体。

## 核心原则
你是一个**自主行动的智能体**，不是一个被动回答问题的聊天机器人。
收到用户问题后，你应该**主动思考、主动探索**，像一位资深 CAE 工程师一样行动：
1. **先规划**：思考需要做什么，需要哪些信息
2. **主动用工具获取信息**：不要猜测文件内容，用 file_read 去看；不知道目录结构，用 file_list 去查
3. **分步执行**：复杂任务分解成多步，每步用工具完成
4. **给出结论**：基于真实数据给出专业建议

## 你的工具
### 基础工具
- **shell_exec**: 在 Linux 容器内执行命令（grep、awk、wc 等文本处理）
- **file_list**: 列出目录内容，了解有哪些文件
- **file_read**: 读取文件内容（支持 max_lines 和 tail 参数控制范围）
- **file_write**: 在 /workspace 下创建或修改文件
- **find_path**: 搜索文件或目录
- **host_exec**: 在 Windows 宿主机上执行命令

### 专业分析工具（优先使用！比手动 grep 更准确）
- **diagnose_convergence(job_dir, job_name)**: 调用 ConvergeDoctor 专业诊断收敛问题，自动解析 .msg/.sta 文件 + 匹配 200+ 已知错误模式，返回根因分析和修复建议
- **analyze_mesh(inp_file)**: 调用 MeshAdvisor 分析网格质量，返回单元类型、节点数、质量评估和优化建议
- **generate_inp(description, output_path, format, domain)**: 调用 InpGenerator 从自然语言生成 INP 文件或 Python 脚本
- **analyze_output(job_dir, job_name, output_type)**: 解析输出文件，提取收敛历史、问题增量步等结构化结果
  - Abaqus 在宿主机: D:\\200_Scientific\\2060_SIMULIA\\002-Commands\\abaqus.bat
  - 宿主机路径示例: E:\\Desktop\\abaqus_agent\\...
  - **提交作业必须后台运行**: start /b abaqus job=<name> cpus=8（不加 start /b 会超时！）
  - 提交后用 file_read 查看 .log 和 .sta 确认作业是否开始运行
  - 如返回"Host Bridge 不可用"，提示用户运行 python host_bridge.py
  - cwd 会自动设为当前工作目录对应的 Windows 路径，通常不需要手动指定

## 当前工作区
{workspace_snapshot}

Docker 容器中路径 /workspace 对应宿主机的 E:\\Desktop\\abaqus_agent

## 行为准则
- **优先用专业工具**：分析收敛用 diagnose_convergence，分析网格用 analyze_mesh，查看结果用 analyze_output。不要用 shell_exec 手动 grep 来做这些事
- **不要猜测**：不知道的信息就用工具去查
- **不要偷懒**：如果用户问文件内容，用 file_read 读了再回答，不要说"请自行查看"
- **结果导向**：直接给出答案和建议，不要说"你可以尝试..."而是直接做
- **INP 文件通常很大**：先用 file_read 的 max_lines=50 看开头概览，再按需读取特定部分
- **MSG 文件看末尾**：用 tail=true 读取最新的错误和警告
- **STA 文件看状态**：了解作业进度和收敛性
- **提交作业用 host_exec**（容器内没有 Abaqus），命令格式: start /b abaqus job=xxx cpus=8
- **提交后立刻用 file_read 查看 .log 文件**确认作业已启动
- **查看容器内文件用 file_read/file_list/shell_exec**

## 主动编程
你可以用 file_write 创建 Python 脚本完成复杂任务：
- 批量处理文件（如提取多个 .sta 的收敛数据）
- 数据分析与统计、生成 matplotlib 图表
- 修改或生成 INP 文件的脚本
- Abaqus Python 后处理脚本（宿主机用 host_exec 执行 abaqus python xxx.py）
当任务涉及批量、重复或复杂逻辑时，**优先写 Python 脚本**然后用 shell_exec 执行。

## 迭代完成
- **任务没完成就继续**：不要半途而废，不要说"你可以自己..."
- **验证结果**：执行操作后用工具验证（文件是否生成、输出是否正确）
- **遇错就修**：看到报错就分析原因、修改、重试
- **多步自动衔接**：如"提交作业并分析"→ 提交 → 确认启动 → 读取结果 → 分析
- 用中文回答"""

            messages: list[dict] = [{"role": "system", "content": system_content}]
            for msg in (request.history or [])[-10:]:
                if hasattr(msg, 'role'):
                    messages.append({"role": msg.role, "content": msg.content})
                else:
                    messages.append({"role": msg.get("role", "user"), "content": msg.get("content", "")})
            messages.append({"role": "user", "content": request.message})

            # ── 原生 Function Calling 循环（litellm 自动适配各模型）──
            MAX_ITERATIONS = 20
            _litellm.drop_params = True  # 不支持 tools 的模型静默忽略

            for iteration in range(MAX_ITERATIONS):
                is_last_chance = (iteration == MAX_ITERATIONS - 1)

                # 每轮推理前发送步骤事件
                iter_msg = f'第 {iteration+1} 轮推理'
                yield f"data: {json.dumps({'type': 'step', 'step': 'calling_llm', 'model': model_name, 'message': iter_msg}, ensure_ascii=False)}\n\n"

                def call_llm_sync(msgs=messages, last=is_last_chance):
                    kw: dict = dict(
                        model=litellm_model,
                        messages=msgs,
                        stream=False,
                        temperature=0.3,
                        timeout=120,
                    )
                    if not last:
                        kw["tools"] = TOOLS_SCHEMA
                        kw["tool_choice"] = "auto"
                    return _litellm.completion(**kw)

                response = await loop.run_in_executor(None, call_llm_sync)
                msg_obj = response.choices[0].message

                # 检查是否有原生 tool_calls
                native_tool_calls = getattr(msg_obj, 'tool_calls', None) or []

                # 如果 LLM 返回了思考内容和工具调用，先发送思考步骤
                if msg_obj.content and native_tool_calls:
                    yield f"data: {json.dumps({'type': 'step', 'step': 'thinking', 'message': msg_obj.content}, ensure_ascii=False)}\n\n"

                if not native_tool_calls or is_last_chance:
                    # 无工具调用 → 输出最终文本
                    response_text: str = msg_obj.content or ""
                    chunk_size = 80
                    for i in range(0, len(response_text), chunk_size):
                        yield f"data: {json.dumps({'type': 'content', 'content': response_text[i:i+chunk_size]}, ensure_ascii=False)}\n\n"
                    break

                # 处理所有工具调用（一次可能有多个）
                # 先把 assistant 消息加进 messages
                messages.append(msg_obj.model_dump() if hasattr(msg_obj, 'model_dump') else {"role": "assistant", "tool_calls": [tc.model_dump() for tc in native_tool_calls]})

                for tc in native_tool_calls:
                    tool_name_tc = tc.function.name
                    try:
                        tool_params_tc = _json.loads(tc.function.arguments or "{}")
                    except Exception:
                        tool_params_tc = {}
                    tool_call_id = tc.id

                    cmd_preview = (
                        tool_params_tc.get('command') or
                        tool_params_tc.get('path') or
                        tool_params_tc.get('name') or ''
                    )[:120]

                    yield f"data: {json.dumps({'type': 'step', 'step': 'tool_call', 'tool': tool_name_tc, 'command': cmd_preview}, ensure_ascii=False)}\n\n"

                    tool_result = await run_tool(tool_name_tc, tool_params_tc, request.workspace_path)

                    result_preview = tool_result[:300].replace('\n', ' ')
                    yield f"data: {json.dumps({'type': 'step', 'step': 'tool_result', 'tool': tool_name_tc, 'output': result_preview, 'full_output': tool_result}, ensure_ascii=False)}\n\n"

                    # 将 tool 结果加回 messages（OpenAI tool message 格式）
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": tool_result,
                    })

            # ── 完成信号 ──
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        except Exception as e:
            import traceback
            yield f"data: {json.dumps({'type': 'error', 'error': str(e), 'traceback': traceback.format_exc()}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

