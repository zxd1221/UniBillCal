"""汇总引擎测试"""

import pytest
import pandas as pd
from unibillcal.core.aggregator import Aggregator, register_strategy, AggregationStrategy


@pytest.fixture
def mapped_df():
    return pd.DataFrame({
        "date":     ["2024-01-05", "2024-01-05", "2024-01-06", "2024-01-06"],
        "store":    ["旗舰店A", "旗舰店A", "旗舰店B", "旗舰店A"],
        "category": ["服装", "服装", "电子", "服装"],
        "subject":  ["6001.01", "6001.01", "6001.02", "6001.01"],
        "amount":   [90.0, 130.0, 200.0, 80.0],
        "platform": ["alipay"] * 4,
    })


class TestStandardAggregation:
    def test_group_and_sum(self, mapped_df):
        agg = Aggregator({
            "strategy": "standard",
            "group_by": ["date", "store", "category", "subject", "platform"],
            "sum_fields": ["amount"],
        })
        result = agg.run(mapped_df)
        # 旗舰店A 在 2024-01-05 有两条，应合并为 90+130=220
        a5 = result[(result["store"] == "旗舰店A") & (result["date"] == "2024-01-05")]
        assert len(a5) == 1
        assert a5["amount"].iloc[0] == pytest.approx(220.0)

    def test_count_field(self, mapped_df):
        agg = Aggregator({
            "strategy": "standard",
            "group_by": ["date", "store", "platform"],
            "sum_fields": ["amount"],
            "count_field": "order_count",
        })
        result = agg.run(mapped_df)
        a5 = result[(result["store"] == "旗舰店A") & (result["date"] == "2024-01-05")]
        assert a5["order_count"].iloc[0] == 2

    def test_no_aggregation_passthrough(self, mapped_df):
        agg = Aggregator({"strategy": "none"})
        result = agg.run(mapped_df)
        assert len(result) == 4

    def test_unknown_strategy_raises(self, mapped_df):
        with pytest.raises(ValueError, match="未知汇总策略"):
            Aggregator({"strategy": "nonexistent"}).run(mapped_df)


class TestCustomStrategy:
    def test_register_and_use_custom_strategy(self, mapped_df):
        class DoubleAmountStrategy(AggregationStrategy):
            def aggregate(self, df, config):
                df = df.copy()
                df["amount"] = df["amount"] * 2
                return df

        register_strategy("double", DoubleAmountStrategy())
        result = Aggregator({"strategy": "double"}).run(mapped_df)
        assert result["amount"].iloc[0] == pytest.approx(mapped_df["amount"].iloc[0] * 2)
