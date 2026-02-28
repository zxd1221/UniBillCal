"""
行过滤器 - 根据配置过滤 DataFrame 中不需要的行

filter 配置示例:
  # 单条件（等值过滤）
  filter:
    column: 交易状态
    value: 交易成功

  # 多条件（AND 关系）
  filter:
    conditions:
      - {column: 交易状态, op: eq, value: 交易成功}
      - {column: 金额, op: gt, value: 0}

  # 排除某些值
  filter:
    conditions:
      - {column: 交易类型, op: not_in, value: [退款, 冻结]}
"""

import pandas as pd
from typing import Any


_OPS = {
    "eq":       lambda s, v: s == v,
    "ne":       lambda s, v: s != v,
    "gt":       lambda s, v: pd.to_numeric(s, errors="coerce") > v,
    "gte":      lambda s, v: pd.to_numeric(s, errors="coerce") >= v,
    "lt":       lambda s, v: pd.to_numeric(s, errors="coerce") < v,
    "lte":      lambda s, v: pd.to_numeric(s, errors="coerce") <= v,
    "in":       lambda s, v: s.isin(v if isinstance(v, list) else [v]),
    "not_in":   lambda s, v: ~s.isin(v if isinstance(v, list) else [v]),
    "contains": lambda s, v: s.astype(str).str.contains(str(v), na=False),
    "startswith": lambda s, v: s.astype(str).str.startswith(str(v), na=False),
    "notnull":  lambda s, v: s.notna(),
    "isnull":   lambda s, v: s.isna(),
}


def apply_filter(df: pd.DataFrame, filter_cfg: dict | None) -> pd.DataFrame:
    """根据过滤配置返回过滤后的 DataFrame"""
    if not filter_cfg:
        return df

    # 简写形式：{column: xxx, value: yyy}
    if "column" in filter_cfg and "conditions" not in filter_cfg:
        col = filter_cfg["column"]
        val = filter_cfg["value"]
        op = filter_cfg.get("op", "eq")
        return _apply_condition(df, col, op, val)

    # 多条件（AND）
    conditions = filter_cfg.get("conditions", [])
    mask = pd.Series([True] * len(df), index=df.index)
    for cond in conditions:
        col = cond["column"]
        op = cond.get("op", "eq")
        val = cond.get("value")
        sub_mask = _build_mask(df, col, op, val)
        mask = mask & sub_mask

    return df[mask].reset_index(drop=True)


def _apply_condition(df: pd.DataFrame, col: str, op: str, value: Any) -> pd.DataFrame:
    mask = _build_mask(df, col, op, value)
    return df[mask].reset_index(drop=True)


def _build_mask(df: pd.DataFrame, col: str, op: str, value: Any) -> pd.Series:
    if col not in df.columns:
        raise ValueError(
            f"过滤条件引用了不存在的列: {col!r}，"
            f"可用列: {list(df.columns)}"
        )
    op_func = _OPS.get(op)
    if op_func is None:
        raise ValueError(f"不支持的过滤操作: {op!r}，支持: {list(_OPS)}")
    return op_func(df[col], value)
