"""Excel 文件数据源适配器"""

import pandas as pd
from .base import BaseAdapter


class ExcelAdapter(BaseAdapter):
    """
    从 Excel 文件读取账单数据。

    source_config 示例:
        type: excel
        path: data/alipay_bills.xlsx
        sheet: Sheet1          # 可选，默认第一个 sheet
        skiprows: 0            # 可选，跳过头部行数
        header_row: 0          # 可选，列名所在行（0-based）
        usecols: null          # 可选，只读取指定列（列名列表）
        dtype: {}              # 可选，强制指定列的数据类型
        na_values: []          # 可选，额外的 NA 值
    """

    def load(self) -> pd.DataFrame:
        cfg = self.source_config
        path = cfg.get("path")
        if not path:
            raise ValueError("Excel 数据源缺少 'path' 配置")

        read_kwargs: dict = {
            "sheet_name": cfg.get("sheet", 0),
            "skiprows": cfg.get("skiprows", 0),
            "header": cfg.get("header_row", 0),
        }

        if cfg.get("usecols"):
            read_kwargs["usecols"] = cfg["usecols"]
        if cfg.get("dtype"):
            read_kwargs["dtype"] = cfg["dtype"]
        if cfg.get("na_values"):
            read_kwargs["na_values"] = cfg["na_values"]

        df = pd.read_excel(path, **read_kwargs)
        # 去除列名和字符串值的首尾空格
        df.columns = [str(c).strip() for c in df.columns]
        str_cols = df.select_dtypes(include="object").columns
        df[str_cols] = df[str_cols].apply(lambda s: s.str.strip() if s.dtype == "object" else s)
        return df
