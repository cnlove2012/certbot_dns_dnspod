# 固定 certbot 基础镜像版本，保证构建可复现、避免 latest 意外引入不兼容大版本。
# 升级方法：修改下方 ARG 后重新构建，并在 CI 中验证。
ARG CERTBOT_VERSION=v5.8.0
FROM certbot/certbot:${CERTBOT_VERSION}

LABEL org.opencontainers.image.title="certbot-dns-dnspod" \
    org.opencontainers.image.description="DNSPod (Tencent Cloud) DNS Authenticator plugin for Certbot" \
    org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.source="https://github.com/cnlove2012/certbot_dns_dnspod"

COPY . /opt/certbot/src/plugin

RUN python tools/pip_install.py --no-cache-dir --editable /opt/certbot/src/plugin
