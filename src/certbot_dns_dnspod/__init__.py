"""
`~certbot_dns_dnspod.dns_dnspod` 插件通过腾讯云 DNSPod API 创建并随后删除
TXT 记录，自动完成 ``dns-01`` 挑战（`~acme.challenges.DNS01`）。


命名参数
--------

``--dns-dnspod-credentials``
   DNSPod API 凭证_ INI 文件。（必填）

``--dns-dnspod-propagation-seconds``
   等待 DNS 传播的秒数，之后才请求 ACME 服务器验证 DNS 记录。
   （默认：120，建议：>= 600）


凭证
----

使用本插件需要一个包含腾讯云 API 密钥的配置文件。密钥在
【腾讯云控制台 → 访问管理 CAM → API 密钥管理】创建，
建议使用仅授予 ``QcloudDNSPodFullAccess`` 策略的子账号密钥。

.. code-block:: ini
   :name: credentials.ini
   :caption: 凭证文件示例：

   # certbot 使用的 DNSPod API 凭证
   dns_dnspod_secret_id = SECRET_ID
   dns_dnspod_secret_key = SECRET_KEY

该文件的路径可通过交互方式或 ``--dns-dnspod-credentials`` 命令行参数提供。
Certbot 会记录该路径用于续期，但不会保存文件内容。

.. caution::
   请像保护密码一样保护这些 API 凭证。能读取该文件的用户可以代表你发起
   任意 API 调用；能让 Certbot 使用这些凭证运行的用户可以完成 ``dns-01``
   挑战以获取新证书或吊销相关域名的现有证书——即使这些域名并非由本服务器管理。

若 Certbot 检测到凭证文件可被系统其他用户访问，将发出警告
"Unsafe permissions on credentials configuration file" 并附上文件路径。
每次使用凭证文件（包括续期）都会发出该警告，只能通过修复权限消除
（例如执行 ``chmod 600`` 限制访问）。


示例
--------

.. code-block:: bash
   :caption: 为 ``example.com`` 签发证书

   certbot certonly \\
     --dns-dnspod \\
     --dns-dnspod-credentials ~/.secrets/certbot/dnspod.ini \\
     -d example.com

.. code-block:: bash
   :caption: 为 ``example.com`` 与 ``www.example.com`` 签发同一张证书

   certbot certonly \\
     --dns-dnspod \\
     --dns-dnspod-credentials ~/.secrets/certbot/dnspod.ini \\
     -d example.com \\
     -d www.example.com

.. code-block:: bash
   :caption: 为 ``example.com`` 签发证书，等待 600 秒 DNS 传播

   certbot certonly \\
     --dns-dnspod \\
     --dns-dnspod-credentials ~/.secrets/certbot/dnspod.ini \\
     --dns-dnspod-propagation-seconds 600 \\
     -d example.com

"""
