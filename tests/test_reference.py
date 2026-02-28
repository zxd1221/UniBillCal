"""关联配置表管理器测试"""

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock
from unibillcal.core.reference import ReferenceManager


@pytest.fixture
def mapped_df():
    return pd.DataFrame({
        "business_date": ["2024-01-05", "2024-01-05", "2024-01-06"],
        "store_name":    ["旗舰店A", "旗舰店B", "旗舰店A"],
        "amount":        [90.0, 200.0, 130.0],
        "platform":      ["alipay"] * 3,
    })


@pytest.fixture
def category_ref():
    return pd.DataFrame({
        "商家名称":  ["旗舰店A", "旗舰店B"],
        "类目名称":  ["服装", "电子"],
        "科目代码":  ["6001.01", "6001.02"],
    })


class TestReferenceManager:
    def test_left_join_adds_fields(self, mapped_df, category_ref):
        refs_cfg = [{
            "name": "category_mapping",
            "source": {"type": "excel", "path": "dummy.xlsx"},
            "join_on": {"left": "store_name", "right": "商家名称"},
            "fields": {"category": "类目名称", "subject": "科目代码"},
        }]

        mgr = ReferenceManager(refs_cfg)
        # 用 mock 绕过实际文件读取
        with patch.object(mgr, "_cache", {"excel:dummy.xlsx": category_ref}):
            result = mgr.apply(mapped_df)

        assert "category" in result.columns
        assert "subject" in result.columns
        assert result[result["store_name"] == "旗舰店A"]["category"].iloc[0] == "服装"
        assert result[result["store_name"] == "旗舰店B"]["category"].iloc[0] == "电子"

    def test_unmatched_store_gets_nan(self, mapped_df, category_ref):
        df = mapped_df.copy()
        df.loc[2, "store_name"] = "未知店铺"
        refs_cfg = [{
            "name": "category_mapping",
            "source": {"type": "excel", "path": "dummy.xlsx"},
            "join_on": {"left": "store_name", "right": "商家名称"},
            "fields": {"category": "类目名称"},
        }]
        mgr = ReferenceManager(refs_cfg)
        with patch.object(mgr, "_cache", {"excel:dummy.xlsx": category_ref}):
            result = mgr.apply(df)

        assert pd.isna(result[result["store_name"] == "未知店铺"]["category"].iloc[0])
