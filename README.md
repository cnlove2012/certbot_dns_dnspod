# certbot-dns-dnspod

[![CI](https://github.com/cnlove2012/certbot_dns_dnspod/actions/workflows/ci.yml/badge.svg)](https://github.com/cnlove2012/certbot_dns_dnspod/actions/workflows/ci.yml)
[![Docker Pulls](https://img.shields.io/docker/pulls/cnlove2012/certbot-dns-dnspod.svg)](https://hub.docker.com/r/cnlove2012/certbot-dns-dnspod)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

[Certbot](https://certbot.eff.org/) 的 DNSPod（腾讯云）DNS 认证插件。
通过腾讯云 DNSPod API 自动创建与删除 `_acme-challenge` TXT 记录，完成 ACME
`dns-01` 挑战——**支持通配符证书**（如 `*.example.com`）。

## 背景：certbot 与 DNS-01 挑战

[Certbot](https://certbot.eff.org/) 是 EFF（电子前哨基金会）维护的开源工具，
用于从 [Let's Encrypt](https://letsencrypt.org/) 免费签发 HTTPS 证书并自动续期
（证书有效期 90 天，到期前 30 天可续）。Let's Encrypt 通过"挑战"验证域名所有权，
其中 DNS-01 方式只需在域名解析中临时创建一条 TXT 记录：

- 无需公网可达的 80 端口，内网/离线机器也能签发证书
- 是签发**通配符证书**（`*.example.com`）的唯一途径

官方 certbot 内置 Cloudflare、Route53 等国际 DNS 服务商插件，但不支持
DNSPod——本插件（及 Docker 镜像）补上这块拼图：申请时自动创建 TXT 记录，
验证通过后自动删除。

详细用法见 [docs/dockerhub-overview.md](docs/dockerhub-overview.md)（与
Docker Hub 页面同源）。

## 凭证获取

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)，进入
   **访问管理 CAM → API 密钥管理**，创建 `SecretId` 与 `SecretKey`。
2. 建议使用子账号密钥，并只授予 `QcloudDNSPodFullAccess` 策略（最小权限）。
3. 创建凭证目录与凭证文件（下文统一使用此路径）：

   ```bash
   mkdir -p ./certbot/letsencrypt/.secrets
   ```

   ```ini
   dns_dnspod_secret_id = 你的SecretId
   dns_dnspod_secret_key = 你的SecretKey
   ```

   将上述内容保存为 `./certbot/letsencrypt/.secrets/credentials.ini`。

4. 收紧权限（Certbot 检测到权限过宽会持续警告）：

   ```bash
   chmod 600 ./certbot/letsencrypt/.secrets/credentials.ini
   ```

> ⚠️ 请像保管密码一样保管该文件。能读取它的任何人都可以操作你的 DNSPod 解析记录。
> `./certbot/letsencrypt/` 已被 .gitignore/.dockerignore 拦截，凭证与证书数据
> 不会被提交到仓库或打进镜像。

## 安装与使用（Docker）

### 1. 获取镜像

直接使用 [Docker Hub](https://hub.docker.com/r/cnlove2012/certbot-dns-dnspod) 上的现成镜像（推荐）：

```bash
docker pull cnlove2012/certbot-dns-dnspod:latest
```

> 生产环境建议固定版本号（如 `docker pull cnlove2012/certbot-dns-dnspod:2026.39.1`）。
> 版本号为 CalVer 格式 `年.周.build`（ISO 周序号），每次合并到 main 自动发布，
> 与 [Releases](https://github.com/cnlove2012/certbot_dns_dnspod/releases) 一一对应；
> `latest` 跟随最后一次成功构建。

或从源码本地构建（适合开发或自定义修改）：

```bash
git clone https://github.com/cnlove2012/certbot_dns_dnspod.git
cd certbot_dns_dnspod
docker build -t certbot-dns-dnspod:dev .
```

> 下文示例统一使用 Hub 镜像 `cnlove2012/certbot-dns-dnspod`；
> 若使用本地构建，请将其替换为 `certbot-dns-dnspod:dev`。

### 2. 申请证书

以下命令在含 `./certbot/letsencrypt/` 数据目录的位置执行（按上文"凭证获取"
操作后即位于仓库根目录）：该目录整体挂载为容器的 `/etc/letsencrypt`
（凭证、证书、账户信息都在其中），容器内通过
`/etc/letsencrypt/.secrets/credentials.ini` 引用凭证。

首次申请需提供邮箱（用于 Let's Encrypt 账号注册与到期提醒）并同意服务条款；
账号注册一次即可，后续续期不再需要这些参数。`-n` 为非交互模式
（容器环境无终端，交互式询问会导致失败）。

签发单域名证书：

```bash
docker run --rm \
  -v ./certbot/letsencrypt/:/etc/letsencrypt/ \
  cnlove2012/certbot-dns-dnspod \
  certonly \
  --dns-dnspod \
  --dns-dnspod-credentials /etc/letsencrypt/.secrets/credentials.ini \
  --email you@example.com \
  --agree-tos \
  -n \
  -d example.com
```

签发通配符证书（主域名与通配符合并为一张证书）：

```bash
docker run --rm \
  -v ./certbot/letsencrypt/:/etc/letsencrypt/ \
  cnlove2012/certbot-dns-dnspod \
  certonly \
  --dns-dnspod \
  --dns-dnspod-credentials /etc/letsencrypt/.secrets/credentials.ini \
  --email you@example.com \
  --agree-tos \
  -n \
  -d example.com \
  -d "*.example.com"
```

DNS 传播较慢时加大等待（默认 120 秒，跨国验证建议 600），在上述命令中加：
`--dns-dnspod-propagation-seconds 600`

签发成功后，证书位于宿主机 `./certbot/letsencrypt/live/<域名>/` 目录下。

### 3. 续期证书

certbot 会自动记录插件与凭证路径，续期只需 `renew`。建议先演练：

```bash
docker run --rm \
  -v ./certbot/letsencrypt/:/etc/letsencrypt/ \
  cnlove2012/certbot-dns-dnspod \
  renew --dry-run
```

配好 cron 定时续期（每天检查，到期前 30 天自动续，一年只需成功一次）：

```cron
17 3 * * * docker run --rm -v $HOME/certbot/letsencrypt/:/etc/letsencrypt/ cnlove2012/certbot-dns-dnspod renew --quiet
```

> - cron 中必须使用绝对路径（`$HOME/...`），`./` 相对路径在 cron 环境下无法解析；
>   请按实际仓库位置调整。
> - 镜像基于官方 `certbot/certbot`（版本固定于 [Dockerfile](Dockerfile) 的
>   `ARG CERTBOT_VERSION`）。
> - 排查续期问题时可加挂日志目录：`-v ./certbot/logs/:/var/log/letsencrypt/`。

## 附：pip 安装（可选）

`pip install certbot-dns-dnspod` 后可直接使用 `certbot`，参数与上述容器内完全一致：

```bash
certbot certonly \
  --dns-dnspod \
  --dns-dnspod-credentials ./certbot/letsencrypt/.secrets/credentials.ini \
  --email you@example.com \
  --agree-tos \
  -n \
  -d example.com
```

## 常见问题

- **"Unsafe permissions on credentials configuration file"**：
  凭证文件权限过宽，执行
  `chmod 600 ./certbot/letsencrypt/.secrets/credentials.ini`。
- **"Domain not exist."**：域名未添加到你的 DNSPod 账户，或使用的密钥属于
  其他子账号。先在 DNSPod 控制台确认域名在列。
- **验证超时**：增大 `--dns-dnspod-propagation-seconds`（默认 120，建议 600）。

## 开发

本项目为 AI 原生开发项目，开发规范与架构说明见 [CLAUDE.md](CLAUDE.md)。

开发环境为 **DevContainer**：VSCode 打开仓库后执行
*Reopen in Container* 即可（Python 3.12，依赖由 `postCreateCommand` 自动安装）。

```bash
python -m pytest          # 测试（纯 mock，无需真实凭证）
ruff check src/           # lint
mypy src/                 # 类型检查
```

## 许可证

[MIT License](LICENSE.txt)
