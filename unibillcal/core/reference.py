"""
关联配置表管理器 - 负责加载公共配置表（类目映射、科目映射等）
并与账单数据进行 LEFT JOIN
"""

import pandas as pd
from ..adapters import get_adapter


class ReferenceManager:
    """
    根据配置中的 references 列表，依次对 DataFrame 执行 LEFT JOIN。

    references 配置示例:
      - name: category_mapping        # 关联名（用于日志）
        source:
          type: excel
          path: config/category_map.xlsx
          sheet: Sheet1
        join_on:
          left: store                  # 主表字段（已映射后的字段名）
          right: store_name            # 配置表字段名
        fields:                        # 从配置表中取出的字段
          category: category_name      # 目标字段: 配置表列名
          subject: subject_code

      - name: subject_mapping
        source:
          type: sqlserver
          connection_string: "..."
          table: SubjectMapping
        join_on:
          left: category
          right: category_code
        fields:
          subject: subject_name
    """

    def __init__(self, references_config: list[dict]):
        self.references_config = references_config
        self._cache: dict[str, pd.DataFrame] = {}

    def apply(self, df: pd.DataFrame) -> pd.DataFrame:
        """依次应用所有关联表，返回丰富后的 DataFrame"""
        for ref_cfg in self.references_config:
            df = self._apply_one(df, ref_cfg)
        return df

    def _apply_one(self, df: pd.DataFrame, ref_cfg: dict) -> pd.DataFrame:
        name = ref_cfg.get("name", "unnamed_reference")
        source_cfg = ref_cfg["source"]
        join_on = ref_cfg["join_on"]
        field_map = ref_cfg.get("fields", {})  # target_field: source_col

        # 加载关联表（带缓存，同一个源不重复加载）
        cache_key = f"{source_cfg.get('type')}:{source_cfg.get('path') or source_cfg.get('table')}"
        if cache_key not in self._cache:
            adapter_cls = get_adapter(source_cfg["type"])
            ref_df = adapter_cls(source_cfg).load()
            self._cache[cache_key] = ref_df
        else:
            ref_df = self._cache[cache_key]

        left_col = join_on["left"]
        right_col = join_on["right"]

        if left_col not in df.columns:
            raise ValueError(
                f"关联 {name!r}: 主表缺少 join 字段 '{left_col}'，"
                f"可用字段: {list(df.columns)}"
            )
        if right_col not in ref_df.columns:
            raise ValueError(
                f"关联 {name!r}: 配置表缺少 join 字段 '{right_col}'，"
                f"可用字段: {list(ref_df.columns)}"
            )

        # 只取需要的列，避免列名冲突
        needed_cols = [right_col] + [
            src for src in field_map.values() if src != right_col
        ]
        needed_cols = [c for c in needed_cols if c in ref_df.columns]
        ref_subset = ref_df[list(dict.fromkeys(needed_cols))].drop_duplicates(
            subset=[right_col]
        )

        # LEFT JOIN
        df = df.merge(
            ref_subset,
            left_on=left_col,
            right_on=right_col,
            how="left",
            suffixes=("", f"_{name}"),
        )

        # 重命名从配置表取出的字段
        rename_map = {}
        for target_field, src_col in field_map.items():
            if src_col in df.columns:
                rename_map[src_col] = target_field
            elif f"{src_col}_{name}" in df.columns:
                rename_map[f"{src_col}_{name}"] = target_field

        if rename_map:
            df = df.rename(columns=rename_map)

        # 如果 right_col != left_col，删除多余的 join key 列
        if right_col != left_col and right_col in df.columns and right_col not in rename_map.values():
            df = df.drop(columns=[right_col], errors="ignore")

        return df
