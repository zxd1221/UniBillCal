"""
字段映射器 - 将平台原始 DataFrame 映射为统一字段名的 DataFrame
"""

import pandas as pd
from .formula import apply_formula
from .config_loader import PlatformConfig


# 统一格式的核心字段
_CORE_FIELDS = ["date", "store", "order_id", "amount", "platform", "remark"]


class FieldMapper:
    """
    根据 PlatformConfig 中的 field_mapping 和 amount_formula，
    将原始 DataFrame 转换为包含统一字段的 DataFrame。

    field_mapping 格式（YAML 侧）:
        date:     交易时间
        store:    商家名称
        order_id: 商户订单号   # 可选
        remark:   备注         # 可选

    amount_formula（与 field_mapping 中的 amount 二选一）:
        "支付金额 - 退款金额"
    """

    def __init__(self, config: PlatformConfig):
        self.config = config

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        执行字段映射，返回统一字段名的 DataFrame。
        原始列中不在映射表里的列将被丢弃（extra_fields 除外）。
        """
        df = df.copy()
        result = pd.DataFrame(index=df.index)

        mapping = self.config.field_mapping  # standard -> source
        # 1. 先执行金额公式（使用原始列名）
        if self.config.amount_formula:
            result["amount"] = apply_formula(df, self.config.amount_formula)
        elif "amount" in mapping:
            src_col = mapping["amount"]
            self._check_col_exists(df, src_col, "amount")
            result["amount"] = pd.to_numeric(df[src_col], errors="coerce").fillna(0)

        # 2. 映射其他标准字段
        for std_field, src_col in mapping.items():
            if std_field == "amount":
                continue  # 已处理
            if src_col not in df.columns:
                # 非必填字段缺失时填 None，必填字段报错
                if std_field in ("date",):
                    raise ValueError(
                        f"平台 {self.config.platform!r}: "
                        f"字段 '{std_field}' 映射的源列 '{src_col}' 不存在，"
                        f"实际列: {list(df.columns)}"
                    )
                result[std_field] = None
            else:
                result[std_field] = df[src_col]

        # 3. 日期标准化
        if "date" in result.columns:
            result["date"] = pd.to_datetime(result["date"], errors="coerce").dt.date

        # 4. 注入平台标识
        result["platform"] = self.config.platform

        # 5. 保留额外字段（extra_fields）
        for col in self.config.extra_fields:
            if col in df.columns:
                result[col] = df[col]

        return result

    def _check_col_exists(self, df: pd.DataFrame, col: str, std_field: str) -> None:
        if col not in df.columns:
            raise ValueError(
                f"平台 {self.config.platform!r}: "
                f"字段 '{std_field}' 映射的源列 '{col}' 不存在，"
                f"实际列: {list(df.columns)}"
            )
