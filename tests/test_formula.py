"""金额公式引擎测试"""

import pytest
import pandas as pd
from unibillcal.core.formula import apply_formula


def make_df(**kwargs):
    return pd.DataFrame(kwargs)


class TestApplyFormula:
    def test_single_column(self):
        df = make_df(金额=[100.0, 200.0, 300.0])
        result = apply_formula(df, "金额")
        assert list(result) == [100.0, 200.0, 300.0]

    def test_subtraction(self):
        df = make_df(支付金额=[100.0, 200.0], 退款金额=[10.0, 0.0])
        result = apply_formula(df, "支付金额 - 退款金额")
        assert list(result) == [90.0, 200.0]

    def test_multi_operands(self):
        df = make_df(收入=[100.0, 200.0], 退款=[10.0, 20.0], 补贴=[5.0, 0.0])
        result = apply_formula(df, "收入 - 退款 + 补贴")
        assert list(result) == [95.0, 180.0]

    def test_with_spaces_in_column_name(self):
        df = make_df(**{"金额(元)": [500.0, 300.0], "退款金额(元)": [0.0, 30.0]})
        result = apply_formula(df, "金额(元) - 退款金额(元)")
        assert list(result) == [500.0, 270.0]

    def test_scalar_multiplier(self):
        df = make_df(金额=[100.0, 200.0])
        result = apply_formula(df, "金额 * 0.8")
        assert list(result) == pytest.approx([80.0, 160.0])

    def test_nan_treated_as_zero(self):
        df = make_df(支付金额=[100.0, float("nan")], 退款金额=[10.0, 0.0])
        result = apply_formula(df, "支付金额 - 退款金额")
        assert list(result) == pytest.approx([90.0, 0.0])

    def test_empty_formula_raises(self):
        df = make_df(金额=[100.0])
        with pytest.raises(ValueError, match="不能为空"):
            apply_formula(df, "")

    def test_no_matching_column_raises(self):
        df = make_df(金额=[100.0])
        with pytest.raises(ValueError, match="未找到"):
            apply_formula(df, "不存在的列 - 另一个不存在的列")
