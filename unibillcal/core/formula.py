"""
金额公式引擎 - 安全地对 DataFrame 每行执行金额计算公式

公式示例:
  "支付金额 - 退款金额"
  "收入金额 + 补贴金额 - 手续费"
  "总金额 * 0.8"

支持: +  -  *  /  ()  数字字面量
列名中的空格用反引号转义，或直接使用列名（引擎会自动处理）
"""

import re
import pandas as pd
import numpy as np


# 匹配 DataFrame 列名（含中文、空格、字母、数字）
_IDENT_RE = re.compile(r"[A-Za-z\u4e00-\u9fff_][\w\u4e00-\u9fff\s]*")


def _sort_names_by_length(names: list[str]) -> list[str]:
    """较长的名字排前面，避免短名字误匹配"""
    return sorted(names, key=len, reverse=True)


def apply_formula(df: pd.DataFrame, formula: str) -> pd.Series:
    """
    对 DataFrame 每行应用金额公式，返回计算结果 Series。

    策略：
    1. 找出公式中所有与 df.columns 匹配的列名
    2. 将列名替换为 df 中对应列的数值（用 locals 字典传给 eval）
    3. 使用 pandas/numpy eval 安全计算

    Args:
        df: 原始（或已初步映射的）DataFrame
        formula: 包含列名的算术表达式

    Returns:
        pd.Series，每行的计算结果
    """
    if not formula or not formula.strip():
        raise ValueError("amount_formula 不能为空")

    cols_in_formula = _extract_columns(formula, df.columns.tolist())
    if not cols_in_formula:
        raise ValueError(
            f"公式 {formula!r} 中未找到任何与数据列匹配的字段名。"
            f"可用列: {list(df.columns)}"
        )

    # 将列名替换为合法的 Python 变量名（去掉空格）
    safe_formula = formula
    col_map: dict[str, str] = {}
    for col in _sort_names_by_length(cols_in_formula):
        safe_var = _to_safe_varname(col)
        col_map[col] = safe_var
        # 精确替换（全词，不能是更长名字的子串）
        safe_formula = _replace_whole_word(safe_formula, col, safe_var)

    # 构建 locals 字典：安全变量名 -> 数值列（强制转 float）
    local_vars = {
        safe_var: pd.to_numeric(df[col], errors="coerce").fillna(0)
        for col, safe_var in col_map.items()
    }

    # 用 pandas.eval 执行（仅允许算术运算）
    try:
        result = pd.eval(safe_formula, local_dict=local_vars, engine="python")
    except Exception as e:
        raise ValueError(f"公式计算失败: {formula!r} -> {safe_formula!r}: {e}") from e

    if isinstance(result, (int, float, np.number)):
        result = pd.Series([result] * len(df), index=df.index)

    return result.rename("amount")


def _extract_columns(formula: str, available_cols: list[str]) -> list[str]:
    """从公式中提取所有出现的列名（与 available_cols 取交集）"""
    found = []
    for col in _sort_names_by_length(available_cols):
        if col in formula:
            found.append(col)
    return found


def _to_safe_varname(name: str) -> str:
    """将含空格/中文的列名转为合法 Python 变量名"""
    # 替换非字母数字下划线字符
    safe = re.sub(r"[^\w]", "_", name, flags=re.UNICODE)
    if safe and safe[0].isdigit():
        safe = "_" + safe
    return safe


def _replace_whole_word(text: str, old: str, new: str) -> str:
    """
    在 text 中将 old 替换为 new。
    由于列名可能含中文/空格，不能用 \b 边界，
    采用精确字符串替换（已按长度降序排列，不会误匹配子串）。
    """
    return text.replace(old, new)
