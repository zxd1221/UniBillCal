"""
金蝶凭证格式 Writer

将统一账单 DataFrame 转换为金蝶导入所需的凭证格式，
并写出为 Excel 文件（金蝶标准导入模板格式）。

金蝶凭证的核心字段（可根据实际版本调整）:
  - 凭证类型 (VoucherType)
  - 凭证日期 (VoucherDate)
  - 摘要     (Summary)
  - 科目代码 (AccountCode)
  - 借方金额 (Debit)
  - 贷方金额 (Credit)
  - 辅助核算 (AuxAccounting)
"""

from pathlib import Path
import pandas as pd
from .base import BaseWriter


# 金蝶标准导入模板列名（可在 output 配置中覆盖）
DEFAULT_KINGDEE_COLUMNS = {
    "voucher_type": "凭证类型",
    "voucher_date": "凭证日期",
    "summary": "摘要",
    "account_code": "科目代码",
    "debit": "借方金额",
    "credit": "贷方金额",
    "currency": "币别",
    "department": "部门",
    "auxiliary": "辅助核算",
}


class KingdeeWriter(BaseWriter):
    """
    生成金蝶标准凭证导入文件。

    output 配置示例:
      format: kingdee
      path: output/alipay_voucher.xlsx
      sheet: 凭证导入
      voucher_type: 记账凭证         # 凭证类型，默认"记账凭证"
      debit_subject: 1122            # 借方科目代码（应收账款）
      credit_subject: 6001           # 贷方科目代码（主营业务收入）
      summary_template: "{store} {date} 销售收入"   # 摘要模板
      currency: RMB                  # 币别，默认 RMB
      column_mapping:                # 可选，覆盖默认金蝶列名
        voucher_date: "业务日期"
    """

    def write(self, df: pd.DataFrame, output_config: dict) -> None:
        path = output_config.get("path")
        if not path:
            raise ValueError("output 配置缺少 'path'")

        Path(path).parent.mkdir(parents=True, exist_ok=True)

        vouchers = self._build_vouchers(df, output_config)
        sheet = output_config.get("sheet", "凭证导入")

        with pd.ExcelWriter(path, engine="openpyxl") as writer:
            vouchers.to_excel(writer, sheet_name=sheet, index=False)

    def _build_vouchers(self, df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
        """将统一账单 DataFrame 转换为金蝶凭证行"""
        col_map = {**DEFAULT_KINGDEE_COLUMNS, **cfg.get("column_mapping", {})}
        voucher_type = cfg.get("voucher_type", "记账凭证")
        debit_subject = cfg.get("debit_subject", "")
        credit_subject = cfg.get("credit_subject", "")
        summary_tpl = cfg.get("summary_template", "{store} {date}")
        currency = cfg.get("currency", "RMB")

        rows = []
        for _, row in df.iterrows():
            summary = self._render_summary(summary_tpl, row)
            date_val = row.get("date", "")
            amount = float(row.get("amount", 0))

            # 借方凭证行
            rows.append({
                col_map["voucher_type"]: voucher_type,
                col_map["voucher_date"]: date_val,
                col_map["summary"]: summary,
                col_map["account_code"]: debit_subject or row.get("subject", ""),
                col_map["debit"]: amount if amount > 0 else 0,
                col_map["credit"]: 0,
                col_map["currency"]: currency,
                col_map.get("department", "部门"): row.get("store", ""),
                col_map.get("auxiliary", "辅助核算"): row.get("category", ""),
            })

            # 贷方凭证行
            rows.append({
                col_map["voucher_type"]: voucher_type,
                col_map["voucher_date"]: date_val,
                col_map["summary"]: summary,
                col_map["account_code"]: credit_subject or row.get("subject", ""),
                col_map["debit"]: 0,
                col_map["credit"]: abs(amount),
                col_map["currency"]: currency,
                col_map.get("department", "部门"): row.get("store", ""),
                col_map.get("auxiliary", "辅助核算"): row.get("category", ""),
            })

        return pd.DataFrame(rows)

    def _render_summary(self, template: str, row: pd.Series) -> str:
        """用行数据渲染摘要模板"""
        try:
            return template.format(**row.to_dict())
        except (KeyError, ValueError):
            return template
