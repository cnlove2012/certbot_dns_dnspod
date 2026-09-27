# CLAUDE.md

本文件为 Claude Code 在此仓库中工作时的项目指引。

## 项目概述

certbot 的 DNSPod（腾讯云）DNS-01 认证插件。用户通过 `--dns-dnspod-credentials` 提供
腾讯云 API 密钥，插件在 DNSPod 托管区创建/删除 `_acme-challenge` TXT 记录完成
ACME dns-01 挑战（支持通配符证书）。

- 布局：src layout，包在 `src/certbot_dns_dnspod/`
- 核心代码：`src/certbot_dns_dnspod/_internal/dns_dnspod.py`（全项目唯一实现文件）
- 插件注册：pyproject.toml 中 entry point
  `dns-dnspod = certbot_dns_dnspod._internal.dns_dnspod:Authenticator`
- Python >= 3.9（3.9 环境自动搭配 certbot 4.x；3.10+ 搭配 certbot 5.x，两者 API 兼容）

## 常用命令

**本项目以 DevContainer 为主要开发环境**（`.devcontainer/devcontainer.json`，
Python 3.12-bookworm）。在容器内依赖已由 `postCreateCommand` 装好
（`pip install -e '.[test]' ruff mypy pre-commit` + pre-commit hook），命令直接执行：

```bash
# 测试（纯 mock，无网络、无真实凭证）
python -m pytest

# 静态检查
ruff check src/
ruff format --check src/
mypy src/
pre-commit run --all-files

# 构建
pip install build && python -m build   # 产出 dist/ 下 sdist+wheel

# Docker（基础镜像版本固定于 Dockerfile 的 ARG CERTBOT_VERSION）
docker build -t certbot-dns-dnspod:dev .
# 冒烟：容器内 certbot 应能发现 dns-dnspod 插件
docker run --rm certbot-dns-dnspod:dev --help all 2>/dev/null | grep -A3 dns-dnspod
```

