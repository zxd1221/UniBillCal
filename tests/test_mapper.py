"""字段映射器测试"""

import pytest
import pandas as pd
from datetime import date
from unibillcal.core.mapper import FieldMapper
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
        "output": {},
    }
    if extra:
        base.update(extra)
    return PlatformConfig.from_dict(base)


class TestFieldMapper:
    def test_basic_mapping(self, alipay_raw_df):
        config = make_config()
        mapper = FieldMapper(config)
        result = mapper.transform(alipay_raw_df)

        assert "date" in result.columns
        assert "store" in result.columns
        assert "amount" in result.columns
        assert "platform" in result.columns

    def test_date_parsed(self, alipay_raw_df):
        config = make_config()
        result = FieldMapper(config).transform(alipay_raw_df)
        assert result["date"].iloc[0] == date(2024, 1, 5)

    def test_amount_formula_applied(self, alipay_raw_df):
        config = make_config()
        result = FieldMapper(config).transform(alipay_raw_df)
        # 第四行(index=3): 支付金额=150, 退款金额=20 -> 130
        assert result["amount"].iloc[3] == pytest.approx(130.0)

    def test_platform_injected(self, alipay_raw_df):
        config = make_config()
        result = FieldMapper(config).transform(alipay_raw_df)
        assert (result["platform"] == "alipay").all()

    def test_missing_date_source_raises(self):
        config = make_config()
        df = pd.DataFrame({"商家名称": ["A"], "支付金额": [100.0], "退款金额": [0.0]})
        with pytest.raises(ValueError, match="date"):
            FieldMapper(config).transform(df)

    def test_extra_fields_preserved(self, alipay_raw_df):
        config = make_config(extra={"extra_fields": ["备注"]})
        result = FieldMapper(config).transform(alipay_raw_df)
        assert "备注" in result.columns
