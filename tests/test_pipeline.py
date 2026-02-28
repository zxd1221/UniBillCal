"""
流水线端到端测试（使用内存数据，不依赖文件系统/数据库）
"""

import pytest
import pandas as pd
from unibillcal.core.pipeline import BillPipeline
from unibillcal.core.config_loader import PlatformConfig


def make_pipeline(extra_config=None):
    base = {
        "platform": "alipay",
        "source": {"type": "excel", "path": "dummy.xlsx"},
        "field_mapping": {
            "date": "交易时间",
            "store": "商家名称",
            "order_id": "商户订单号",
        },
        "amount_formula": "支付金额 - 退款金额",
        "aggregation": {
            "strategy": "standard",
            "group_by": ["date", "store", "platform"],
            "sum_fields": ["amount"],
            "count_field": "order_count",
        },
        "output": {},
    }
    if extra_config:
        base.update(extra_config)
    config = PlatformConfig.from_dict(base)
    return BillPipeline(config)


class TestBillPipeline:
    def test_full_pipeline_no_reference(self, alipay_raw_df):
        """不含关联配置表的完整流水线"""
        pipeline = make_pipeline()
        result = pipeline.run(source_df=alipay_raw_df)

        assert "date" in result.columns
        assert "store" in result.columns
        assert "amount" in result.columns
        assert "order_count" in result.columns
        assert "platform" in result.columns

        # 汇总后行数应少于原始行数（有相同 date+store 的记录）
        assert len(result) < len(alipay_raw_df)

    def test_amount_correctly_aggregated(self, alipay_raw_df):
        """验证金额汇总正确"""
        pipeline = make_pipeline()
        result = pipeline.run(source_df=alipay_raw_df)

        # 旗舰店A: (100-0) + (60-0) + (150-20) = 290 (跨两天汇总)
        store_a = result[result["store"] == "旗舰店A"]
        total = store_a["amount"].sum()
        assert total == pytest.approx(290.0)

    def test_with_filter(self, alipay_raw_df):
        """验证过滤步骤生效"""
        pipeline = make_pipeline(extra_config={
            "filter": {
                "column": "商家名称",
                "op": "eq",
                "value": "旗舰店A",
            }
        })
        result = pipeline.run(source_df=alipay_raw_df)
        assert (result["store"] == "旗舰店A").all()

    def test_step_by_step(self, alipay_raw_df):
        """分步运行流水线"""
        pipeline = make_pipeline()

        # 只运行 map 步骤
        mapped = pipeline.map(alipay_raw_df)
        assert "amount" in mapped.columns
        assert len(mapped) == len(alipay_raw_df)

        # 继续运行 aggregate
        aggregated = pipeline.aggregate(mapped)
        assert len(aggregated) < len(mapped)

    def test_config_validation_missing_date(self):
        """缺少 date 字段映射应报错"""
        with pytest.raises(ValueError):
            PlatformConfig.from_dict({
                "platform": "test",
                "source": {"type": "excel", "path": "x.xlsx"},
                "field_mapping": {"store": "商家名称"},
                "amount_formula": "金额",
                "output": {},
            })

    def test_wechat_pipeline(self, wechat_raw_df):
        """微信账单流水线"""
        config_dict = {
            "platform": "wechat",
            "source": {"type": "excel", "path": "dummy.xlsx"},
            "field_mapping": {
                "date": "交易时间",
                "store": "商品名称",
                "order_id": "微信单号",
            },
            "amount_formula": "金额(元) - 退款金额(元)",
            "aggregation": {
                "strategy": "standard",
                "group_by": ["date", "store", "platform"],
                "sum_fields": ["amount"],
            },
            "output": {},
        }
        pipeline = BillPipeline(PlatformConfig.from_dict(config_dict))
        result = pipeline.run(source_df=wechat_raw_df)

        assert len(result) > 0
        # 店铺X: 500-0=500, 店铺Y: 300-30=270
        store_y = result[result["store"] == "店铺Y商品"]
        assert store_y["amount"].iloc[0] == pytest.approx(270.0)
