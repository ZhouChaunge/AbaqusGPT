<div align="center">

# AAAR — Auto Abaqus Agent Research

**自主式 AI 有限元分析智能体 / Autonomous AI Agent for Abaqus Finite Element Analysis**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)

[Features](#features) | [Quick Start](#quick-start) | [Architecture](#architecture) | [Contributing](#contributing)

</div>

---

## What is AAAR?

AAAR (Auto Abaqus Agent Research) 是一个**自主式 AI 智能体**，专为 Abaqus 有限元分析设计。它不是简单的 LLM 聊天包装器——而是一个能够**自主思考、主动探索、调用专业工具**的 ReAct Agent。

AAAR is an **autonomous AI agent** purpose-built for Abaqus FEA. It goes beyond a simple LLM chat wrapper — it **thinks, explores, and acts** using a ReAct loop with professional domain tools.

**核心能力 / Core Capabilities:**
- 🤖 **ReAct Agent** — 自主规划、工具调用、迭代求解，而非被动回答
- 🔧 **10+ 专业工具** — 收敛诊断、网格分析、INP 生成、输出解析，一键调用
- 🏗️ **三面板 IDE** — 文件树 + 代码查看器 + AI 对话，在 Web 上操作 Abaqus 项目
- 🌐 **15+ LLM 供应商** — OpenAI、Claude、Gemini、DeepSeek、通义千问等国内外模型
- 📡 **宿主机桥接** — Docker 内的 Agent 安全调用 Windows 上的 Abaqus 命令

---

## Features

| Module | Description |
|--------|-------------|
| **Convergence Doctor** | 自动诊断 `.msg`/`.sta` 文件，匹配 200+ 已知错误模式，给出根因分析和修复方案 |
| **Mesh Advisor** | 网格质量评估 + 单元类型建议 + 网格优化方案 |
| **INP Generator** | 自然语言 → `.inp` 文件或 Python 脚本，支持多工程领域 |
| **Output Analyzer** | 解析输出文件，提取收敛历史、识别问题增量步 |
| **Workspace Monitor** | 三面板 IDE：实时文件浏览、代码查看、AI Agent 对话 |
| **Domain Expert** | 9 大工程领域专业知识（岩土、结构、机械、热分析、冲击等） |
| **Host Bridge** | Docker 容器安全调用 Windows 宿主机上的 Abaqus 命令 |

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
git clone https://github.com/ZhouChaunge/Auto-Abaqus-Agent-Research.git
cd Auto-Abaqus-Agent-Research
docker-compose up -d

# Access:
# - Web UI:  http://localhost:3000
# - API:     http://localhost:8000
# - API Docs: http://localhost:8000/docs

# (Optional) Start host bridge for Abaqus command execution:
python host_bridge.py
```

### Option 2: Local Development

```bash
git clone https://github.com/ZhouChaunge/Auto-Abaqus-Agent-Research.git
cd Auto-Abaqus-Agent-Research
pip install -e ".[dev]"
cd frontend && npm install && cd ..
cp .env.example .env
uvicorn server.main:app --reload
```

### Option 3: CLI Only

```bash
pip install abaqusgpt
abaqusgpt diagnose Job-1.msg
abaqusgpt generate "Steel plate 20x10x5mm, fixed bottom, 10MPa pressure"
abaqusgpt ask "What is the difference between C3D8R and C3D8?"
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  Frontend (React + Tailwind)                │
│  Chat Page │ Monitor IDE (3-panel) │ Knowledge │ Settings   │
├─────────────────────────┬───────────────────────────────────┤
│                         │ HTTP / SSE / WebSocket            │
├─────────────────────────▼───────────────────────────────────┤
│                  Backend (FastAPI)                           │
│  Chat API │ Workspace API │ Providers API │ Models API      │
├─────────────────────────┬───────────────────────────────────┤
│                         │                                   │
├─────────────────────────▼───────────────────────────────────┤
│              ReAct Agent (Tool-Calling Loop)                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │shell_exec│ │file_read │ │host_exec │ │file_write│  ... │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌────────────────┐ ┌────────────┐ ┌──────────────┐       │
│  │diagnose_conv.  │ │analyze_mesh│ │generate_inp  │  ...  │
│  │(ConvergeDoctor)│ │(MeshAdvisor)│ │(InpGenerator)│       │
│  └────────────────┘ └────────────┘ └──────────────┘       │
├─────────────────────────┬───────────────────────────────────┤
│                         │                                   │
├─────────────────────────▼───────────────────────────────────┤
│                  Knowledge Base                             │
│  Error Database (200+) │ Element Library │ Domain Knowledge │
│  Geotechnical │ Structural │ Mechanical │ Thermal │ Impact │
├─────────────────────────┬───────────────────────────────────┤
│                         │                                   │
├─────────────────────────▼───────────────────────────────────┤
│                  LLM Providers (15+)                        │
│  OpenAI │ Claude │ Gemini │ DeepSeek │ Qwen │ Ollama │ ... │
├─────────────────────────┬───────────────────────────────────┤
│                         │ Host Bridge (HTTP)                │
├─────────────────────────▼───────────────────────────────────┤
│            Windows Host (Abaqus Runtime)                    │
└─────────────────────────────────────────────────────────────┘
```

---

## Agent Tool Chain

AAAR 的核心创新是将专业 Abaqus 分析能力封装为 Agent 可调用的工具：

| Tool | Description | Backed By |
|------|-------------|-----------|
| `diagnose_convergence` | 收敛问题诊断，匹配 200+ 错误模式 | ConvergeDoctor + MsgParser + StaParser + ErrorDB |
| `analyze_mesh` | 网格质量分析 | MeshAdvisor + InpParser |
| `generate_inp` | 自然语言生成 INP/Python | InpGenerator + LLM |
| `analyze_output` | 输出解析（收敛历史、问题增量步） | StaParser + MsgParser |
| `shell_exec` | 容器内 bash 命令 | subprocess |
| `file_read/write/list` | 文件操作 | filesystem |
| `host_exec` | 宿主机命令执行（Abaqus） | Host Bridge |
| `find_path` | 文件搜索 | find |

**调用链示例 / Example Call Chain:**
```
用户: "帮我分析 job_015 为什么不收敛"
  → Agent 调用 file_list(job_dir)  → 发现 .msg, .sta, .inp 文件
  → Agent 调用 diagnose_convergence(job_dir, "job_015")  → 返回结构化诊断
  → Agent 调用 analyze_mesh("job_015.inp")  → 返回网格质量报告
  → Agent 综合所有信息，给出分析报告和修改建议
```

---

## Domain Knowledge

| Domain | Coverage |
|--------|----------|
| **Geotechnical** | Mohr-Coulomb, Drucker-Prager, CAM-Clay; Soil-structure interaction |
| **Structural** | Concrete Damaged Plasticity (CDP); Rebar modeling; Seismic analysis |
| **Mechanical** | Contact analysis; Gear/bearing modeling; Fatigue |
| **Thermal** | Heat transfer; Thermal-stress coupling; Phase change |
| **Impact** | Explicit solver; Collision; Penetration; Blast |
| **Composite** | Laminate modeling; Hashin failure; Delamination |
| **Biomechanical** | Soft tissue hyperelasticity; Bone modeling |
| **Electromagnetic** | EM-thermal-structural coupling |

---

## Supported LLM Providers

| Provider | Models | Config |
|----------|--------|--------|
| OpenAI | GPT-4, GPT-4o | `OPENAI_API_KEY` |
| Anthropic | Claude 3.5/4 | `ANTHROPIC_API_KEY` |
| DeepSeek | DeepSeek-V3 | `DEEPSEEK_API_KEY` |
| Zhipu AI | GLM-4 | `ZHIPU_API_KEY` |
| Qwen | qwen-max | `DASHSCOPE_API_KEY` |
| Moonshot | Kimi | `MOONSHOT_API_KEY` |
| Ollama | Local models | `OLLAMA_BASE_URL` |

---

## Configuration

```bash
cp .env.example .env
# Edit .env and add your API keys
```

---

## License

MIT License - see [LICENSE](LICENSE)

---

<div align="center">

**AAAR** — Auto Abaqus Agent Research

Making Finite Element Analysis Smarter

[Report Bug](https://github.com/ZhouChaunge/Auto-Abaqus-Agent-Research/issues) | [Request Feature](https://github.com/ZhouChaunge/Auto-Abaqus-Agent-Research/issues)

</div>
