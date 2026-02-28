"""BillNormalizer 单元测试"""

import pytest
import pandas as pd
from datetime import date
from unibillcal.core.normalizer import BillNormalizer
from unibillcal.core.config_loader import PlatformConfig
from tests.conftest import make_alipay_config


def make_config(extra=None):
    return PlatformConfig.from_dict(make_alipay_config(extra))


class TestBillNormalizer:
    def test_output_has_unified_schema(self, alipay_raw_df):
        """标准化输出必须包含核心统一字段"""
        unified = BillNormalizer(make_config()).normalize(source_df=alipay_raw_df)
        for field in ("business_date", "store_name", "amount",
                      "raw_amount", "platform", "source_type", "source_id"):
            assert field in unified.columns

    def test_row_count_unchanged_without_filter(self, alipay_raw_df):
        """无过滤器时，标准化不改变行数"""
        unified = BillNormalizer(make_config()).normalize(source_df=alipay_raw_df)
        assert len(unified) == len(alipay_raw_df)

    def test_filter_reduces_rows(self, alipay_raw_df):
        """过滤器应在标准化前减少行数"""
        config = make_config(extra={
            "filter": {"column": "商家名称", "op": "eq", "value": "旗舰店A"}
        })
        unified = BillNormalizer(config).normalize(source_df=alipay_raw_df)
        assert len(unified) < len(alipay_raw_df)
        assert (unified["store_name"] == "旗舰店A").all()

    def test_business_date_is_date_type(self, alipay_raw_df):
        """business_date 应为 date 类型"""
        unified = BillNormalizer(make_config()).normalize(source_df=alipay_raw_df)
        assert unified["business_date"].iloc[0] == date(2024, 1, 5)

    def test_amount_formula_correct(self, alipay_raw_df):
        """金额公式应正确计算：支付=150, 退款=20 -> 130"""
        unified = BillNormalizer(make_config()).normalize(source_df=alipay_raw_df)
        assert unified["raw_amount"].iloc[3] == pytest.approx(130.0)

    def test_platform_label_injected(self, alipay_raw_df):
        """platform 应自动注入"""
        unified = BillNormalizer(make_config()).normalize(source_df=alipay_raw_df)
        assert (unified["platform"] == "alipay").all()

    def test_source_type_injected(self, alipay_raw_df):
        """source_type 应自动注入"""
        unified = BillNormalizer(make_config()).normalize(source_df=alipay_raw_df)
        assert (unified["source_type"] == "excel").all()

    def test_source_id_traceable(self, alipay_raw_df):
        """每行 source_id 应唯一且可追溯"""
        unified = BillNormalizer(make_config()).normalize(source_df=alipay_raw_df)
        assert unified["source_id"].nunique() == len(unified)

    def test_step_by_step_matches_normalize(self, alipay_raw_df):
        """分步调用结果应与 normalize() 一致"""
        config = make_config()
        normalizer = BillNormalizer(config)
        step_result = normalizer.map(normalizer.filter(alipay_raw_df))
        full_result = normalizer.normalize(source_df=alipay_raw_df)
        assert list(step_result.columns) == list(full_result.columns)
        assert len(step_result) == len(full_result)

    def test_wechat_normalize(self, wechat_raw_df):
        """微信平台标准化：store_name / amount / source_type"""
        config = PlatformConfig.from_dict({
            "platform": "wechat",
            "source": {"type": "sqlserver", "connection_string": "dummy"},
            "field_mapping": {
                "business_date": "交易时间",
                "store_name":    "商品名称",
                "order_no":      "微信单号",
            },
            "amount_formula": "金额(元) - 退款金额(元)",
        })
        unified = BillNormalizer(config).normalize(source_df=wechat_raw_df)
        assert (unified["source_type"] == "sqlserver").all()
        store_y = unified[unified["store_name"] == "店铺Y商品"]
        assert store_y["raw_amount"].iloc[0] == pytest.approx(270.0)
