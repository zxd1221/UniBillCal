"""
字段映射器（FieldMapper）

职责：将平台原始 DataFrame → 统一标准格式 DataFrame

此层只做结构转换，不包含任何业务规则：
  1. 字段重命名（按 field_mapping 配置）
  2. 金额公式计算（raw_amount = formula 结果；amount = raw_amount 初始值）
  3. 基础数据清洗（日期解析、空值处理）
  4. 自动注入元数据字段（platform / source_type / source_id）

统一字段名（配置中的 key）对应 UNIFIED_FIELDS：
  business_date / store_name / order_no / ...
"""

import pandas as pd
from .formula import apply_formula
from .config_loader import PlatformConfig
from ..models.unified import UNIFIED_FIELDS

# 必填的映射字段（配置中必须包含）
_REQUIRED_MAPPING_KEYS = {"business_date"}


class FieldMapper:
    """
    根据 PlatformConfig 将原始 DataFrame 转换为统一格式。

    配置示例（YAML field_mapping 节）:
        business_date: 交易时间      # 统一字段名: 源列名
        store_name:    商家名称
        order_no:      商户订单号     # 可选
    """

    def __init__(self, config: PlatformConfig):
        self.config = config

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        执行映射，返回统一格式 DataFrame。

        新增字段说明：
          raw_amount  - 金额公式的直接计算结果
          amount      - 初始值与 raw_amount 相同，Processor 可按业务规则调整
          source_type - 自动从 config.source.type 注入
          source_id   - 优先用 order_no，否则自动生成 "{platform}_{index}"
        """
        df = df.copy()
        mapping: dict[str, str] = self.config.field_mapping  # unified_key -> source_col
        result = pd.DataFrame(index=df.index)

        # ── 1. 金额计算 ────────────────────────────────────────────────
        raw_amount = self._compute_raw_amount(df, mapping)
        result["raw_amount"] = raw_amount
        result["amount"] = raw_amount  # Processor 可按需调整 amount

        # ── 2. 映射其他标准字段 ────────────────────────────────────────
        for std_key, src_col in mapping.items():
            if std_key in ("amount", "raw_amount"):
                continue  # 已处理
            if src_col not in df.columns:
                if std_key in _REQUIRED_MAPPING_KEYS:
                    raise ValueError(
                        f"平台 {self.config.platform!r}: "
                        f"字段 '{std_key}' 映射的源列 '{src_col}' 不存在，"
                        f"实际列: {list(df.columns)}"
                    )
                result[std_key] = None
            else:
                result[std_key] = df[src_col]

        # ── 3. 日期标准化 ──────────────────────────────────────────────
        if "business_date" in result.columns:
            result["business_date"] = (
                pd.to_datetime(result["business_date"], errors="coerce").dt.date
            )

        # ── 4. 字符串列去首尾空格 ─────────────────────────────────────
        str_cols = result.select_dtypes(include="object").columns
        for col in str_cols:
            result[col] = result[col].apply(
                lambda v: v.strip() if isinstance(v, str) else v
            )

        # ── 5. 自动注入元数据 ──────────────────────────────────────────
        result["platform"] = self.config.platform
        result["source_type"] = self.config.source.get("type", "unknown")
        result["source_id"] = self._build_source_id(df, result, mapping)

        # ── 6. 保留额外字段 ────────────────────────────────────────────
        for col in self.config.extra_fields:
            if col in df.columns:
                result[col] = df[col]

        return result

    # ------------------------------------------------------------------ #
    #  内部方法
    # ------------------------------------------------------------------ #

    def _compute_raw_amount(
        self, df: pd.DataFrame, mapping: dict[str, str]
    ) -> pd.Series:
        """计算原始金额（公式或直接映射）"""
        if self.config.amount_formula:
            return apply_formula(df, self.config.amount_formula)

        if "amount" in mapping:
            src_col = mapping["amount"]
            if src_col not in df.columns:
                raise ValueError(
                    f"平台 {self.config.platform!r}: "
                    f"amount 映射的源列 '{src_col}' 不存在"
                )
            return pd.to_numeric(df[src_col], errors="coerce").fillna(0)

        raise ValueError(
            f"平台 {self.config.platform!r}: "
            "必须在 field_mapping 中指定 'amount' 或提供 'amount_formula'"
        )

    def _build_source_id(
        self,
        raw_df: pd.DataFrame,
        result: pd.DataFrame,
        mapping: dict[str, str],
    ) -> pd.Series:
        """
        构建原始记录唯一标识。

        优先级：
          1. field_mapping 中明确映射了 source_id → 使用对应源列值
          2. order_no 已映射 → "{platform}_{order_no}"
          3. 兜底 → "{platform}_{行索引}"
        """
        platform = self.config.platform

        # 优先级 1：显式映射
        if "source_id" in mapping and mapping["source_id"] in raw_df.columns:
            return raw_df[mapping["source_id"]].astype(str)

        # 优先级 2：用 order_no
        if "order_no" in result.columns and result["order_no"].notna().any():
            return platform + "_" + result["order_no"].fillna("").astype(str)

        # 兜底：行索引
        return pd.Series(
            [f"{platform}_{i}" for i in range(len(result))],
            index=result.index,
        )
