"""
BillPipeline - 账单处理总流水线

架构分两层：

  Layer 1: 标准化（每平台一个配置文件，配置驱动，无需改代码）
    BillNormalizer(平台A配置) → 统一格式 DataFrame
    BillNormalizer(平台B配置) → 统一格式 DataFrame
    BillNormalizer(平台C配置) → 统一格式 DataFrame
                ↓ pd.concat
            合并统一 DataFrame

  Layer 2: 统一处理（所有平台共用，业务逻辑在 processor.py 代码中）
    UnifiedProcessor → 关联配置表 → 汇总 → 最终输出
"""

from __future__ import annotations

import logging
from pathlib import Path
import pandas as pd

from .normalizer import BillNormalizer
from .processor import UnifiedProcessor
from .config_loader import PlatformConfig
from .processing_config import ProcessingConfig
from ..output import get_writer

logger = logging.getLogger(__name__)


class BillPipeline:
    """
    多平台账单处理总流水线。

    用法（完整流程）:
        pipeline = BillPipeline(
            platform_configs=[
                PlatformConfig.from_file("config/alipay.yaml"),
                PlatformConfig.from_file("config/wechat.yaml"),
            ],
            processing_config=ProcessingConfig.from_file("config/processing.yaml"),
        )
        result_df = pipeline.run()

    用法（单平台标准化，调试用）:
        normalizer = BillNormalizer(PlatformConfig.from_file("config/alipay.yaml"))
        unified_df = normalizer.normalize()
    """

    def __init__(
        self,
        platform_configs: list[PlatformConfig],
        processing_config: ProcessingConfig | None = None,
    ):
        self.platform_configs = platform_configs
        self.processing_config = processing_config or ProcessingConfig.from_dict({})

    # ------------------------------------------------------------------ #
    #  工厂方法
    # ------------------------------------------------------------------ #

    @classmethod
    def from_files(
        cls,
        platform_config_paths: list[str | Path],
        processing_config_path: str | Path | None = None,
    ) -> "BillPipeline":
        """从文件路径构建流水线"""
        platform_configs = [
            PlatformConfig.from_file(p) for p in platform_config_paths
        ]
        processing_config = (
            ProcessingConfig.from_file(processing_config_path)
            if processing_config_path
            else ProcessingConfig.from_dict({})
        )
        return cls(platform_configs, processing_config)

    @classmethod
    def from_platform_dir(
        cls,
        platform_dir: str | Path,
        processing_config_path: str | Path | None = None,
    ) -> "BillPipeline":
        """扫描目录下所有 *.yaml 文件作为平台配置（排除 processing.yaml）"""
        platform_dir = Path(platform_dir)
        paths = sorted(
            p for p in platform_dir.glob("*.yaml")
            if p.name != "processing.yaml"
        )
        if not paths:
            raise ValueError(f"目录 {platform_dir} 中未找到平台配置文件")
        return cls.from_files(paths, processing_config_path)

    # ------------------------------------------------------------------ #
    #  主流程
    # ------------------------------------------------------------------ #

    def run(
        self,
        source_dfs: dict[str, pd.DataFrame] | None = None,
    ) -> pd.DataFrame:
        """
        执行完整流水线：标准化所有平台 → 合并 → 统一处理 → 输出。

        Args:
            source_dfs: {platform_name: DataFrame}，直接提供原始数据跳过 Load 步骤，
                        主要用于单元测试。

        Returns:
            汇总处理后的 DataFrame。
        """
        # ── Layer 1：标准化各平台 ──────────────────────────────────────
        unified_frames: list[pd.DataFrame] = []
        for cfg in self.platform_configs:
            raw = (source_dfs or {}).get(cfg.platform)
            normalizer = BillNormalizer(cfg)
            unified = normalizer.normalize(source_df=raw)

            # 可选：将单平台标准化结果写到中间输出
            if cfg.output:
                self._write_intermediate(unified, cfg)

            unified_frames.append(unified)

        if not unified_frames:
            raise ValueError("没有平台数据可处理")

        combined = pd.concat(unified_frames, ignore_index=True)
        logger.info("所有平台合并完成，共 %d 行", len(combined))

        # ── Layer 2：统一业务处理 ──────────────────────────────────────
        processor = UnifiedProcessor(self.processing_config)
        result = processor.process(combined)

        # 写出最终结果
        if self.processing_config.output:
            self._write_final(result)

        return result

    # ------------------------------------------------------------------ #
    #  输出
    # ------------------------------------------------------------------ #

    def _write_intermediate(self, df: pd.DataFrame, cfg: PlatformConfig) -> None:
        """写出单平台标准化数据（中间持久化）"""
        output_cfg = cfg.output
        writer = get_writer(output_cfg)
        writer.write(df, output_cfg)
        logger.info("[%s] 中间数据已写出: %s", cfg.platform, output_cfg.get("path"))

    def _write_final(self, df: pd.DataFrame) -> None:
        """写出最终汇总结果"""
        output_cfg = self.processing_config.output
        writer = get_writer(output_cfg)
        writer.write(df, output_cfg)
        logger.info("最终结果已写出: %s", output_cfg.get("path"))
