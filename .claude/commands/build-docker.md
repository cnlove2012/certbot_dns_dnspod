---
description: 构建插件 Docker 镜像并做插件注册冒烟测试
---

构建 certbot-dns-dnspod 的 Docker 镜像并验证插件在容器内正确注册。

## 步骤

1. `docker build -t certbot-dns-dnspod:dev .`（基础镜像版本由 Dockerfile 的
   `ARG CERTBOT_VERSION` 固定，如需其他版本用
   `docker build --build-arg CERTBOT_VERSION=vX.Y.Z` 覆盖）。
2. 冒烟测试：`docker run --rm certbot-dns-dnspod:dev --help all 2>/dev/null | grep -A3 dns-dnspod`
   ——输出应包含 `dns-dnspod` 插件的描述与参数说明。
3. 报告构建耗时、镜像大小（`docker images certbot-dns-dnspod:dev`）与冒烟结果。

> 提示：`tools/pip_install.py` 来自 certbot 官方基础镜像（本地仓库中没有此文件，属正常）。
