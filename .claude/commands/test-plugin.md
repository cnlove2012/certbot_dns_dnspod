---
description: 本地全量质量检查（ruff + mypy + pytest + pre-commit）
---

对本仓库运行完整的本地质量检查流水线，并汇总结果。

## 步骤

1. 确认开发环境就绪：本项目以 DevContainer 开发（Python 3.12，
   postCreateCommand 已安装依赖）。先运行 `python -c "import certbot_dns_dnspod"`
   探测；若模块缺失（例如在宿主机裸环境），先执行
   `pip install -e '.[test]' ruff mypy pre-commit` 补装。
2. 依序执行以下命令，逐条记录通过/失败：
   ```bash
   ruff check src/
   ruff format --check src/
   mypy src/
   python -m pytest -v
   pre-commit run --all-files
   ```
3. 任何一步失败：展示完整失败输出，定位原因并给出修复建议（不要自行改动代码，除非我明确要求）。
4. 最后输出汇总表格：检查项 | 结果 | 备注。

> 注意：测试全部基于 mock，无需真实腾讯云凭证或网络。
