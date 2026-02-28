from .base import BaseWriter
from .excel_writer import ExcelWriter
from .kingdee_writer import KingdeeWriter
from .sqlserver_writer import SqlServerWriter

# 注册表：通过 output.type 或 output.format 选择 Writer
# - type 字段：标识输出目的地类型（excel / sqlserver）
# - format 字段：kingdee 时使用金蝶格式（覆盖 type 优先级更高）
_WRITER_REGISTRY: dict[str, type[BaseWriter]] = {
    "excel": ExcelWriter,
    "sqlserver": SqlServerWriter,
    "kingdee": KingdeeWriter,
}


def get_writer(output_config: dict) -> BaseWriter:
    """
    根据 output 配置选择合适的 Writer。

    优先使用 format 字段（如 kingdee），其次使用 type 字段（excel / sqlserver）。
    """
    # format 优先（用于指定金蝶等特殊格式）
    key = output_config.get("format") or output_config.get("type", "excel")
    writer_cls = _WRITER_REGISTRY.get(key.lower())
    if writer_cls is None:
        raise ValueError(
            f"未知输出类型/格式: {key!r}，支持: {list(_WRITER_REGISTRY)}"
        )
    return writer_cls()


def register_writer(name: str, writer_cls: type[BaseWriter]) -> None:
    """注册自定义输出 Writer"""
    _WRITER_REGISTRY[name] = writer_cls


__all__ = [
    "BaseWriter", "ExcelWriter", "KingdeeWriter", "SqlServerWriter",
    "get_writer", "register_writer",
]