若在宿主机（macOS）临时开发，需自建环境后再执行上述命令：

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]" ruff mypy pre-commit
```

CI（.github/workflows/ci.yml）在 Python 3.9–3.13 矩阵上跑 lint+mypy+pytest。

**自动发版**（.github/workflows/docker-publish.yml）：push main（PR 合并或直接 push）
**且含非文档类改动**时全自动发版——纯文档/AI 配置改动跳过（不打 tag、不占 build 号，
`paths-ignore` 豁免列表与 ci.yml 一致）。流程为：前置快速检查 job → 计算 CalVer 版本
（`年.周.build`，ISO 周，如 `v2026.39.1`）→ **立即推 tag**（尽早落库）→ pyproject
version 写回 main（`chore(release)` 提交，github-actions[bot]）→ GitHub Release
（自动变更说明）→ 一次构建双推送 Docker Hub 与阿里云 ACR 杭州
（registry.cn-hangzhou.aliyuncs.com/cnlove2012/certbot-dns-dnspod），各推版本镜像 +
`latest`，Docker Hub 拉回冒烟（需仓库 secrets `DOCKERHUB_USERNAME`/`DOCKERHUB_TOKEN`、
`ALIYUN_REGISTRY_USERNAME`/`ALIYUN_REGISTRY_PASSWORD`，未配置/失效时对应 Login 步骤
直接报错）。构建必须 `provenance: false`——attestation 的 `oci.empty.v1+json` 空层
不被阿里云 ACR 个人版识别。

发版语义要点（设计取舍，勿"修复"）：

- **仅必要变更发版**（2026-09-27 决策，取代早期"每合并必发版"）：纯文档类 push
  不触发发版、不占 build 号；确需发布时 workflow_dispatch 手动补发。

- tag 打在 merge commit 上、写回 version 的 commit 在 tag 之后——version 字段
  滞后一版属预期（记录性质，运行时无影响）。
- 快速连续 push 时 `cancel-in-progress: true` 会取消进行中的旧发布：旧版本的
  tag 已保留、其镜像可能缺失，`latest` 始终由最后一次成功构建决定（用户认可的取舍）。
- tag/写回/Release 均在同一 workflow 内完成——GITHUB_TOKEN 的 push 不触发其他
  workflow（GitHub 防递归），拆开会导致镜像构建不触发。
- 手动补发：Actions → Docker Publish → Run workflow（main 分支）。

## 架构

两个类，职责严格分离（`_internal/dns_dnspod.py`）：

- `Authenticator(dns_common.DNSAuthenticator)`：certbot 插件入口。
  `_setup_credentials` 读取凭证 ini；`_perform`/`_cleanup` 委托给 `_DNSPodClient`。
  生命周期由 certbot 保证：perform 前必先 `_setup_credentials`。
- `_DNSPodClient`：封装腾讯云 SDK。构造时一次性拉取 `DescribeDomainList` 建立
  域名→DomainId 映射（`self.domain_list`，dict，不缓存失效）。

关键约定：

- **凭证 ini 键名带插件前缀**：`dns_dnspod_secret_id` / `dns_dnspod_secret_key`
  （`CredentialsConfiguration` 以插件名 `dns-dnspod` 作前缀读取，`conf("secret_id")`
  内部会自动加前缀）。测试写 ini 时必须用带前缀键名。
- **SubDomain 是相对主机记录**：完整记录名 `_acme-challenge.example.cn` 需
  `record_name.removesuffix(f".{zone}")` 转为 `_acme-challenge` 后传给 SDK。
- `RecordLine` 固定 `"默认"`。
- `DescribeRecordList` 的 `ErrorOnEmpty` 必须显式设 `"no"`（默认 yes 时无记录会抛
  `ResourceNotFound.NoData` 而非返回空列表）；`Limit` 上限 3000。
- `_find_domain_id` 做精确/点边界 + 最长区匹配（`devexample.cn` 不得命中 `example.cn`）。
- 所有 `TencentCloudSDKException` 必须转译为 `certbot.errors.PluginError`（`raise ... from err`）。
- `del_txt_record` 是 cleanup 路径：尽力而为，域名缺失时静默跳过而非抛错。

## 代码风格

- ruff：规则集见 pyproject.toml（E/F/W/I/B/UP/C4/SIM/RUF），行宽 100，
  isort 一行一导入（certbot 官方风格），中文注释中的全角标点豁免（RUF001-003 已忽略）。
- 格式化用 `ruff format`（不用 black）。
- docstring 用 reST 风格（`:param str domain: ...`），与 certbot 官方插件一致。
- 测试中访问下划线方法/属性加 `# pylint: disable=protected-access`，
  mock 替换方法加 `# type: ignore[method-assign]`。

## 安全规约（最高优先级）

- **任何改动不得引入硬编码凭证**。测试只用 `FAKE_SECRET_ID`/`FAKE_SECRET_KEY` 常量与 mock。
- `*.pem`、`credentials.ini`、`letsencrypt/`、`.env` 已被 .gitignore/.dockerignore 双重拦截，
  不得为"临时调试"绕过。
- 本仓库历史上有过密钥泄露整改（详见 git log `chore: 清理敏感调试脚本`），前车之鉴。
- 若在代码/文件中发现疑似真实密钥（`AKID` 开头的 SecretId 等），立即停止操作并提示用户
  去腾讯云 CAM 控制台轮换密钥——删除文件不能消除既有暴露。
- 不在日志中打印凭证或签名头；debug 日志只记录响应体。

## 已知注意事项

- certbot 5.x 的 `DNSAuthenticator.perform` 末尾无条件调用 `display_util.notify`，
  测试环境需 patch（见 AuthenticatorTest.setUp）。
- mypy 检查目标为 3.10（新版 mypy 不支持 3.9 目标）；3.9 语法兼容由 ruff
  `target-version = "py39"` 把关，勿在代码中使用 3.10+ 语法（如 `X | Y` 类型标注）。
- 升级 certbot 基础镜像：改 Dockerfile `ARG CERTBOT_VERSION` 后重新构建并跑冒烟。

## AI 协作配置

- 项目命令：`.claude/commands/`（`/test-plugin` 本地全量检查、`/build-docker` 镜像构建冒烟、
  `/release` 发布流程）。
- 子代理：`.claude/agents/`（`code-reviewer` 代码审查、`release-helper` 发布助手）。
- 通用 AI 工具兼容入口：AGENTS.md（指向本文件）。
