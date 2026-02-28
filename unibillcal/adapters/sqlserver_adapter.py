"""SQL Server 数据源适配器"""

import pandas as pd
from .base import BaseAdapter


class SqlServerAdapter(BaseAdapter):
    """
    从 SQL Server 数据库读取账单数据。

    source_config 示例:
        type: sqlserver
        connection_string: "mssql+pyodbc://user:pass@server/db?driver=ODBC+Driver+17+for+SQL+Server"
        table: bill_alipay      # 直接读取整张表（与 query 二选一）
        query: "SELECT ..."     # 自定义 SQL（优先级高于 table）
        params: {}              # 可选，query 的参数（用于参数化查询）
    """

    def load(self) -> pd.DataFrame:
        try:
            from sqlalchemy import create_engine, text
        except ImportError as e:
            raise ImportError(
                "SQL Server 适配器需要 sqlalchemy 和 pyodbc，"
                "请运行: pip install sqlalchemy pyodbc"
            ) from e

        cfg = self.source_config
        conn_str = cfg.get("connection_string")
        if not conn_str:
            raise ValueError("SQL Server 数据源缺少 'connection_string' 配置")

        engine = create_engine(conn_str)

        query = cfg.get("query")
        table = cfg.get("table")

        if not query and not table:
            raise ValueError("SQL Server 数据源需要指定 'query' 或 'table'")

        sql = query if query else f"SELECT * FROM [{table}]"
        params = cfg.get("params") or {}

        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn, params=params)

        df.columns = [str(c).strip() for c in df.columns]
        return df
