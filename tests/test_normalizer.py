"""BillNormalizer 单元测试"""

import pytest
import pandas as pd
from datetime import date
from unibillcal.core.normalizer import BillNormalizer
from unibillcal.core.config_loader import PlatformConfig


def make_config(extra=None):
    base = {
        "platform": "alipay",
        "source": {"type": "excel", "path": "dummy.xlsx"},
        "field_mapping": {
            "date": "交易时间",
            "store": "商家名称",
            "order_id": "商户订单号",
        },
        "amount_formula": "支付金额 - 退款金额",
    }
    if extra:
        base.update(extra)
    return PlatformConfig.from_dict(base)


class TestBillNormalizer:
    def test_normalize_returns_unified_schema(self, alipay_raw_df):
        """标准化后应包含统一字段"""
        config = make_config()
        unified = BillNormalizer(config).normalize(source_df=alipay_raw_df)

        assert "date" in unified.columns
        assert "store" in unified.columns
        assert "amount" in unified.columns
        assert "platform" in unified.columns

    def test_row_count_preserved(self, alipay_raw_df):
        """标准化不改变行数（过滤器为空时）"""
        config = make_config()
        unified = BillNormalizer(config).normalize(source_df=alipay_raw_df)
        assert len(unified) == len(alipay_raw_df)

    def test_filter_reduces_rows(self, alipay_raw_df):
        """过滤器应减少行数"""
        config = make_config(extra={
            "filter": {"column": "商家名称", "op": "eq", "value": "旗舰店A"}
        })
        unified = BillNormalizer(config).normalize(source_df=alipay_raw_df)
        assert len(unified) < len(alipay_raw_df)
        assert (unified["store"] == "旗舰店A").all()

    def test_date_type(self, alipay_raw_df):
        """日期字段应被解析为 date 对象"""
        config = make_config()
        unified = BillNormalizer(config).normalize(source_df=alipay_raw_df)
        assert unified["date"].iloc[0] == date(2024, 1, 5)

    def test_amount_formula(self, alipay_raw_df):
        """金额公式应正确计算"""
        config = make_config()
        unified = BillNormalizer(config).normalize(source_df=alipay_raw_df)
        # 第4行(index=3): 支付=150, 退款=20 -> 130
        assert unified["amount"].iloc[3] == pytest.approx(130.0)

    def test_platform_label_injected(self, alipay_raw_df):
        """应自动注入平台标识"""
        config = make_config()
        unified = BillNormalizer(config).normalize(source_df=alipay_raw_df)
        assert (unified["platform"] == "alipay").all()

    def test_step_by_step(self, alipay_raw_df):
        """分步调用应与 normalize() 结果一致"""
        config = make_config()
        normalizer = BillNormalizer(config)
        filtered = normalizer.filter(alipay_raw_df)
        mapped = normalizer.map(filtered)

        full = normalizer.normalize(source_df=alipay_raw_df)
        assert list(mapped.columns) == list(full.columns)
        assert len(mapped) == len(full)

    def test_wechat_normalize(self, wechat_raw_df):
        """微信平台标准化"""
        config = PlatformConfig.from_dict({
            "platform": "wechat",
            "source": {"type": "excel", "path": "dummy.xlsx"},
            "field_mapping": {
                "date": "交易时间",
                "store": "商品名称",
                "order_id": "微信单号",
            },
            "amount_formula": "金额(元) - 退款金额(元)",
        })
        unified = BillNormalizer(config).normalize(source_df=wechat_raw_df)
        # 店铺Y: 300-30=270
        store_y = unified[unified["store"] == "店铺Y商品"]
        assert store_y["amount"].iloc[0] == pytest.approx(270.0)
