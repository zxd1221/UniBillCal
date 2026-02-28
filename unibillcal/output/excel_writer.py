"""Excel 输出 Writer"""

import os
from pathlib import Path
import pandas as pd
from .base import BaseWriter


class ExcelWriter(BaseWriter):
    """
    将统一格式 DataFrame 写出为 Excel 文件。

    output 配置示例:
      format: excel
      path: output/alipay_unified.xlsx
      sheet: 统一账单               # 可选，默认 Sheet1
      columns:                      # 可选，只输出这些列（按顺序）
        - date
        - store
        - category
        - subject
        - amount
      date_format: "%Y-%m-%d"       # 可选
    """

    def write(self, df: pd.DataFrame, output_config: dict) -> None:
        path = output_config.get("path")
        if not path:
            raise ValueError("output 配置缺少 'path'")

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        sheet = output_config.get("sheet", "统一账单")
        columns = output_config.get("columns")
        date_format = output_config.get("date_format", "%Y-%m-%d")

        out_df = df.copy()
        if columns:
            out_df = out_df[[c for c in columns if c in out_df.columns]]

        with pd.ExcelWriter(path, engine="openpyxl", date_format=date_format) as writer:
            out_df.to_excel(writer, sheet_name=sheet, index=False)
