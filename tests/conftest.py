"""
测试公共夹具 - 生成内存中的样本数据
（原始数据使用中文列名，反映真实平台导出格式）
"""

import pytest
import pandas as pd
from datetime import date


@pytest.fixture
def alipay_raw_df():
    """
    模拟支付宝原始账单数据（Excel 导出格式，保持中文列名）。
    旗舰店A 在 2024-01-05 有两条记录（ALI001 + ALI006），
    合计 6 条原始行 → 汇总后 5 个 (business_date, store_name) 组合。
    """
    return pd.DataFrame({
        "交易时间": ["2024-01-05", "2024-01-05", "2024-01-05",
                    "2024-01-06", "2024-01-06", "2024-01-07"],
        "商家名称":  ["旗舰店A", "旗舰店A", "旗舰店B",
                    "旗舰店A", "旗舰店C", "旗舰店B"],
        "商户订单号": ["ALI001", "ALI006", "ALI002",
                     "ALI003", "ALI004", "ALI005"],
        "支付金额":  [100.0, 60.0, 200.0, 150.0, 80.0, 300.0],
        "退款金额":  [0.0,   0.0,  0.0,   20.0,  0.0,  50.0],
        "交易状态":  ["交易成功"] * 6,
        "交易分类":  ["购物"] * 6,
        "备注":      [""] * 6,
    })


@pytest.fixture
def wechat_raw_df():
    """模拟微信支付原始账单数据"""
    return pd.DataFrame({
        "交易时间":    ["2024-01-05", "2024-01-05", "2024-01-06"],
        "商品名称":    ["店铺X商品",  "店铺Y商品",  "店铺X商品"],
        "微信单号":    ["WX001",      "WX002",      "WX003"],
        "金额(元)":    [500.0,        300.0,        200.0],
        "退款金额(元)": [0.0,          30.0,          0.0],
        "收支":        ["收入",        "收入",        "收入"],
        "当前状态":    ["支付成功",    "支付成功",    "支付成功"],
    })


@pytest.fixture
def category_ref_df():
    """模拟类目/科目映射配置表"""
    return pd.DataFrame({
        "商家名称":  ["旗舰店A", "旗舰店B", "旗舰店C"],
        "类目名称":  ["服装",    "电子",    "服装"],
        "科目代码":  ["6001.01", "6001.02", "6001.01"],
    })


def make_alipay_config(extra=None):
    """支付宝平台配置字典工厂（使用新标准字段名）"""
    base = {
        "platform": "alipay",
        "source": {"type": "excel", "path": "dummy.xlsx"},
        "field_mapping": {
            "business_date": "交易时间",
            "store_name":    "商家名称",
            "order_no":      "商户订单号",
        },
        "amount_formula": "支付金额 - 退款金额",
    }
    if extra:
        base.update(extra)
    return base
