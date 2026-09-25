"""Tests for certbot_dns_dnspod.dns_dnspod."""

import unittest
from unittest import mock

from certbot.compat import os
from certbot.errors import PluginError
from certbot.plugins import dns_test_common
from certbot.plugins.dns_test_common import DOMAIN
from certbot.tests import util as test_util

from certbot_dns_dnspod._internal.dns_dnspod import Authenticator
from certbot_dns_dnspod._internal.dns_dnspod import _DNSPodClient

FAKE_SECRET_ID = "FAKE_SECRET_ID"
FAKE_SECRET_KEY = "FAKE_SECRET_KEY"

FAKE_ZONE = "example.cn"
FAKE_DOMAIN_ID = 12345
FAKE_RECORD_ID = 987654
FAKE_VALIDATION = "yLp+rH5xJ6vB3x4wC3dcx1oGtsPT7sU2sQI0U.txt"


class AuthenticatorTest(test_util.TempDirTestCase, dns_test_common.BaseAuthenticatorTest):
    def setUp(self):
        super().setUp()

        path = os.path.join(self.tempdir, "file.ini")
        dns_test_common.write(
            {
                # CredentialsConfiguration 以插件名（dns-dnspod）为键前缀读取 ini
                "dns_dnspod_secret_id": FAKE_SECRET_ID,
                "dns_dnspod_secret_key": FAKE_SECRET_KEY,
            },
            path,
        )

        self.config = mock.MagicMock(
            dns_dnspod_credentials=path,
            dns_dnspod_propagation_seconds=0,  # don't wait during tests
        )

        self.auth = Authenticator(self.config, "dns-dnspod")

        self.mock_client = mock.MagicMock()

        # pylint: disable=protected-access
        self.auth._get_dnspod_client = mock.MagicMock(  # type: ignore[method-assign]
            return_value=self.mock_client
        )

        # perform() 末尾会调用 display_util.notify（传播等待提示），
        # 测试环境未初始化 display，这里将其 patch 掉
        notify_patcher = mock.patch("certbot.display.util.notify")
        notify_patcher.start()
        self.addCleanup(notify_patcher.stop)

    def test_perform(self):
        self.auth.perform([self.achall])

        expected = [
            mock.call.add_txt_record(DOMAIN, "_acme-challenge." + DOMAIN, mock.ANY, mock.ANY)
        ]
        self.assertEqual(expected, self.mock_client.mock_calls)

    def test_cleanup(self):
        # _attempt_cleanup | pylint: disable=protected-access
        self.auth._attempt_cleanup = True
        self.auth.cleanup([self.achall])

        expected = [mock.call.del_txt_record(DOMAIN, "_acme-challenge." + DOMAIN, mock.ANY)]
        self.assertEqual(expected, self.mock_client.mock_calls)


