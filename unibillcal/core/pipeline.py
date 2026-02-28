"""
BillPipeline - 核心处理流水线

处理步骤:
  1. Load      读取原始数据（通过适配器）
  2. Filter    过滤不需要的行
  3. Map       字段映射 + 金额公式计算
  4. Reference 关联公共配置表（类目/科目映射等）
  5. Aggregate 汇总计算
  6. Output    写出结果

每个步骤都是独立模块，可单独测试或替换。
"""

from __future__ import annotations

import logging
import pandas as pd

from .config_loader import PlatformConfig
from .filter import apply_filter
from .mapper import FieldMapper
from .reference import ReferenceManager
from .aggregator import Aggregator
from ..adapters import get_adapter
from ..output import get_writer

logger = logging.getLogger(__name__)


class BillPipeline:
    """
    账单处理流水线。

    用法:
        config = PlatformConfig.from_file("config/alipay.yaml")
        pipeline = BillPipeline(config)
        result_df = pipeline.run()

    或直接使用类方法:
        result_df = BillPipeline.run_from_file("config/alipay.yaml")
    """

    def __init__(self, config: PlatformConfig):
        self.config = config
        self._steps_override: dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    #  工厂 / 便捷入口
    # ------------------------------------------------------------------ #

    @classmethod
    def run_from_file(cls, config_path: str) -> pd.DataFrame:
        """一行代码运行完整流水线"""
        config = PlatformConfig.from_file(config_path)
        return cls(config).run()

    @classmethod
    def run_from_dict(cls, config_dict: dict) -> pd.DataFrame:
        config = PlatformConfig.from_dict(config_dict)
        return cls(config).run()

    # ------------------------------------------------------------------ #
    #  主流程
    # ------------------------------------------------------------------ #

    def run(self, source_df: pd.DataFrame | None = None) -> pd.DataFrame:
        """
        执行完整流水线，返回统一格式 DataFrame。

        Args:
            source_df: 可直接传入已加载的 DataFrame（跳过 Load 步骤），
                       主要用于测试。
        """
        platform = self.config.platform
        logger.info("[%s] 开始处理", platform)

        # 1. Load
        if source_df is None:
            df = self._step_load()
        else:
            df = source_df.copy()
        logger.info("[%s] Load 完成，共 %d 行", platform, len(df))

        # 2. Filter（在原始列名阶段过滤）
        df = self._step_filter(df)
        logger.info("[%s] Filter 完成，剩余 %d 行", platform, len(df))

        # 3. Map
        df = self._step_map(df)
        logger.info("[%s] Map 完成，列: %s", platform, list(df.columns))

        # 4. Reference
        df = self._step_reference(df)
        logger.info("[%s] Reference 完成，列: %s", platform, list(df.columns))

        # 5. Aggregate
        df = self._step_aggregate(df)
        logger.info("[%s] Aggregate 完成，共 %d 行", platform, len(df))

        # 6. Output
        self._step_output(df)

        return df

    # ------------------------------------------------------------------ #
    #  各步骤实现
    # ------------------------------------------------------------------ #

    def _step_load(self) -> pd.DataFrame:
        source_cfg = self.config.source
        adapter_cls = get_adapter(source_cfg["type"])
        return adapter_cls(source_cfg).load()

    def _step_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        return apply_filter(df, self.config.filter)

    def _step_map(self, df: pd.DataFrame) -> pd.DataFrame:
        return FieldMapper(self.config).transform(df)

    def _step_reference(self, df: pd.DataFrame) -> pd.DataFrame:
        if not self.config.references:
            return df
        return ReferenceManager(self.config.references).apply(df)

    def _step_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        agg_cfg = self.config.aggregation
        if not agg_cfg:
            return df
        return Aggregator(agg_cfg).run(df)

    def _step_output(self, df: pd.DataFrame) -> None:
        output_cfg = self.config.output
        if not output_cfg or not output_cfg.get("path"):
            return
        writer = get_writer(output_cfg)
        writer.write(df, output_cfg)
        logger.info(
            "[%s] 输出完成: %s",
            self.config.platform,
            output_cfg.get("path"),
        )

    # ------------------------------------------------------------------ #
    #  分步运行（方便调试 / 单元测试）
    # ------------------------------------------------------------------ #

    def load(self) -> pd.DataFrame:
        return self._step_load()

    def filter(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._step_filter(df)

    def map(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._step_map(df)

    def reference(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._step_reference(df)

    def aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        return self._step_aggregate(df)


# 补充类型注解
from typing import Any
