# AGENTS.md

本仓库的 AI 助手工作规范统一见 [CLAUDE.md](CLAUDE.md)（项目结构、常用命令、
架构说明、代码风格、安全规约）。

Claude Code 专用配置在 `.claude/`：

- 命令：`/test-plugin`（本地全量检查）、`/build-docker`（镜像构建冒烟）、`/release`（发布流程）
- 子代理：`code-reviewer`（代码审查）、`release-helper`（发布助手）
