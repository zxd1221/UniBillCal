from .base import BaseWriter
from .excel_writer import ExcelWriter
from .kingdee_writer import KingdeeWriter

_WRITER_REGISTRY: dict[str, type[BaseWriter]] = {
    "excel": ExcelWriter,
    "kingdee": KingdeeWriter,
}


def get_writer(output_config: dict) -> BaseWriter:
    fmt = output_config.get("format", "excel").lower()
    writer_cls = _WRITER_REGISTRY.get(fmt)
    if writer_cls is None:
        raise ValueError(
            f"未知输出格式: {fmt!r}，支持: {list(_WRITER_REGISTRY)}"
        )
    return writer_cls()


def register_writer(name: str, writer_cls: type[BaseWriter]) -> None:
    """注册自定义输出 Writer"""
    _WRITER_REGISTRY[name] = writer_cls


__all__ = ["BaseWriter", "ExcelWriter", "KingdeeWriter", "get_writer", "register_writer"]
