"""
UnifiedProcessor - 统一账单业务逻辑处理器

职责：对来自所有平台的标准化账单数据，执行统一的业务计算。

════════════════════════════════════════════════════════════
  新增平台？  → 只需添加平台配置文件，无需修改本文件
  改业务规则？→ 修改本文件中标注 [可修改] 的方法或常量
════════════════════════════════════════════════════════════

处理流程：
  1. 关联公共配置表（类目/科目映射）
  2. 汇总计算（统一维度分组 + 金额求和）
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
    │  [可修改] 业务规则常量                                   │
    │  修改下面的常量即可调整汇总维度、金额来源等业务规则       │
    └─────────────────────────────────────────────────────────┘
    """

    # ================================================================
    # [可修改] 汇总维度 - 按这些字段分组汇总
    # ================================================================
    GROUP_BY_FIELDS: list[str] = [
        "date",
        "store",
        "category",
        "subject",
        "platform",
    ]

    # ================================================================
    # [可修改] 求和字段 - 这些字段在分组内求和
    # ================================================================
    SUM_FIELDS: list[str] = ["amount"]

    # ================================================================
    # [可修改] 订单计数字段名（None 表示不统计订单数）
    # ================================================================
    ORDER_COUNT_FIELD: str | None = "order_count"

    # ================================================================
    # [可修改] 订单 ID 字段名（用于计数）
    # ================================================================
    ORDER_ID_FIELD: str = "order_id"

    def __init__(self, config: ProcessingConfig):
        self.config = config

    # ------------------------------------------------------------------ #
    #  主流程
    # ------------------------------------------------------------------ #

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        执行完整的统一处理：关联配置表 → 汇总计算。

        Args:
            df: 所有平台标准化后合并的 DataFrame（统一字段格式）

        Returns:
            汇总后的 DataFrame，包含 category / subject / amount / order_count 等
        """
        logger.info("统一处理开始，输入 %d 行", len(df))

        df = self._join_references(df)
        logger.info("关联配置表完成，列: %s", list(df.columns))

        df = self._aggregate(df)
        logger.info("汇总完成，共 %d 行", len(df))

        return df

    # ------------------------------------------------------------------ #
    # [可修改] 关联公共配置表
    # ------------------------------------------------------------------ #

    def _join_references(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        关联公共配置表（类目映射、科目映射等）。

        [可修改] 如需添加额外的关联逻辑（如多级映射、兜底规则），在此处扩展。
        """
        if not self.config.references:
            return df
        return ReferenceManager(self.config.references).apply(df)

    # ------------------------------------------------------------------ #
    # [可修改] 汇总计算
    # ------------------------------------------------------------------ #

    def _aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        按统一维度分组汇总。

        [可修改] 修改此方法以调整汇总规则，例如：
          - 改变分组维度：修改 GROUP_BY_FIELDS 常量
          - 增加加权平均：在 agg_dict 中添加 mean 规则
          - 增加自定义列：在 result 上追加新列
        """
        # 只使用 DataFrame 中实际存在的分组字段
        group_fields = [f for f in self.GROUP_BY_FIELDS if f in df.columns]
        if not group_fields:
            logger.warning("分组字段均不存在于数据中，跳过汇总")
            return df

        agg_dict: dict = {}

        # 求和字段
        for col in self.SUM_FIELDS:
            if col in df.columns:
                agg_dict[col] = (col, "sum")

        # 订单计数
        if self.ORDER_COUNT_FIELD and self.ORDER_ID_FIELD in df.columns:
            agg_dict[self.ORDER_COUNT_FIELD] = (self.ORDER_ID_FIELD, "count")
        elif self.ORDER_COUNT_FIELD:
            # order_id 不存在时，按行数计数
            df = df.copy()
            df["_row_"] = 1
            agg_dict[self.ORDER_COUNT_FIELD] = ("_row_", "sum")

        if not agg_dict:
            return df.drop_duplicates(subset=group_fields).reset_index(drop=True)

        result = (
            df.groupby(group_fields, dropna=False)
            .agg(**{k: pd.NamedAgg(column=v[0], aggfunc=v[1]) for k, v in agg_dict.items()})
            .reset_index()
        )

        # 清理临时列
        if "_row_" in df.columns:
            result = result.drop(columns=["_row_"], errors="ignore")

        return result
