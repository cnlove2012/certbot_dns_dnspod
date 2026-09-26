---
description: 发版核对 / 手动补发（发版本身已全自动：push main 即 CalVer 发版）
---

发版已全自动：push main（PR 合并或直接 push）后 Docker Publish 工作流自动完成
CalVer 版本计算（年.周.build）→ tag → pyproject 写回 → GitHub Release →
Docker Hub 版本镜像 + latest → 冒烟。本命令用于**核对发版结果**或**手动补发**。

## 步骤

1. 核对最近发版产物（委托 release-helper 代理执行）：
   新 tag、docker-publish 工作流状态、GitHub Release、版本镜像冒烟。
2. 若某次合并未产生版本（如 secrets 失效、权限错），修复根因后补发：
   `gh workflow run docker-publish.yml --ref main`。
3. 被取消（cancelled）的 run 属预期——快速连续 push 时旧发布让位，
   旧 tag 保留、镜像可能缺失，latest 由最后一次成功构建决定。
4. 详细排查指引见 release-helper 代理定义。
