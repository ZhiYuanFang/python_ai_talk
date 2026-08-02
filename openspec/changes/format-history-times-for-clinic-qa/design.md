## Context

查记录已走 clinic agent + 字段裁剪，但时间戳原样进 prompt，回答常无具体时间。列表按 startTime 倒序时 `slim[-20:]` 取最旧。汇总问法（最近7天吃奶变化）需要更大窗口与不同提示，门禁词表也要覆盖「总结/最近N天」。

## Goals / Non-Goals

**Goals:**

- Python 将 start/end 转为上海时区可读中文后再注入
- 点查：相对时间 + 日/月/年最小规格
- 注入取最新 N 条（倒序列表用 `[:N]`）
- 汇总题：门禁、data_requirement、提示与可选按日聚合
- clinic_answer 强制念可读时间 / 据记录总结

**Non-Goals:**

- 不改 Go history API 契约
- 不做完整统计分析引擎（薄聚合即可）
- 不强制修 filter 请求秒/毫秒不一致（可另开；本 change 只保证展示侧判秒/毫秒）

## Decisions

### 1. 格式化落在 `slim_history_events_for_prompt`（或紧邻 helper）

- **选择**：裁剪后把 `startTime`/`endTime` 写成可读字符串（覆盖原数字字段）
- **理由**：clinic/tip/history_answer 共用一处；模型只见人话
- **秒/毫秒**：数值 `> 1e12` 视为毫秒，否则秒

### 2. 点查文案规则（style=relative）

相对「现在」Asia/Shanghai：

| 距今 | 输出 |
|------|------|
| &lt; 1 分钟 | `刚刚` |
| &lt; 1 小时 | `{n}分钟前` |
| &lt; 1 天 | `今天 HH:mm` 或 `昨天 HH:mm`（跨自然日） |
| ≥ 1 天且同年 | `M月D日 HH:mm` |
| 跨年 | `YYYY年M月D日 HH:mm` |

### 3. 汇总明细文案（style=calendar）

- **选择**：同年 `M月D日 HH:mm`，跨年带年；少用「N分钟前」
- **理由**：便于模型做 7 天对比

### 4. 取最新窗口

- **选择**：默认假设 API 新→旧；点查/通用注入用 `[:20]`（或配置 N），删除 `[-20:]`
- **若顺序不确定**：可按解析后的时间戳再 sort 降序后取前 N（更稳，推荐）

### 5. 汇总场景

- **门禁**：扩展 `looks_like_history_query`：最近、总结、变化、趋势、这周、七天/7天 等
- **data_requirement 提示**：识别「最近 N 天」→ `last_7_days` / `last_30_days`；吃奶相关多 event_ids；limit≥50
- **注入**：可选按日聚合（次数、eventNumber 求和）+ 少量明细（calendar 时间）；无聚合时至少给足窗口内最新记录
- **clinic_answer**：增加【汇总题】规则——据记录谈次数/总量是否变化，无数据老实说

### 6. 点查提示

- **选择**：明确「开始时间念 startTime 可读字段，禁止只说大概」

## Risks / Trade-offs

- [列表实际为正序] → 按时间戳重排再取前 N，避免再踩坑
- [聚合字段单位不一] → 按 eventName 分组；无 number 只报次数
- [门禁过宽] → 宁可进 history/clinic 也不误 feeding

## Migration Plan

1. 部署后验：上次睡眠开始有可读时间；7 天吃奶总结有次数/量级依据
2. 回滚：恢复数字时间戳 + 旧切片即可

## Open Questions

- 无（相对规格 + 汇总场景已确认）