class _DNSPodClientTest(unittest.TestCase):
    """_DNSPodClient 单元测试（全部 mock，无网络请求）。"""

    def _make_client(self, domain_list=None):
        """构造不联网的 client：跳过构造期的 DescribeDomainList 拉取。"""
        with mock.patch.object(_DNSPodClient, "_get_domain_list") as mock_list:
            mock_list.return_value = (
                domain_list if domain_list is not None else {FAKE_ZONE: FAKE_DOMAIN_ID}
            )
            client = _DNSPodClient(FAKE_SECRET_ID, FAKE_SECRET_KEY)
        client._get_client = mock.MagicMock()  # type: ignore[method-assign]  # pylint: disable=protected-access
        return client

    @staticmethod
    def _record(record_id, value, name="_acme-challenge", record_type="TXT"):
        return mock.MagicMock(RecordId=record_id, Value=value, Name=name, Type=record_type)

    # _find_domain_id -------------------------------------------------------

    def test_find_domain_id_exact(self):
        client = self._make_client()
        # pylint: disable=protected-access
        self.assertEqual(client._find_domain_id(FAKE_ZONE), (FAKE_DOMAIN_ID, FAKE_ZONE))

    def test_find_domain_id_subdomain(self):
        client = self._make_client()
        # pylint: disable=protected-access
        self.assertEqual(client._find_domain_id("sub." + FAKE_ZONE), (FAKE_DOMAIN_ID, FAKE_ZONE))

    def test_find_domain_id_boundary(self):
        """回归：点边界检查——devexample.cn 不得误命中 example.cn。"""
        client = self._make_client()
        # pylint: disable=protected-access
        self.assertEqual(client._find_domain_id("dev" + FAKE_ZONE), (None, ""))

    def test_find_domain_id_longest_zone(self):
        """账户同时持有父子两区时，取最长（最精确）的区。"""
        client = self._make_client({FAKE_ZONE: 1, "dev." + FAKE_ZONE: 2})
        # pylint: disable=protected-access
        self.assertEqual(client._find_domain_id("dev." + FAKE_ZONE), (2, "dev." + FAKE_ZONE))

    def test_find_domain_id_unknown(self):
        client = self._make_client()
        # pylint: disable=protected-access
        self.assertEqual(client._find_domain_id("other.example.org"), (None, ""))

    # add_txt_record --------------------------------------------------------

    def test_add_txt_record(self):
        client = self._make_client()
        client.add_txt_record(FAKE_ZONE, "_acme-challenge." + FAKE_ZONE, FAKE_VALIDATION, 600)

        sdk_client = client._get_client.return_value
        self.assertEqual(sdk_client.CreateTXTRecord.call_count, 1)
        req = sdk_client.CreateTXTRecord.call_args[0][0]
        self.assertEqual(req.Domain, FAKE_ZONE)
        self.assertEqual(req.DomainId, FAKE_DOMAIN_ID)
        self.assertEqual(req.SubDomain, "_acme-challenge")
        self.assertEqual(req.Value, FAKE_VALIDATION)
        self.assertEqual(req.RecordLine, "默认")
        self.assertEqual(req.TTL, 600)

    def test_add_txt_record_unknown_domain(self):
        client = self._make_client()
        with self.assertRaises(PluginError):
            client.add_txt_record(
                "other.example.org", "_acme-challenge.other.example.org", FAKE_VALIDATION, 600
            )
        sdk_client = client._get_client.return_value
        sdk_client.CreateTXTRecord.assert_not_called()

    # del_txt_record --------------------------------------------------------

    def test_del_txt_record(self):
        client = self._make_client()
        sdk_client = client._get_client.return_value
        sdk_client.DescribeRecordList.return_value.RecordList = [
            self._record(FAKE_RECORD_ID, FAKE_VALIDATION),
        ]

        client.del_txt_record(FAKE_ZONE, "_acme-challenge." + FAKE_ZONE, FAKE_VALIDATION)

        list_req = sdk_client.DescribeRecordList.call_args[0][0]
        self.assertEqual(list_req.SubDomain, "_acme-challenge")
        self.assertEqual(list_req.RecordType, "TXT")
        self.assertEqual(list_req.ErrorOnEmpty, "no")

        sdk_client.DeleteRecord.assert_called_once()
        del_req = sdk_client.DeleteRecord.call_args[0][0]
        self.assertEqual(del_req.Domain, FAKE_ZONE)
        self.assertEqual(del_req.DomainId, FAKE_DOMAIN_ID)
        self.assertEqual(del_req.RecordId, FAKE_RECORD_ID)

    def test_del_txt_record_value_mismatch(self):
        """同名但值不同的记录（如其他证书的验证记录）不得被删除。"""
        client = self._make_client()
        sdk_client = client._get_client.return_value
        sdk_client.DescribeRecordList.return_value.RecordList = [
            self._record(FAKE_RECORD_ID, "other-value"),
        ]

        client.del_txt_record(FAKE_ZONE, "_acme-challenge." + FAKE_ZONE, FAKE_VALIDATION)

        sdk_client.DeleteRecord.assert_not_called()

    def test_del_txt_record_empty(self):
        """无记录：零删除调用且不抛错。"""
        client = self._make_client()
        sdk_client = client._get_client.return_value
        sdk_client.DescribeRecordList.return_value.RecordList = []

        client.del_txt_record(FAKE_ZONE, "_acme-challenge." + FAKE_ZONE, FAKE_VALIDATION)

        sdk_client.DeleteRecord.assert_not_called()

    def test_del_txt_record_pagination(self):
        """首页满页时继续翻页，第二页的匹配记录同样被删除。"""
        client = self._make_client()
        client._record_list_page_limit = 2
        sdk_client = client._get_client.return_value
        page1 = [self._record(i, f"stale-{i}") for i in range(2)]
        page2 = [self._record(FAKE_RECORD_ID, FAKE_VALIDATION)]
        sdk_client.DescribeRecordList.side_effect = [
            mock.MagicMock(RecordList=page1),
            mock.MagicMock(RecordList=page2),
        ]

        client.del_txt_record(FAKE_ZONE, "_acme-challenge." + FAKE_ZONE, FAKE_VALIDATION)

        self.assertEqual(sdk_client.DescribeRecordList.call_count, 2)
        offsets = [c[0][0].Offset for c in sdk_client.DescribeRecordList.call_args_list]
        self.assertEqual(offsets, [0, 2])
        sdk_client.DeleteRecord.assert_called_once()
        self.assertEqual(sdk_client.DeleteRecord.call_args[0][0].RecordId, FAKE_RECORD_ID)

    def test_del_txt_record_domain_not_found(self):
        """cleanup 尽力而为：域名不在账户中时静默跳过，不调用任何 API。"""
        client = self._make_client()
        client.del_txt_record(
            "other.example.org", "_acme-challenge.other.example.org", FAKE_VALIDATION
        )
        sdk_client = client._get_client.return_value
        sdk_client.DescribeRecordList.assert_not_called()

    # SDK 异常转译 -----------------------------------------------------------

    def test_del_txt_record_sdk_error(self):
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
            TencentCloudSDKException,
        )

        client = self._make_client()
        sdk_client = client._get_client.return_value
        sdk_client.DescribeRecordList.side_effect = TencentCloudSDKException(
            "InternalError", "boom"
        )

        with self.assertRaises(PluginError):
            client.del_txt_record(FAKE_ZONE, "_acme-challenge." + FAKE_ZONE, FAKE_VALIDATION)

    def test_add_txt_record_sdk_error(self):
        from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
            TencentCloudSDKException,
        )

        client = self._make_client()
        sdk_client = client._get_client.return_value
        sdk_client.CreateTXTRecord.side_effect = TencentCloudSDKException("InternalError", "boom")

        with self.assertRaises(PluginError):
            client.add_txt_record(FAKE_ZONE, "_acme-challenge." + FAKE_ZONE, FAKE_VALIDATION, 600)


if __name__ == "__main__":
    unittest.main()  # pragma: no cover
