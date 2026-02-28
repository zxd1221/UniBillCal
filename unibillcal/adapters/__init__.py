from .base import BaseAdapter
from .excel_adapter import ExcelAdapter
from .sqlserver_adapter import SqlServerAdapter

ADAPTER_REGISTRY: dict[str, type[BaseAdapter]] = {
    "excel": ExcelAdapter,
    "sqlserver": SqlServerAdapter,
}


def get_adapter(source_type: str) -> type[BaseAdapter]:
    adapter_cls = ADAPTER_REGISTRY.get(source_type.lower())
    if adapter_cls is None:
        raise ValueError(
            f"未知数据源类型: {source_type!r}，"
            f"支持的类型: {list(ADAPTER_REGISTRY)}"
        )
    return adapter_cls


__all__ = ["BaseAdapter", "ExcelAdapter", "SqlServerAdapter", "get_adapter"]
