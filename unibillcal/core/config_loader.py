"""
平台配置加载器

平台配置只负责"数据标准化"：
  - 从哪里读数据（source）
  - 过滤哪些行（filter）
  - 字段怎么映射到统一格式（field_mapping + amount_formula）
  - 标准化结果写到哪里（output，可选）

汇总计算、关联配置表等业务逻辑不在此处——由 UnifiedProcessor 统一处理。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml


class PlatformConfig:
    """
    单个平台的标准化配置。

    YAML 结构（只包含平台特有的内容）:
      platform:       平台标识（如 alipay、wechat）
      description:    描述（可选）
      source:         数据源（type + 位置信息）
      filter:         行过滤条件（可选）
      field_mapping:  统一字段名 -> 源字段名 的映射
                      统一字段名须使用标准名：business_date / store_name / order_no 等
      amount_formula: 金额计算公式（使用源字段名，与 field_mapping.amount 二选一）
      extra_fields:   额外保留的源字段（可选，以原始列名指定）
      output:         标准化结果的中间输出位置（可选）
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
    def output(self) -> dict | None:
        """标准化数据的中间输出（可选）"""
        return self._cfg.get("output")

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

        if "business_date" not in self._cfg.get("field_mapping", {}):
            raise ValueError(
                "field_mapping 必须包含 'business_date' 字段（对应源数据的日期列）"
            )

        has_amount = (
            "amount" in self._cfg.get("field_mapping", {})
            or self._cfg.get("amount_formula")
        )
        if not has_amount:
            raise ValueError(
                "必须在 field_mapping 中指定 'amount' 或提供 'amount_formula'"
            )
