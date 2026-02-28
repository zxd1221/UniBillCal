# 平台配置文件说明

每个平台对应一个 YAML 配置文件，框架会自动解析并执行处理流水线。

## 配置结构

```yaml
platform: <平台标识>       # 必填，如 alipay / wechat / pinduoduo
description: <描述>        # 可选

source:                    # 必填：数据源
  type: excel | sqlserver
  # Excel:
  path: data/xxx.xlsx
  sheet: Sheet1
  skiprows: 0
  # SQL Server:
  connection_string: "mssql+pyodbc://..."
  table: <表名>            # 与 query 二选一
  query: "SELECT ..."

filter:                    # 可选：行过滤
  column: <列名>
  op: eq | ne | gt | gte | lt | lte | in | not_in | contains
  value: <值>
  # 或多条件（AND）:
  conditions:
    - {column: ..., op: ..., value: ...}

field_mapping:             # 必填：标准字段 -> 源字段
  date: <源列名>           # 必填
  store: <源列名>
  order_id: <源列名>       # 可选
  amount: <源列名>         # 与 amount_formula 二选一
  remark: <源列名>         # 可选

amount_formula: "<算术表达式>"  # 使用源列名，如 "收入 - 退款 + 补贴"

extra_fields:              # 可选：额外保留的原始列
  - <列名>

references:                # 可选：关联配置表列表
  - name: <关联名>
    source:                # 同 source 结构
      type: excel | sqlserver
      ...
    join_on:
      left: <主表字段>     # 已映射后的统一字段名
      right: <配置表字段>
    fields:
      <目标字段>: <配置表列名>

aggregation:               # 可选：汇总规则
  strategy: standard | none | pivot
  group_by: [date, store, category, subject, platform]
  sum_fields: [amount]
  mean_fields: []
  count_field: order_count
  custom_rules:
    <输出列>: {func: sum|mean|max|min, source: <源列>}

output:                    # 可选：输出配置
  format: excel | kingdee
  path: output/xxx.xlsx
  sheet: <Sheet名>
  columns: [...]           # 可选，指定输出列及顺序
  # 金蝶特有配置:
  voucher_type: 记账凭证
  debit_subject: "1122"
  credit_subject: "6001"
  summary_template: "{store} {date} 销售收入"
```

## 新增平台步骤

1. 在 `config/` 目录下新建 `<platform>.yaml` 文件
2. 按上述结构填写配置
3. 运行: `python main.py --platform <platform>`

**无需修改任何核心代码！**
