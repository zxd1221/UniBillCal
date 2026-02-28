"""BillPipeline 端到端测试（Layer 1 + Layer 2 联合）"""

import pytest
import pandas as pd
from unibillcal.core.pipeline import BillPipeline
from unibillcal.core.config_loader import PlatformConfig
from unibillcal.core.processing_config import ProcessingConfig


def make_platform_config(platform="alipay", extra=None):
    base = {
        "platform": platform,
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


def make_pipeline(platform_cfg=None, extra_platform_cfg=None):
    cfg = platform_cfg or make_platform_config(extra=extra_platform_cfg)
    return BillPipeline(
        platform_configs=[cfg],
        processing_config=ProcessingConfig.from_dict({}),
    )


class TestBillPipeline:
    def test_full_pipeline(self, alipay_raw_df):
        """单平台：标准化 + 统一处理"""
        pipeline = make_pipeline()
        result = pipeline.run(source_dfs={"alipay": alipay_raw_df})

        assert "date" in result.columns
        assert "store" in result.columns
        assert "amount" in result.columns
        assert "order_count" in result.columns
        assert "platform" in result.columns
        # 汇总后行数 < 原始行数
        assert len(result) < len(alipay_raw_df)

    def test_amount_correctly_aggregated(self, alipay_raw_df):
        """旗舰店A 跨日期总金额：(100+60+130)=290"""
        pipeline = make_pipeline()
        result = pipeline.run(source_dfs={"alipay": alipay_raw_df})
        store_a = result[result["store"] == "旗舰店A"]
        assert store_a["amount"].sum() == pytest.approx(290.0)

    def test_filter_applied(self, alipay_raw_df):
        """平台过滤器应在标准化阶段生效"""
        pipeline = make_pipeline(extra_platform_cfg={
            "filter": {"column": "商家名称", "op": "eq", "value": "旗舰店A"}
        })
        result = pipeline.run(source_dfs={"alipay": alipay_raw_df})
        assert (result["store"] == "旗舰店A").all()

    def test_multi_platform(self, alipay_raw_df, wechat_raw_df):
        """多平台合并后统一处理"""
        wechat_cfg = PlatformConfig.from_dict({
            "platform": "wechat",
            "source": {"type": "excel", "path": "dummy.xlsx"},
            "field_mapping": {
                "date": "交易时间",
                "store": "商品名称",
                "order_id": "微信单号",
            },
            "amount_formula": "金额(元) - 退款金额(元)",
        })
        pipeline = BillPipeline(
            platform_configs=[make_platform_config(), wechat_cfg],
            processing_config=ProcessingConfig.from_dict({}),
        )
        result = pipeline.run(source_dfs={
            "alipay": alipay_raw_df,
            "wechat": wechat_raw_df,
        })
        platforms = set(result["platform"].unique())
        assert "alipay" in platforms
        assert "wechat" in platforms

    def test_config_validation_missing_date(self):
        """缺少 date 字段映射应在配置加载时报错"""
        with pytest.raises(ValueError, match="date"):
            PlatformConfig.from_dict({
                "platform": "test",
                "source": {"type": "excel", "path": "x.xlsx"},
                "field_mapping": {"store": "商家名称"},
                "amount_formula": "金额",
            })

    def test_wechat_pipeline(self, wechat_raw_df):
        """微信单平台流水线"""
        wechat_cfg = PlatformConfig.from_dict({
            "platform": "wechat",
            "source": {"type": "excel", "path": "dummy.xlsx"},
            "field_mapping": {
                "date": "交易时间",
                "store": "商品名称",
                "order_id": "微信单号",
            },
            "amount_formula": "金额(元) - 退款金额(元)",
        })
        result = BillPipeline(
            platform_configs=[wechat_cfg],
            processing_config=ProcessingConfig.from_dict({}),
        ).run(source_dfs={"wechat": wechat_raw_df})

        assert len(result) > 0
        store_y = result[result["store"] == "店铺Y商品"]
        assert store_y["amount"].iloc[0] == pytest.approx(270.0)
