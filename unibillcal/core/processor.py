"""
UnifiedProcessor - 统一账单业务逻辑处理器

职责：对来自所有平台的标准化账单执行统一的业务计算。

════════════════════════════════════════════════════════════
  新增平台？  → 只需添加平台配置文件，无需修改本文件
  改业务规则？→ 修改本文件中标注 [可修改] 的方法或常量
════════════════════════════════════════════════════════════

处理流程：
  1. 关联公共配置表（类目/科目映射）
  2. 金额规范化（正负方向处理）
  3. 分组汇总（统一维度 + 金额求和）
"""

from __future__ import annotations

import logging
import pandas as pd

from .reference import ReferenceManager
from .processing_config import ProcessingConfig

logger = logging.getLogger(__name__)


class UnifiedProcessor:
    """
    对合并后的标准化账单执行统一业务逻辑。

    ┌─────────────────────────────────────────────────────────┐
    │  [可修改] 区域                                           │
    │  修改下方常量和方法即可调整业务规则，无需改动其他代码    │
    └─────────────────────────────────────────────────────────┘
    """

    # ================================================================
    # [可修改] 汇总维度 - 按这些字段分组汇总
    # ================================================================
    GROUP_BY_FIELDS: list[str] = [
        "business_date",
        "store_name",
        "category",
        "subject",
        "platform",
    ]

    # ================================================================
    # [可修改] 求和字段 - 分组内对这些字段求和
    # ================================================================
    SUM_FIELDS: list[str] = ["amount"]

    # ================================================================
    # [可修改] 订单计数字段名（None 表示不统计）
    # ================================================================
    ORDER_COUNT_FIELD: str | None = "order_count"

    # ================================================================
    # [可修改] 用于计数的订单号字段名
    # ================================================================
    ORDER_NO_FIELD: str = "order_no"

    def __init__(self, config: ProcessingConfig):
        self.config = config

    # ------------------------------------------------------------------ #
    #  主流程
    # ------------------------------------------------------------------ #

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        执行完整统一处理：关联配置表 → 金额规范化 → 汇总。

        Args:
            df: 所有平台标准化后合并的 DataFrame

        Returns:
            汇总后的 DataFrame（含 category / subject / amount / order_count 等）
        """
        logger.info("统一处理开始，输入 %d 行", len(df))

        df = self._join_references(df)
        logger.info("关联配置表完成，列: %s", list(df.columns))

        df = self._normalize_amount(df)

        df = self._aggregate(df)
        logger.info("汇总完成，共 %d 行", len(df))

        return df

    # ------------------------------------------------------------------ #
    # [可修改] 关联公共配置表
    # ------------------------------------------------------------------ #

    def _join_references(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        关联公共配置表（类目映射、科目映射等）。

        [可修改] 如需增加多级映射、兜底规则、模糊匹配等，在此扩展。
        """
        if not self.config.references:
            return df
        return ReferenceManager(self.config.references).apply(df)

    # ------------------------------------------------------------------ #
    # [可修改] 金额规范化
    # ------------------------------------------------------------------ #

    def _normalize_amount(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        对 amount 字段进行业务规范化（正负方向处理等）。

        [可修改] 默认不做额外处理（amount 已由 Mapper 按公式计算）。
        如需按交易类型区分收支正负，在此实现，例如：

            mask = df["transaction_type"] == "退款"
            df.loc[mask, "amount"] = -df.loc[mask, "amount"].abs()

        注意：此方法修改 amount，raw_amount 保持不变（原始计算值）。
        """
        return df

    # ------------------------------------------------------------------ #
    # [可修改] 汇总计算
    # ------------------------------------------------------------------ #

    def _aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        按统一维度分组汇总。

        [可修改] 调整汇总规则示例：
          - 改变分组维度 → 修改 GROUP_BY_FIELDS 常量
          - 增加均值列   → 在 agg_dict 中添加 mean 项
          - 不做汇总     → 直接 return df
        """
        group_fields = [f for f in self.GROUP_BY_FIELDS if f in df.columns]
        if not group_fields:
            logger.warning("GROUP_BY_FIELDS 中的字段均不在数据中，跳过汇总")
            return df

        agg_dict: dict = {}

        for col in self.SUM_FIELDS:
            if col in df.columns:
                agg_dict[col] = (col, "sum")

        if self.ORDER_COUNT_FIELD:
            if self.ORDER_NO_FIELD in df.columns:
                agg_dict[self.ORDER_COUNT_FIELD] = (self.ORDER_NO_FIELD, "count")
            else:
                df = df.copy()
                df["_cnt_"] = 1
                agg_dict[self.ORDER_COUNT_FIELD] = ("_cnt_", "sum")

        if not agg_dict:
            return df.drop_duplicates(subset=group_fields).reset_index(drop=True)

        result = (
            df.groupby(group_fields, dropna=False)
            .agg(**{k: pd.NamedAgg(column=v[0], aggfunc=v[1]) for k, v in agg_dict.items()})
            .reset_index()
        )

        return result
