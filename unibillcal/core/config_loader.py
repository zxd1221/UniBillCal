"""
平台配置加载器 - 负责读取和验证 YAML 配置文件
"""

import os
from pathlib import Path
from typing import Any
import yaml


class PlatformConfig:
    """
    封装单个平台的 YAML 配置，提供类型安全的访问接口。

    YAML 顶层结构:
      platform:       平台标识（如 alipay、wechat）
      description:    描述（可选）
      source:         数据源配置（type、path/connection_string 等）
      filter:         行过滤条件（可选）
      field_mapping:  标准字段 → 源字段 的映射
      amount_formula: 金额计算公式（使用源字段名）
      references:     关联配置表列表（可选）
      aggregation:    汇总规则
      output:         输出配置
    """

    def __init__(self, config: dict):
        self._cfg = config
        self._validate()

    # ------------------------------------------------------------------ #
    #  工厂方法
    # ------------------------------------------------------------------ #

    @classmethod
    def from_file(cls, path: str | Path) -> "PlatformConfig":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        if raw is None:
            raise ValueError(f"配置文件为空: {path}")
        return cls(raw)

    @classmethod
    def from_dict(cls, d: dict) -> "PlatformConfig":
        return cls(d)

    # ------------------------------------------------------------------ #
    #  属性访问
    # ------------------------------------------------------------------ #

    @property
    def platform(self) -> str:
        return self._cfg["platform"]

    @property
    def description(self) -> str:
        return self._cfg.get("description", "")

    @property
    def source(self) -> dict:
        return self._cfg["source"]

    @property
    def filter(self) -> dict | None:
        """行过滤条件，例如: {column: "状态", value: "交易成功"}"""
        return self._cfg.get("filter")

    @property
    def field_mapping(self) -> dict[str, str]:
        """standard_field -> source_column 映射"""
        return self._cfg.get("field_mapping", {})

    @property
    def amount_formula(self) -> str:
        """金额公式，使用源字段名，如 '支付金额 - 退款金额'"""
        return self._cfg.get("amount_formula", "")

    @property
    def references(self) -> list[dict]:
        """关联配置表列表"""
        return self._cfg.get("references", [])

    @property
    def aggregation(self) -> dict:
        return self._cfg.get("aggregation", {})

    @property
    def output(self) -> dict:
        return self._cfg.get("output", {})

    @property
    def extra_fields(self) -> list[str]:
        """额外保留的源字段（不在 field_mapping 中但需要输出）"""
        return self._cfg.get("extra_fields", [])

    def get(self, key: str, default: Any = None) -> Any:
        return self._cfg.get(key, default)

    # ------------------------------------------------------------------ #
    #  内部验证
    # ------------------------------------------------------------------ #

    def _validate(self) -> None:
        required = ["platform", "source", "field_mapping"]
        for key in required:
            if key not in self._cfg:
                raise ValueError(f"配置缺少必要字段: {key!r}")

        if "type" not in self._cfg["source"]:
            raise ValueError("source 配置缺少 'type' 字段（excel 或 sqlserver）")

        if "date" not in self._cfg.get("field_mapping", {}):
            raise ValueError("field_mapping 必须包含 'date' 字段")

        if "amount" not in self._cfg.get("field_mapping", {}) and not self._cfg.get("amount_formula"):
            raise ValueError("必须在 field_mapping 中指定 'amount' 或提供 'amount_formula'")
