FROM certbot/certbot:latest

LABEL authors="Mr.Jackin"

COPY . /opt/certbot/src/plugin

RUN python tools/pip_install.py --no-cache-dir --editable /opt/certbot/src/plugin
