<div align="center">

# AbaqusGPT

**AI-Powered Assistant for Abaqus Finite Element Analysis**

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-61DAFB?logo=react&logoColor=black)](https://reactjs.org/)

[Features](#features) | [Quick Start](#quick-start) | [Documentation](#documentation) | [Contributing](#contributing)

</div>

---

## Features

| Module | Description |
|--------|-------------|
| **Convergence Doctor** | Automatically diagnose `.msg`/`.sta` files and identify root causes |
| **Model Generator** | Natural language to `.inp` files or Python scripts |
| **Mesh Advisor** | Mesh quality assessment + optimization suggestions |
| **Result Interpreter** | Help understand simulation outputs and check reasonability |
| **Domain Q&A** | Multi-domain knowledge base (Geotechnical, Structural, Mechanical, Thermal...) |

---

## Quick Start

### Option 1: Docker (Recommended)

```bash
docker-compose up -d

# Access:
# - Web UI:  http://localhost:3000
# - API:     http://localhost:8000
# - API Docs: http://localhost:8000/docs
```

### Option 2: Local Development

```bash
git clone https://github.com/ZhouChaunge/AbaqusGPT.git
cd AbaqusGPT
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
+-------------------------------------------------------------+
|                    Frontend (React + Tailwind)               |
+-----------------------------+-------------------------------+
                              | HTTP / WebSocket
+-----------------------------v-------------------------------+
|                    Backend (FastAPI)                         |
+-----------------------------+-------------------------------+
                              |
+-----------------------------v-------------------------------+
|                    Agents Layer                              |
|  Converge Doctor | Inp Generator | Mesh Advisor | Material  |
+-----------------------------+-------------------------------+
                              |
+-----------------------------v-------------------------------+
|                    Knowledge Base                            |
|  Geotechnical | Structural | Mechanical | Thermal | Impact  |
+-----------------------------+-------------------------------+
                              |
+-----------------------------v-------------------------------+
|                    LLM Providers                             |
|  OpenAI | Claude | Ollama | DeepSeek | 15+ more providers   |
+-------------------------------------------------------------+
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

**AbaqusGPT** - Making Finite Element Analysis Easier

[Report Bug](https://github.com/ZhouChaunge/AbaqusGPT/issues) | [Request Feature](https://github.com/ZhouChaunge/AbaqusGPT/issues)

</div>
