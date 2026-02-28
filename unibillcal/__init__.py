"""
UniBillCal - 多平台账单统一处理框架
支持从 SQL Server / Excel 读取多平台账单数据，
经字段映射、公式计算、关联配置表、汇总后，
输出统一格式供金蝶凭证生成使用。
"""

from .core.pipeline import BillPipeline
from .core.config_loader import PlatformConfig

__all__ = ["BillPipeline", "PlatformConfig"]
__version__ = "1.0.0"
