"""
UniBillCal - 多平台账单统一处理框架

架构说明：
  Layer 1 - 标准化（配置驱动，每平台一个 YAML）：
    BillNormalizer 将平台原始数据 → 统一格式 DataFrame

  Layer 2 - 统一处理（代码驱动，所有平台共用）：
    UnifiedProcessor 关联配置表 + 汇总计算 → 最终输出

新增平台：添加一个 YAML 配置文件即可，无需修改任何代码。
调整业务逻辑：修改 UnifiedProcessor（processor.py）中的方法。
"""

from .core.pipeline import BillPipeline
from .core.normalizer import BillNormalizer
from .core.processor import UnifiedProcessor
from .core.config_loader import PlatformConfig
from .core.processing_config import ProcessingConfig

__all__ = [
    "BillPipeline",
    "BillNormalizer",
    "UnifiedProcessor",
    "PlatformConfig",
    "ProcessingConfig",
]
__version__ = "1.1.0"
