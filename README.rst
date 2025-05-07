certbot-dns-dnspod
=====================

DNSPod_ DNS Authenticator plugin for Certbot

This plugin automates the process of completing a ``dns-01`` challenge by
creating, and subsequently removing, TXT records using the DNSPod Remote API.

Configuration of DNSPod
---------------------------

In the `System -> Remote Users` you have to have a user, with the following rights

- Client Functions
- DNS zone functions
- DNS txt functions


.. _DNSPod: https://www.dnspod.cn/
.. _certbot: https://certbot.eff.org/

Installation
------------

::

    pip install certbot-dns-dnspod


Named Arguments
---------------

To start using DNS authentication for dnspod, pass the following arguments on
certbot's command line:

============================================================= ==============================================
``--authenticator dns-dnspod``          select the authenticator plugin (Required)

``--dns-dnspod-credentials``         DNSPod Remote User credentials
                                                              INI file. (Required)

``--dns-dnspod-propagation-seconds`` | waiting time for DNS to propagate before asking
                                                              | the ACME server to verify the DNS record.
                                                              | (Default: 120, Recommended: >= 600)
============================================================= ==============================================

Credentials
-----------

An example ``credentials.ini`` file:

.. code-block:: ini

   dns_dnspod_secret_id = secretId
   dns_dnspod_secret_key = secretKey

The path to this file can be provided interactively or using the
``--dns-dnspod-credentials`` command-line argument. Certbot
records the path to this file for use during renewal, but does not store the
file's contents.

**CAUTION:** You should protect these API credentials as you would the
password to your dnspod account. Users who can read this file can use these
credentials to issue arbitrary API calls on your behalf. Users who can cause
Certbot to run using these credentials can complete a ``dns-01`` challenge to
acquire new certificates or revoke existing certificates for associated
domains, even if those domains aren't being managed by this server.

Certbot will emit a warning if it detects that the credentials file can be
accessed by other users on your system. The warning reads "Unsafe permissions
on credentials configuration file", followed by the path to the credentials
file. This warning will be emitted each time Certbot uses the credentials file,
including for renewal, and cannot be silenced except by addressing the issue
(e.g., by using a command like ``chmod 600`` to restrict access to the file).


Examples
--------

To acquire a single certificate for both ``example.com`` and
``*.example.com``, waiting 900 seconds for DNS propagation:

.. code-block:: bash

   certbot certonly \
     --authenticator dns-dnspod \
     --dns-dnspod-credentials /etc/letsencrypt/.secrets/domain.tld.ini \
     --dns-dnspod-propagation-seconds 90 \
     --agree-tos \
     --expand \
     --non-interactive
     --rsa-key-size 4096 \
     -d 'example.com' \
     -d '*.example.com'

Docker
------

In order to create a docker container with a certbot-dns-ispconfig installation,
create an empty directory with the following ``Dockerfile``:

.. code-block:: docker

    FROM certbot/certbot
    COPY . /opt/certbot/src/plugin
    RUN python tools/pip_install.py --no-cache-dir --editable /opt/certbot/src/plugin

Proceed to build the image::

    docker build -t cnlove2012/certbot-dns-dnspod:latest -f Dockerfile .

Once that's finished, the application can be run as follows::

    docker run --rm \
       -v /var/lib/letsencrypt:/var/lib/letsencrypt \
       -v /var/log/letsencrypt:/var/log/letsencrypt \
       -v /etc/letsencrypt:/etc/letsencrypt \
       --cap-drop=all \
       cnlove2012/certbot-dns-dnspod:latest certonly \
       --non-interactive \
	   --agree-tos \
       --authenticator dns-dnspod \
       --dns-dnspod-propagation-seconds 90 \
       --dns-dnspod-credentials /etc/letsencrypt/.secrets/credentials.ini \
       --no-self-upgrade \
       --keep-until-expiring --expand \
       --server https://acme-v02.api.letsencrypt.org/directory \
       -d example.com -d '*.example.com'

It is suggested to secure the folder as follows::
chown root:root /etc/letsencrypt/.secrets
chmod 600 /etc/letsencrypt/.secrets

Renew::

    docker run --rm \
	    -v ./letsencrypt/lib:/var/lib/letsencrypt \
	    -v ./letsencrypt/log:/var/log/letsencrypt \
	    -v ./letsencrypt/conf.d:/etc/letsencrypt \
	    cnlove2012/certbot-dns-dnspod:latest renew \
	    --force-renewal

