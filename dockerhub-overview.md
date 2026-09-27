<!-- 本文件为 Docker Hub Repository overview 的源文件，手动同步至
     hub.docker.com/r/cnlove2012/certbot-dns-dnspod（Settings → Description）。
     注意：本项目经 GitHub Actions 推送镜像（非 Docker Hub autobuild），
     overview 不会自动同步——修改本文件后需手动更新 Hub 页面。 -->

# certbot-dns-dnspod

[Certbot](https://certbot.eff.org/) 的 DNSPod（腾讯云）DNS 认证插件镜像。
通过腾讯云 DNSPod API 自动创建/删除 `_acme-challenge` TXT 记录，完成 ACME
`dns-01` 挑战——**支持通配符证书**（如 `*.example.com`）。

基于官方 [certbot/certbot](https://hub.docker.com/r/certbot/certbot) 镜像，
版本固定（见 [Dockerfile](https://github.com/cnlove2012/certbot_dns_dnspod/blob/main/Dockerfile)），
`dns-dnspod` 插件已内置，开箱即用。

## 背景：certbot 与 DNS-01 挑战

[Certbot](https://certbot.eff.org/) 是 EFF（电子前哨基金会）维护的开源工具，
用于从 [Let's Encrypt](https://letsencrypt.org/) 免费签发 HTTPS 证书并自动续期
（证书有效期 90 天，到期前 30 天可续）。

Let's Encrypt 通过"挑战"验证域名所有权。与需要公网可达 80 端口的 HTTP-01 相比，
**DNS-01** 只需在域名解析中临时创建一条指定 TXT 记录：

- 不需要服务器开放公网端口，内网/离线机器也能签证书
- 是签发**通配符证书**（`*.example.com`）的唯一途径

Certbot 官方镜像内置 Cloudflare、Route53 等国际 DNS 服务商插件，但不支持
DNSPod（腾讯云）。本镜像在官方 certbot 之上加入了 `dns-dnspod` 插件，
使 DNSPod 托管的域名也能全自动完成 DNS-01 挑战：申请时自动创建 TXT 记录，
验证通过后自动删除。

## Tags

- `latest` — 跟随 main 分支最后一次成功构建
- `年.周.build`（CalVer，如 `2026.39.1`）— 代码或配置变更合并后自动发布
  （纯文档改动不发版），与
  [GitHub Releases](https://github.com/cnlove2012/certbot_dns_dnspod/releases)
  一一对应。生产环境建议固定版本号。

## 快速开始

### 1. 准备腾讯云凭证

在 [腾讯云控制台 → CAM → API 密钥管理](https://console.cloud.tencent.com/cam/capi)
创建 `SecretId` / `SecretKey`（建议使用子账号，只授予 `QcloudDNSPodFullAccess`）。

创建凭证文件（**注意键名带 `dns_dnspod_` 前缀**）：

```ini
dns_dnspod_secret_id = 你的SecretId
dns_dnspod_secret_key = 你的SecretKey
```

保存为 `./certbot/letsencrypt/.secrets/credentials.ini` 并收紧权限
（certbot 检测到权限过宽会持续警告）：

```bash
mkdir -p ./certbot/letsencrypt/.secrets
chmod 600 ./certbot/letsencrypt/.secrets/credentials.ini
```

> ⚠️ 请像保管密码一样保管凭证文件。能读取它的任何人都可以操作你的 DNSPod 解析记录。

### 2. 申请证书

首次申请需提供邮箱（用于 Let's Encrypt 账号注册与到期提醒）并同意服务条款；
账号注册一次即可，后续续期不再需要这些参数。

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

说明：

- `-n`（非交互模式）：容器环境无终端，交互式询问会导致失败
- DNS 传播较慢时加大等待（默认 120 秒，跨国验证建议 600）：
  `--dns-dnspod-propagation-seconds 600`
- 签发成功后，证书位于宿主机 `./certbot/letsencrypt/live/<域名>/` 目录下

### 3. 续期

```bash
docker run --rm \
  -v ./certbot/letsencrypt/:/etc/letsencrypt/ \
  cnlove2012/certbot-dns-dnspod \
  renew --dry-run
```

配好 cron 定时续期（到期前 30 天自动续，cron 中必须用绝对路径）：

```cron
17 3 * * * docker run --rm -v $HOME/certbot/letsencrypt/:/etc/letsencrypt/ cnlove2012/certbot-dns-dnspod renew --quiet
```

## 常见问题

- **"Unsafe permissions on credentials configuration file"** — 凭证文件权限过宽，
  执行 `chmod 600`。
- **"Domain not exist."** — 域名未添加到你的 DNSPod 账户，或密钥属于其他子账号。
- **验证超时** — 增大 `--dns-dnspod-propagation-seconds`（默认 120，建议 600）。

## 源码与反馈

<https://github.com/cnlove2012/certbot_dns_dnspod> · MIT License
