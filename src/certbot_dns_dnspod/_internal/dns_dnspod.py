"""DNS Authenticator for DNSPod."""

import logging
from typing import Callable

from certbot import errors
from certbot.plugins import dns_common
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import TencentCloudSDKException
from tencentcloud.common.profile import client_profile
from tencentcloud.common.profile import http_profile
from tencentcloud.dnspod.v20210323 import dnspod_client
from tencentcloud.dnspod.v20210323 import models

logger = logging.getLogger(__name__)


class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for DNSPod

    This Authenticator uses the DNSPod Remote REST API to fulfill a dns-01 challenge.
    """

    description = "Obtain certificates using a DNS TXT record (if you are using DNSPod for DNS)."
    ttl = 600

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(
        cls,
        add: Callable[..., None],  # pylint: disable=arguments-differ
        default_propagation_seconds: int = 10,
    ) -> None:
        super().add_parser_arguments(add, default_propagation_seconds=120)
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
        self._get_dnspod_client().add_txt_record(domain, validation_name, validation, self.ttl)

    def _cleanup(self, domain, validation_name, validation):
        self._get_dnspod_client().del_txt_record(domain, validation_name, validation)

    def _get_dnspod_client(self):
        # certbot 生命周期保证 perform() 先经 _setup_credentials() 完成赋值
        assert self.credentials is not None
        return _DNSPodClient(
            self.credentials.conf("secret_id"),
            self.credentials.conf("secret_key"),
        )


class _DNSPodClient:
    """
    Encapsulates all communication with the DNSPod Remote REST API.
    """

    # DescribeRecordList 的 Limit 上限（API 文档：当前最大支持 3000）
    _record_list_page_limit = 3000

    def __init__(self, secret_id, secret_key):
        logger.debug("creating DNSPodClient")
        self.credential = credential.Credential(secret_id, secret_key)
        self.domain_list = self._get_domain_list()

    def _get_client(self):
        return dnspod_client.DnspodClient(
            self.credential,
            "",
            client_profile.ClientProfile(httpProfile=http_profile.HttpProfile()),
        )

    def _get_domain_list(self):
        domain_list = {}
        try:
            client = self._get_client()
            resp = client.DescribeDomainList(models.DescribeDomainListRequest())
            for domain in resp.DomainList:
                domain_list[domain.Name] = domain.DomainId
            return domain_list
        except TencentCloudSDKException as err:
            logger.debug("get DomainList error: %s", err.get_message())
            raise errors.PluginError(err.get_message()) from err

    def _find_domain_id(self, sub: str):
        # 精确或点边界匹配（避免 devexample.cn 误命中 example.cn），多区命中时取最长区
        best_id = None
        best_zone = ""
        for zone, domain_id in self.domain_list.items():
            if (sub == zone or sub.endswith("." + zone)) and len(zone) > len(best_zone):
                best_id = domain_id
                best_zone = zone
        return best_id, best_zone

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
            raise errors.PluginError(err.get_message()) from err

    def del_txt_record(self, domain, record_name, record_content):
        """
        Delete a TXT record using the supplied information.

        Same-name records with matching content (e.g. leftovers from retried
        challenges) are all deleted. Cleanup is best-effort: if the domain is
        unknown to the DNSPod account, the deletion is silently skipped.

        :param str domain: The domain to use to look up the managed zone.
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content (typically the challenge validation).
        :raises certbot.errors.PluginError: if an error occurs communicating with the DNSPod API
        """
        logger.debug(
            "deleting TXT domain: %s; record name: %s; record content: %s.",
            domain,
            record_name,
            record_content,
        )

        domain_id, zone = self._find_domain_id(domain)
        if domain_id is None:
            logger.debug("domain %s not found in DNSPod account; skipping cleanup", domain)
            return

        subdomain = record_name.removesuffix(f".{zone}")
        client = self._get_client()
        offset = 0
        limit = self._record_list_page_limit
        try:
            while True:
                req = models.DescribeRecordListRequest()
                req.Domain = zone
                req.DomainId = domain_id
                req.SubDomain = subdomain
                req.RecordType = "TXT"
                req.Offset = offset
                req.Limit = limit
                # 默认值 "yes" 会在无记录时抛 ResourceNotFound.NoData，显式关闭
                req.ErrorOnEmpty = "no"
                resp = client.DescribeRecordList(req)
                records = resp.RecordList or []
                for record in records:
                    if record.Value != record_content:
                        continue
                    del_req = models.DeleteRecordRequest()
                    del_req.Domain = zone
                    del_req.DomainId = domain_id
                    del_req.RecordId = record.RecordId
                    client.DeleteRecord(del_req)
                    logger.debug("deleted TXT record id=%s (%s)", record.RecordId, record_name)
                if len(records) < limit:
                    break
                offset += limit
        except TencentCloudSDKException as err:
            logger.debug("delete TXT error: %s", err.get_message())
            raise errors.PluginError(err.get_message()) from err
