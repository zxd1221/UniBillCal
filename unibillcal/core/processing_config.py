"""
统一处理配置加载器

ProcessingConfig 对应 processing.yaml，包含：
  - references: 公共配置表（类目映射、科目映射等），所有平台共用
  - output:     最终输出位置（Excel 或 SQL Server）

注意：汇总逻辑（分组字段、求和字段等）不在此处——在 UnifiedProcessor 代码中。
"""

from __future__ import annotations

from pathlib import Path
import yaml


class ProcessingConfig:
    """
    统一处理阶段的配置。

    YAML 结构:
      references:               # 公共配置表列表（类目/科目映射等）
        - name: category_mapping
          source:
            type: excel         # 或 sqlserver
            path: config/category_map.xlsx
          join_on:
            left: store         # 统一格式中的字段名
            right: 商家名称     # 配置表中的字段名
          fields:
            category: 类目名称  # 目标字段: 配置表列名
            subject: 科目代码

      output:                   # 最终输出（汇总后的结果）
        type: excel             # 或 sqlserver
        path: output/result.xlsx
        format: unified         # unified（统一格式）或 kingdee（金蝶凭证）
        sheet: 汇总结果
        mode: overwrite         # overwrite 或 append
    """

    def __init__(self, config: dict):
        self._cfg = config

    @classmethod
    def from_file(cls, path: str | Path) -> "ProcessingConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"处理配置文件不存在: {path}")
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
        return cls(raw)

    @classmethod
    def from_dict(cls, d: dict) -> "ProcessingConfig":
        return cls(d)

    @property
    def references(self) -> list[dict]:
        """公共配置表列表（类目/科目映射等）"""
        return self._cfg.get("references", [])

    @property
    def output(self) -> dict:
        return self._cfg.get("output", {})
