"""字段映射器测试（FieldMapper）"""

import pytest
import pandas as pd
from datetime import date
from unibillcal.core.mapper import FieldMapper
from unibillcal.core.config_loader import PlatformConfig
from tests.conftest import make_alipay_config


def make_config(extra=None):
    return PlatformConfig.from_dict(make_alipay_config(extra))


class TestFieldMapper:
    def test_unified_fields_present(self, alipay_raw_df):
        """Mapper 输出必须包含所有统一标准字段"""
        result = FieldMapper(make_config()).transform(alipay_raw_df)

        for field in ("business_date", "store_name", "amount",
                      "raw_amount", "platform", "source_type", "source_id"):
            assert field in result.columns, f"缺少统一字段: {field}"

    def test_business_date_parsed(self, alipay_raw_df):
        """business_date 应被解析为 date 对象"""
        result = FieldMapper(make_config()).transform(alipay_raw_df)
        assert result["business_date"].iloc[0] == date(2024, 1, 5)

    def test_raw_amount_equals_formula_result(self, alipay_raw_df):
        """raw_amount 应等于公式计算值，amount 初始值与 raw_amount 相同"""
        result = FieldMapper(make_config()).transform(alipay_raw_df)
        # 第4行(index=3): 支付金额=150, 退款金额=20 -> 130
        assert result["raw_amount"].iloc[3] == pytest.approx(130.0)
        assert result["amount"].iloc[3] == pytest.approx(130.0)

    def test_platform_injected(self, alipay_raw_df):
        """platform 字段应自动注入"""
        result = FieldMapper(make_config()).transform(alipay_raw_df)
        assert (result["platform"] == "alipay").all()

    def test_source_type_injected(self, alipay_raw_df):
        """source_type 应自动从 source.type 注入"""
        result = FieldMapper(make_config()).transform(alipay_raw_df)
        assert (result["source_type"] == "excel").all()

    def test_source_id_uses_order_no(self, alipay_raw_df):
        """source_id 应包含平台前缀和订单号"""
        result = FieldMapper(make_config()).transform(alipay_raw_df)
        assert result["source_id"].iloc[0].startswith("alipay_")
        assert "ALI001" in result["source_id"].iloc[0]

    def test_missing_business_date_raises(self):
        """business_date 源列缺失应报错"""
        config = make_config()
        df = pd.DataFrame({"商家名称": ["A"], "支付金额": [100.0], "退款金额": [0.0]})
        with pytest.raises(ValueError, match="business_date"):
            FieldMapper(config).transform(df)

    def test_extra_fields_preserved(self, alipay_raw_df):
        """extra_fields 中指定的原始列应被保留"""
        config = make_config(extra={"extra_fields": ["备注"]})
        result = FieldMapper(config).transform(alipay_raw_df)
        assert "备注" in result.columns

    def test_string_fields_stripped(self, alipay_raw_df):
        """字符串字段应去除首尾空格"""
        df = alipay_raw_df.copy()
        df.loc[0, "商家名称"] = "  旗舰店A  "
        result = FieldMapper(make_config()).transform(df)
        assert result["store_name"].iloc[0] == "旗舰店A"
