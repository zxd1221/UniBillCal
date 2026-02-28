"""
汇总引擎 - 按配置对账单数据进行分组汇总

使用策略模式（Strategy Pattern）支持多种汇总规则，
未来新增汇总策略只需注册新的 AggregationStrategy 子类。

aggregation 配置示例:
  strategy: standard          # 汇总策略名，默认 standard
  group_by: [date, store, category, subject, platform]
  sum_fields: [amount]        # 求和字段
  mean_fields: []             # 求均值字段（可选）
  count_field: order_count    # 计数字段名（可选，输出行数）
  custom_rules:               # 额外的聚合规则（可选）
    commission: {func: sum, source: commission_fee}
"""

from __future__ import annotations

import pandas as pd
from abc import ABC, abstractmethod
from typing import Callable


# ------------------------------------------------------------------ #
#  抽象策略
# ------------------------------------------------------------------ #

class AggregationStrategy(ABC):
    """汇总策略基类"""

    @abstractmethod
    def aggregate(self, df: pd.DataFrame, config: dict) -> pd.DataFrame:
        """执行汇总，返回汇总后的 DataFrame"""
        ...


# ------------------------------------------------------------------ #
#  内置策略
# ------------------------------------------------------------------ #

class StandardAggregation(AggregationStrategy):
    """
    标准汇总策略：
    - 按 group_by 字段分组
    - 对 sum_fields 求和
    - 对 mean_fields 求均值
    - 可选添加行计数列
    - 支持 custom_rules 自定义聚合
    """

    def aggregate(self, df: pd.DataFrame, config: dict) -> pd.DataFrame:
        group_by = config.get("group_by", [])
        if not group_by:
            # 没有分组字段时，直接返回原数据
            return df

        # 过滤 group_by 字段，只保留 df 中存在的
        valid_group = [c for c in group_by if c in df.columns]
        if not valid_group:
            raise ValueError(
                f"group_by 中的字段均不在 DataFrame 中，"
                f"配置: {group_by}，实际列: {list(df.columns)}"
            )

        agg_dict: dict[str, Any] = {}

        # sum 字段
        for col in config.get("sum_fields", []):
            if col in df.columns:
                agg_dict[col] = "sum"

        # mean 字段
        for col in config.get("mean_fields", []):
            if col in df.columns:
                agg_dict[f"{col}_avg"] = pd.NamedAgg(column=col, aggfunc="mean")

        # 计数
        count_field = config.get("count_field")
        if count_field:
            # 用 size() 计数，后面手动添加列
            pass

        # custom_rules: {output_col: {func: "sum"|"mean"|"max"|"min", source: col}}
        for out_col, rule in config.get("custom_rules", {}).items():
            src = rule.get("source", out_col)
            func = rule.get("func", "sum")
            if src in df.columns:
                agg_dict[out_col] = pd.NamedAgg(column=src, aggfunc=func)

        if not agg_dict:
            # 没有聚合字段时，按 group_by 去重
            return df[valid_group].drop_duplicates().reset_index(drop=True)

        grouped = df.groupby(valid_group, dropna=False)
        result = grouped.agg(**{
            k: v if isinstance(v, pd.NamedAgg) else pd.NamedAgg(column=k, aggfunc=v)
            for k, v in agg_dict.items()
        }).reset_index()

        if count_field:
            counts = grouped.size().reset_index(name=count_field)
            result = result.merge(counts, on=valid_group, how="left")

        return result


class NoAggregation(AggregationStrategy):
    """不执行任何汇总，直接透传原始行"""

    def aggregate(self, df: pd.DataFrame, config: dict) -> pd.DataFrame:
        return df


class PivotAggregation(AggregationStrategy):
    """
    透视汇总策略：将某列的值展开为多列（用于交叉报表场景）。

    aggregation 配置:
      strategy: pivot
      index: [date, store]
      columns: category
      values: amount
      aggfunc: sum
    """

    def aggregate(self, df: pd.DataFrame, config: dict) -> pd.DataFrame:
        index = config.get("index", [])
        columns = config.get("columns")
        values = config.get("values", "amount")
        aggfunc = config.get("aggfunc", "sum")

        if not index or not columns:
            raise ValueError("pivot 策略需要 index 和 columns 配置")

        pivot = df.pivot_table(
            index=index,
            columns=columns,
            values=values,
            aggfunc=aggfunc,
            fill_value=0,
        )
        pivot.columns.name = None
        return pivot.reset_index()


# ------------------------------------------------------------------ #
#  策略注册表
# ------------------------------------------------------------------ #

_STRATEGY_REGISTRY: dict[str, AggregationStrategy] = {
    "standard": StandardAggregation(),
    "none": NoAggregation(),
    "pivot": PivotAggregation(),
}


def register_strategy(name: str, strategy: AggregationStrategy) -> None:
    """
    注册自定义汇总策略。
    新增业务逻辑时，实现 AggregationStrategy 并调用此函数注册。

    示例:
        class MyStrategy(AggregationStrategy):
            def aggregate(self, df, config):
                ...
        register_strategy("my_strategy", MyStrategy())
    """
    _STRATEGY_REGISTRY[name] = strategy


# ------------------------------------------------------------------ #
#  Aggregator 门面
# ------------------------------------------------------------------ #

class Aggregator:
    """根据配置选择并执行汇总策略"""

    def __init__(self, aggregation_config: dict):
        self.config = aggregation_config

    def run(self, df: pd.DataFrame) -> pd.DataFrame:
        strategy_name = self.config.get("strategy", "standard")
        strategy = _STRATEGY_REGISTRY.get(strategy_name)
        if strategy is None:
            raise ValueError(
                f"未知汇总策略: {strategy_name!r}，"
                f"已注册策略: {list(_STRATEGY_REGISTRY)}"
            )
        return strategy.aggregate(df, self.config)


# 补充类型注解
from typing import Any
