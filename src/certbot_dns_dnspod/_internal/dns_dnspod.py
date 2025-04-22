"""DNS Authenticator for DNSPod."""
import logging

from typing import Callable
from certbot import errors
from certbot.plugins import dns_common

from tencentcloud.common import credential
from tencentcloud.common.profile import client_profile
from tencentcloud.common.profile import http_profile
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.dnspod.v20210323 import dnspod_client, models

logger = logging.getLogger(__name__)


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for DNSPod

    This Authenticator uses the DNSPod Remote REST API to fulfill a dns-01 challenge.
    """

    description = "Obtain certificates using a DNS TXT record (if you are using DNSPod for DNS)."
    ttl = 600

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add: Callable[..., None],  # pylint: disable=arguments-differ
                             default_propagation_seconds: int = 10) -> None:
        super(Authenticator, cls).add_parser_arguments(
            add, default_propagation_seconds=120)
        add("credentials", help="DNSPod credentials INI file.")

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return (
            "This plugin configures a DNS TXT record to respond to a dns-01 challenge using "
            + "the DNSPod Remote REST API."
        )

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            "credentials",
            "DNSPod credentials INI file",
            {
                "secret_id": "SecretId for DNSPod Remote API.",
                "secret_key": "SecretKey for DNSPod Remote API.",
            },
        )

    def _perform(self, domain, validation_name, validation):
        self._get_dnspod_client().add_txt_record(
            domain, validation_name, validation, self.ttl
        )

    def _cleanup(self, domain, validation_name, validation):
        self._get_dnspod_client().del_txt_record(domain, validation_name, validation)

    def _get_dnspod_client(self):
        return _DNSPodClient(
            self.credentials.conf("secret_id"),
            self.credentials.conf("secret_key"),
        )


class _DNSPodClient(object):
    """
    Encapsulates all communication with the DNSPod Remote REST API.
    """

    def __init__(self, secret_id, secret_key):
        logger.debug("creating DNSPodClient")
        self.credential = credential.Credential(secret_id, secret_key)
        self.domain_list = self._get_domain_list()

    def _get_client(self):
        return dnspod_client.DnspodClient(
            self.credential,
            "",
            client_profile.ClientProfile(
                httpProfile=http_profile.HttpProfile()
            )
        )

    def _get_domain_list(self):
        domain_list = {}
        try:
            client = self._get_client()
            resp = client.DescribeDomainList(
                models.DescribeDomainListRequest()
            )
            for domain in resp.DomainList:
                domain_list[domain.Name] = domain.DomainId
            return domain_list
        except TencentCloudSDKException as err:
            logger.debug("get DomainList error: %s", err.get_message())
            raise errors.PluginError(err.get_message())

    def _find_domain_id(self, sub: str):
        for domain, domain_id in self.domain_list.copy().items():
            if sub.endswith(domain):
                return domain_id, domain
        return None, ""

    def add_txt_record(self, domain, validation_name, validation, ttl):
        """
        Add a TXT record using the supplied information.

        :param str domain: 域名.
        :param str validation_name: 主机记录.
        :param str validation: The record content (typically the challenge validation).
        :param int ttl: The record TTL (number of seconds that the record may be cached).
        :raises certbot.errors.PluginError: if an error occurs communicating with the DNSPod API
        """

        domain_id, name = self._find_domain_id(domain)
        if domain_id is None:
            raise errors.PluginError("Domain not exist.")

        try:
            client = self._get_client()

            # 实例化一个请求对象
            req = models.CreateTXTRecordRequest()
            req.Domain = name
            req.DomainId = domain_id
            req.Value = validation
            req.RecordLine = "默认"
            req.TTL = ttl
            req.SubDomain = validation_name.removesuffix(f".{name}")
            req.Remark = "certbot_dns_dnspod certificate validation"

            # 通过client对象调用想要访问的接口，需要传入请求对象
            resp = client.CreateTXTRecord(req)
            logger.debug("created TXT response: %s", resp.to_json_string())
        except TencentCloudSDKException as err:
            logger.debug("created TXT error: %s", err.get_message())
            raise errors.PluginError(err.get_message())

    def del_txt_record(self, domain, record_name, record_content):
        """
        Delete a TXT record using the supplied information.

        :param str domain: The domain to use to look up the managed zone.
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content (typically the challenge validation).
        :raises certbot.errors.PluginError: if an error occurs communicating with the DNSPod API
        """
        logger.debug(
            "deleting TXT domain: %s; record name: %s; record content: %s.",
            domain,
            record_name,
            record_content
        )
