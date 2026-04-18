# AI PR Review Setup Guide | AI PR 代码审查设置指南

[English](#english) | [中文](#中文)

---

## English

This project uses **GitHub Copilot Code Review** to automatically review pull requests.

### Prerequisites

- GitHub Copilot subscription (Individual/Business/Enterprise)

### How It Works

Every time you create a PR:
1. Copilot automatically reviews code changes
2. Provides suggestions as PR comments
3. You can ask follow-up questions with `@copilot`

### Manual Trigger

In any PR comment:
```
@copilot /review
```

### Skip Review

Add these labels to skip automatic review:
- `skip-review`
- `no-copilot`
- `wip`

### Configuration

See [.github/copilot-code-review.yml](../.github/copilot-code-review.yml)

---

## 中文

本项目使用 **GitHub Copilot 代码审查** 自动审查 Pull Request。

### 前提条件

- 需要 GitHub Copilot 订阅（Individual/Business/Enterprise）

### 工作原理

每次创建 PR 时：
1. Copilot 自动审查代码变更
2. 以 PR 评论形式提供建议
3. 可以用 `@copilot` 进行追问

### 手动触发

在任意 PR 评论中输入：
```
@copilot /review
```

### 跳过审查

添加以下标签可跳过自动审查：
- `skip-review`
- `no-copilot`
- `wip`

### 配置文件

详见 [.github/copilot-code-review.yml](../.github/copilot-code-review.yml)

---

## References | 参考资料

- [GitHub Copilot Code Review Docs](https://docs.github.com/en/copilot/using-github-copilot/code-review)

## References | 参考资料

- [StructureClaw Repository](https://github.com/structureclaw/structureclaw) - Uses Gemini + Copilot
- [GitHub Copilot Code Review Docs](https://docs.github.com/en/copilot/using-github-copilot/code-review)
- [Gemini Code Assist Docs](https://cloud.google.com/gemini/docs/code-assist)
- [CodeRabbit Docs](https://docs.coderabbit.ai/)
