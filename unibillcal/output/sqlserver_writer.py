"""SQL Server 输出 Writer"""

import pandas as pd
from .base import BaseWriter


class SqlServerWriter(BaseWriter):
    """
    将 DataFrame 写入 SQL Server 数据库表，支持 append 和 replace 两种模式。

    output 配置示例:
      type: sqlserver
      connection_string: "mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+17+for+SQL+Server"
      table: unified_bills      # 目标表名
      schema: dbo               # 可选，默认 dbo
      mode: append              # append（追加）或 replace（清空后写入）
      chunksize: 1000           # 可选，每批写入行数（大数据量时建议设置）
    """

    def write(self, df: pd.DataFrame, output_config: dict) -> None:
        try:
            from sqlalchemy import create_engine
        except ImportError as e:
            raise ImportError(
                "SQL Server Writer 需要 sqlalchemy 和 pyodbc，"
                "请运行: pip install sqlalchemy pyodbc"
            ) from e

        conn_str = output_config.get("connection_string")
        table = output_config.get("table")

        if not conn_str:
            raise ValueError("SQL Server output 配置缺少 'connection_string'")
        if not table:
            raise ValueError("SQL Server output 配置缺少 'table'")

        schema = output_config.get("schema", "dbo")
        mode = output_config.get("mode", "append")
        chunksize = output_config.get("chunksize", 1000)

        # pandas 的 if_exists 参数：append / replace / fail
        if_exists = "append" if mode == "append" else "replace"

        engine = create_engine(conn_str)
        df.to_sql(
            name=table,
            con=engine,
            schema=schema,
            if_exists=if_exists,
            index=False,
            chunksize=chunksize,
        )
