"""UnifiedProcessor 单元测试"""

import pytest
import pandas as pd
from unittest.mock import patch
from unibillcal.core.processor import UnifiedProcessor
from unibillcal.core.processing_config import ProcessingConfig


@pytest.fixture
def unified_df():
    """模拟来自多平台标准化后合并的 DataFrame"""
    return pd.DataFrame({
        "date":     ["2024-01-05", "2024-01-05", "2024-01-05",
                     "2024-01-06", "2024-01-06", "2024-01-07"],
        "store":    ["旗舰店A", "旗舰店A", "旗舰店B",
                     "旗舰店A", "旗舰店C", "旗舰店B"],
        "order_id": ["ALI001", "ALI006", "ALI002",
                     "ALI003", "ALI004", "WX001"],
        "amount":   [100.0, 60.0, 200.0, 130.0, 80.0, 500.0],
        "platform": ["alipay", "alipay", "alipay",
                     "alipay", "alipay", "wechat"],
    })


@pytest.fixture
def category_ref():
    return pd.DataFrame({
        "商家名称":  ["旗舰店A", "旗舰店B", "旗舰店C"],
        "类目名称":  ["服装", "电子", "服装"],
        "科目代码":  ["6001.01", "6001.02", "6001.01"],
    })


class TestUnifiedProcessor:
    def test_aggregate_sums_amount(self, unified_df):
        """相同分组键的金额应被求和"""
        config = ProcessingConfig.from_dict({})
        processor = UnifiedProcessor(config)
        result = processor.process(unified_df)

        # 旗舰店A 跨 alipay 平台：100+60+130=290
        store_a_alipay = result[
            (result["store"] == "旗舰店A") & (result["platform"] == "alipay")
        ]
        assert store_a_alipay["amount"].sum() == pytest.approx(290.0)

    def test_aggregate_counts_orders(self, unified_df):
        """订单计数应正确统计"""
        config = ProcessingConfig.from_dict({})
        processor = UnifiedProcessor(config)
        result = processor.process(unified_df)

        # 旗舰店A 在 2024-01-05 有2笔
        a5 = result[
            (result["store"] == "旗舰店A") &
            (result["date"] == "2024-01-05") &
            (result["platform"] == "alipay")
        ]
        assert a5["order_count"].iloc[0] == 2

    def test_reduces_row_count(self, unified_df):
        """汇总后行数应少于原始行数"""
        config = ProcessingConfig.from_dict({})
        processor = UnifiedProcessor(config)
        result = processor.process(unified_df)
        assert len(result) < len(unified_df)

    def test_with_reference_join(self, unified_df, category_ref):
        """关联配置表后应增加 category / subject 字段"""
        refs_cfg = [{
            "name": "category_mapping",
            "source": {"type": "excel", "path": "dummy.xlsx"},
            "join_on": {"left": "store", "right": "商家名称"},
            "fields": {"category": "类目名称", "subject": "科目代码"},
        }]
        config = ProcessingConfig.from_dict({"references": refs_cfg})
        processor = UnifiedProcessor(config)

        # 通过 patch ExcelAdapter.load 来绕过文件读取
        from unibillcal.adapters.excel_adapter import ExcelAdapter
        with patch.object(ExcelAdapter, "load", return_value=category_ref):
            joined = processor._join_references(unified_df.copy())

        assert "category" in joined.columns
        assert joined[joined["store"] == "旗舰店A"]["category"].iloc[0] == "服装"

    def test_no_references_passthrough(self, unified_df):
        """无关联配置表时，数据应正常通过"""
        config = ProcessingConfig.from_dict({})
        processor = UnifiedProcessor(config)
        joined = processor._join_references(unified_df)
        assert len(joined) == len(unified_df)

    def test_custom_group_by(self, unified_df):
        """修改 GROUP_BY_FIELDS 常量可以改变汇总维度"""
        config = ProcessingConfig.from_dict({})
        processor = UnifiedProcessor(config)
        # 只按 store 分组（模拟修改业务规则）
        original_group_by = UnifiedProcessor.GROUP_BY_FIELDS
        try:
            UnifiedProcessor.GROUP_BY_FIELDS = ["store"]
            result = processor._aggregate(unified_df)
            # 旗舰店A 跨平台跨日期全部合并
            store_a = result[result["store"] == "旗舰店A"]
            assert store_a["amount"].iloc[0] == pytest.approx(290.0)
        finally:
            UnifiedProcessor.GROUP_BY_FIELDS = original_group_by
