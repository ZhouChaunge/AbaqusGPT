# AI PR Review Setup Guide | AI PR 代码审查设置指南

[English](#english) | [中文](#中文)

---

## English

This project supports multiple AI code review tools to automatically review pull requests and provide suggestions.

### Supported Tools

| Tool | Type | Cost | Features |
|------|------|------|----------|
| **GitHub Copilot** | GitHub Native | Requires Copilot subscription | Auto review, PR summary |
| **Gemini Code Assist** | Google App | Free | Security scanning, best practices |
| **CodeRabbit** | Third-party App | Free tier available | Detailed review, learning system |

### 1. GitHub Copilot Code Review ⭐ Recommended

**Prerequisites:**
- GitHub Copilot subscription (Individual/Business/Enterprise)

**Setup:**
1. Go to your repository **Settings** → **General**
2. Scroll to **Features** section
3. Enable **"Copilot"** → **"Code review"**

**Trigger manually:**
```
@copilot /review
```

**Configuration:** [.github/copilot-code-review.yml](../.github/copilot-code-review.yml)

---

### 2. Gemini Code Assist (Google)

**Installation:**
1. Visit [GitHub Marketplace - Gemini Code Assist](https://github.com/marketplace/gemini-code-assist)
2. Click "Install it for free"
3. Select repository `ZhouChaunge/AbaqusGPT`
4. Complete authorization

**Features:**
- Automatic PR code review
- Security vulnerability detection
- Code style suggestions
- Supports Chinese & English

**Configuration:** [.gemini/config.yaml](../.gemini/config.yaml)

---

### 3. CodeRabbit (Optional)

**Installation:**
1. Visit [CodeRabbit.ai](https://coderabbit.ai)
2. Sign in with GitHub
3. Select repository to install

**Features:**
- Detailed line-by-line review
- Learning from your codebase
- Interactive chat in PR comments
- Support for Chinese comments

**Configuration:** [.coderabbit.yaml](../.coderabbit.yaml)

---

### How It Works

After installation, every time you create a PR:
1. AI automatically reviews code changes
2. Provides suggestions as PR comments
3. You can @ the bot to ask questions

### Skip Review

Add these labels to skip automatic review:
- `skip-review`
- `no-copilot`
- `wip`

---

## 中文

本项目支持多种 AI 代码审查工具，可自动审查 Pull Request 并提供改进建议。

### 支持的工具

| 工具 | 类型 | 费用 | 功能特点 |
|------|------|------|----------|
| **GitHub Copilot** | GitHub 原生 | 需 Copilot 订阅 | 自动审查、PR 摘要生成 |
| **Gemini Code Assist** | Google App | 免费 | 安全扫描、最佳实践检查 |
| **CodeRabbit** | 第三方 App | 免费版可用 | 详细审查、学习系统 |

### 1. GitHub Copilot 代码审查 ⭐ 推荐

**前提条件：**
- 需要 GitHub Copilot 订阅（Individual/Business/Enterprise）

**设置步骤：**
1. 进入仓库 **Settings** → **General**
2. 向下滚动到 **Features** 部分
3. 启用 **"Copilot"** → **"Code review"**

**手动触发审查：**
```
@copilot /review
```

**配置文件：** [.github/copilot-code-review.yml](../.github/copilot-code-review.yml)

---

### 2. Gemini Code Assist (Google)

**安装步骤：**
1. 访问 [GitHub Marketplace - Gemini Code Assist](https://github.com/marketplace/gemini-code-assist)
2. 点击 "Install it for free"
3. 选择仓库 `ZhouChaunge/AbaqusGPT`
4. 完成授权

**功能特点：**
- PR 自动代码审查
- 安全漏洞检测
- 代码风格建议
- 支持中英文评论

**配置文件：** [.gemini/config.yaml](../.gemini/config.yaml)

---

### 3. CodeRabbit（可选）

**安装步骤：**
1. 访问 [CodeRabbit.ai](https://coderabbit.ai)
2. 使用 GitHub 登录
3. 选择要安装的仓库

**功能特点：**
- 逐行详细审查
- 从代码库学习你的风格
- PR 评论区交互式对话
- 支持中文评论

**配置文件：** [.coderabbit.yaml](../.coderabbit.yaml)

---

### 使用方式

安装后，每次创建 PR 时：
1. AI 会自动审查代码变更
2. 在 PR 评论区给出建议
3. 可以 @ 机器人进行对话提问

### 跳过审查

添加以下标签可跳过自动审查：
- `skip-review`
- `no-copilot`
- `wip`

---

## References | 参考资料

- [StructureClaw Repository](https://github.com/structureclaw/structureclaw) - Uses Gemini + Copilot
- [GitHub Copilot Code Review Docs](https://docs.github.com/en/copilot/using-github-copilot/code-review)
- [Gemini Code Assist Docs](https://cloud.google.com/gemini/docs/code-assist)
- [CodeRabbit Docs](https://docs.coderabbit.ai/)
