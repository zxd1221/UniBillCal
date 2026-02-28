"""Excel 输出 Writer"""

from pathlib import Path
import pandas as pd
from .base import BaseWriter


class ExcelWriter(BaseWriter):
    """
    将 DataFrame 写出为 Excel 文件，支持 overwrite（默认）和 append 两种模式。

    output 配置示例:
      type: excel
      path: output/unified.xlsx
      sheet: 统一账单          # 可选，默认"统一账单"
      mode: overwrite           # overwrite（默认）或 append
      columns:                  # 可选，只输出这些列（按顺序）
        - date
        - store
        - category
        - subject
        - amount
      date_format: "%Y-%m-%d"   # 可选
    """

    def write(self, df: pd.DataFrame, output_config: dict) -> None:
        path = output_config.get("path")
        if not path:
            raise ValueError("output 配置缺少 'path'")

        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)

        sheet = output_config.get("sheet", "统一账单")
        columns = output_config.get("columns")
        date_format = output_config.get("date_format", "%Y-%m-%d")
        mode = output_config.get("mode", "overwrite")

        out_df = df.copy()
        if columns:
            out_df = out_df[[c for c in columns if c in out_df.columns]]

        if mode == "append" and p.exists():
            # 读取已有数据，追加后整体写回
            existing = pd.read_excel(p, sheet_name=sheet)
            out_df = pd.concat([existing, out_df], ignore_index=True)

        with pd.ExcelWriter(str(p), engine="openpyxl", date_format=date_format) as writer:
            out_df.to_excel(writer, sheet_name=sheet, index=False)
