"""
统一账单数据模型 - 所有平台数据处理后的标准格式
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Optional


# 统一格式的标准字段列表（用于验证和文档）
UNIFIED_FIELDS = [
    "date",         # 日期
    "store",        # 店铺/商家
    "order_id",     # 订单号（可选）
    "category",     # 类目（来自类目映射表）
    "subject",      # 科目（来自科目映射表）
    "amount",       # 金额（已按公式计算）
    "platform",     # 来源平台
    "remark",       # 备注（可选）
]


@dataclass
class UnifiedBill:
    """统一账单记录"""
    date: date
    store: str
    amount: Decimal
    platform: str
    order_id: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    remark: Optional[str] = None
    # 扩展字段：承载平台特有的额外信息
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "date": self.date,
            "store": self.store,
            "order_id": self.order_id,
            "category": self.category,
            "subject": self.subject,
            "amount": float(self.amount),
            "platform": self.platform,
            "remark": self.remark,
            **self.extra,
        }
