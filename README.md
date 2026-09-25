# certbot-dns-dnspod

[![CI](https://github.com/cnlove2012/certbot_dns_dnspod/actions/workflows/ci.yml/badge.svg)](https://github.com/cnlove2012/certbot_dns_dnspod/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.9%2B-blue)
![License](https://img.shields.io/badge/license-Apache--2.0-green)

[Certbot](https://certbot.eff.org/) 的 DNSPod（腾讯云）DNS 认证插件。
通过腾讯云 DNSPod API 自动创建与删除 `_acme-challenge` TXT 记录，完成 ACME
`dns-01` 挑战——**支持通配符证书**（如 `*.example.com`）。

## 凭证获取

1. 登录 [腾讯云控制台](https://console.cloud.tencent.com/)，进入
   **访问管理 CAM → API 密钥管理**，创建 `SecretId` 与 `SecretKey`。
2. 建议使用子账号密钥，并只授予 `QcloudDNSPodFullAccess` 策略（最小权限）。
3. 创建凭证文件（路径任意，下文以 `~/dnspod.ini` 为例）：

   ```ini
   dns_dnspod_secret_id = 你的SecretId
   dns_dnspod_secret_key = 你的SecretKey
   ```

4. 收紧权限（Certbot 检测到权限过宽会持续警告）：

   ```bash
   chmod 600 ~/dnspod.ini
   ```

> ⚠️ 请像保管密码一样保管该文件。能读取它的任何人都可以操作你的 DNSPod 解析记录。

## 安装

```bash
pip install certbot-dns-dnspod
```

或从源码安装：

```bash
git clone https://github.com/cnlove2012/certbot_dns_dnspod.git
cd certbot_dns_dnspod
pip install .
```

## 使用

签发单域名证书：

```bash
certbot certonly \
  --dns-dnspod \
  --dns-dnspod-credentials ~/dnspod.ini \
  -d example.com
```

签发通配符证书：

```bash
certbot certonly \
  --dns-dnspod \
  --dns-dnspod-credentials ~/dnspod.ini \
  -d example.com \
  -d "*.example.com"
```

等待 DNS 传播（国内解析生效通常较快，跨国验证建议加大）：

```bash
certbot certonly \
  --dns-dnspod \
  --dns-dnspod-credentials ~/dnspod.ini \
  --dns-dnspod-propagation-seconds 600 \
  -d example.com
```

续期（certbot 会自动记录插件与凭证路径，配好 cron/systemd 定时执行即可）：

```bash
certbot renew --dry-run   # 先演练
certbot renew             # 实际续期
```

## Docker 使用

```bash
docker build -t certbot-dns-dnspod .
```

单条命令签发（挂载凭证文件与 certbot 工作目录）：

```bash
docker run --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  -v ~/dnspod.ini:/dnspod.ini:ro \
  certbot-dns-dnspod \
  certonly \
  --dns-dnspod \
  --dns-dnspod-credentials /dnspod.ini \
  -d example.com
```

续期：

```bash
docker run --rm \
  -v /etc/letsencrypt:/etc/letsencrypt \
  -v /var/lib/letsencrypt:/var/lib/letsencrypt \
  -v ~/dnspod.ini:/dnspod.ini:ro \
  certbot-dns-dnspod \
  renew
```

> 镜像基于官方 `certbot/certbot`（版本固定于 [Dockerfile](Dockerfile) 的
> `ARG CERTBOT_VERSION`）。`/etc/letsencrypt` 与 `/var/lib/letsencrypt` 分别
> 保存证书/账户信息与续期状态，请持久化挂载。

## 常见问题

- **"Unsafe permissions on credentials configuration file"**：
  凭证文件权限过宽，执行 `chmod 600 ~/dnspod.ini`。
- **"Domain not exist."**：域名未添加到你的 DNSPod 账户，或使用的密钥属于
  其他子账号。先在 DNSPod 控制台确认域名在列。
- **验证超时**：增大 `--dns-dnspod-propagation-seconds`（默认 120，建议 600）。

## 开发

本项目为 AI 原生开发项目，开发规范与架构说明见 [CLAUDE.md](CLAUDE.md)。

```bash
python3.12 -m venv .venv && . .venv/bin/activate
pip install -e ".[test]" ruff mypy pre-commit

python -m pytest          # 测试（纯 mock，无需真实凭证）
ruff check src/           # lint
mypy src/                 # 类型检查
```

## 许可证

[Apache License 2.0](LICENSE.txt)
