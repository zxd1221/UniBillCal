"""行过滤器测试"""

import pytest
import pandas as pd
from unibillcal.core.filter import apply_filter


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        "交易状态": ["交易成功", "交易关闭", "交易成功", "退款中"],
        "金额":     [100.0, 0.0, 200.0, -50.0],
        "类型":     ["购物", "购物", "转账", "购物"],
    })


class TestApplyFilter:
    def test_no_filter(self, sample_df):
        result = apply_filter(sample_df, None)
        assert len(result) == 4

    def test_eq_filter(self, sample_df):
        result = apply_filter(sample_df, {"column": "交易状态", "value": "交易成功"})
        assert len(result) == 2
        assert (result["交易状态"] == "交易成功").all()

    def test_gt_filter(self, sample_df):
        result = apply_filter(sample_df, {"column": "金额", "op": "gt", "value": 0})
        assert len(result) == 2

    def test_not_in_filter(self, sample_df):
        result = apply_filter(sample_df, {
            "column": "交易状态", "op": "not_in",
            "value": ["交易关闭", "退款中"]
        })
        assert len(result) == 2

    def test_multi_condition_and(self, sample_df):
        result = apply_filter(sample_df, {
            "conditions": [
                {"column": "交易状态", "op": "eq", "value": "交易成功"},
                {"column": "金额", "op": "gt", "value": 50},
            ]
        })
        assert len(result) == 2

    def test_invalid_column_raises(self, sample_df):
        with pytest.raises(ValueError, match="不存在的列"):
            apply_filter(sample_df, {"column": "不存在的列", "value": "x"})
