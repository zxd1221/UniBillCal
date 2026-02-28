"""
统一账单数据模型 - 系统核心输出的标准格式

所有平台经过标准化处理后，数据必须符合此结构。
这是系统的核心契约：Mapper 层输出它，Processor 层消费它。
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


# ────────────────────────────────────────────────────────────
#  统一标准字段定义（字段顺序即为最终输出列顺序）
# ────────────────────────────────────────────────────────────
UNIFIED_FIELDS: list[str] = [
    "business_date",  # 业务日期（date 类型）
    "platform",       # 来源平台（自动注入）
    "store_name",     # 店铺名称
    "category",       # 类目（来自公共类目映射表）
    "subject",        # 科目（来自公共科目映射表）
    "amount",         # 标准金额（业务处理后，正负已规范化）
    "raw_amount",     # 原始金额（公式计算结果，未经业务加工）
    "order_no",       # 订单号（可选）
    "source_type",    # 数据来源类型（自动注入：excel / sqlserver）
    "source_id",      # 原始记录唯一标识（用于追溯）
]

# Mapper 输出时必须包含的最小字段集
REQUIRED_UNIFIED_FIELDS: list[str] = [
    "business_date",
    "platform",
    "store_name",
    "amount",
    "raw_amount",
    "source_type",
    "source_id",
]


@dataclass
class UnifiedBill:
    """统一账单记录（用于类型提示；系统内部以 DataFrame 传输）"""
    business_date: date
    platform: str
    store_name: str
    amount: Decimal
    raw_amount: Decimal
    source_type: str              # excel / sqlserver
    source_id: str                # 原始记录唯一标识
    order_no: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "business_date": self.business_date,
            "platform": self.platform,
            "store_name": self.store_name,
            "category": self.category,
            "subject": self.subject,
            "amount": float(self.amount),
            "raw_amount": float(self.raw_amount),
            "order_no": self.order_no,
            "source_type": self.source_type,
            "source_id": self.source_id,
            **self.extra,
        }
