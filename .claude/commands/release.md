---
description: 发布新版本（版本 bump → CHANGELOG → tag → 构建 → 校验）
---

使用 release-helper 子代理的流程发布一个新版本。

## 步骤

1. 先运行一次本地全量检查（等同 /test-plugin），任何失败则终止。
2. 询问我目标版本号与本次发布的主要内容（用于 CHANGELOG 摘要）。
3. 委托 release-helper 代理执行完整发布流程（版本 bump、CHANGELOG、tag、
   sdist/wheel 构建、twine check、Docker 构建冒烟）。
4. 每个关键节点（版本号写入、tag 创建、构建完成）向我汇报。
5. 推送到远程（`git push --tags`）前必须获得我的明确确认。
