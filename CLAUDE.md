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

```bash
# 环境（本地用 python3.12）
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]" ruff mypy pre-commit

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

CI（.github/workflows/ci.yml）在 Python 3.9–3.13 矩阵上跑 lint+mypy+pytest。

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
