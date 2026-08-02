## 1. 时间格式化与最新窗口

- [x] 1.1 实现时间戳→上海时区中文（秒/毫秒判断；relative：分钟前/今天昨天/月日/年；calendar：月日时分）
- [x] 1.2 扩展 `slim_history_events_for_prompt`：写入可读 start/end；按时间降序后取最新 N 条
- [x] 1.3 `clinic_answer`（及 tip/history 共用处）改为使用上述最新窗口，去掉 `[-N:]`

## 2. 汇总场景与提示

- [x] 2.1 扩展 `looks_like_history_query`：最近/总结/变化/趋势/这周/7天等
- [x] 2.2 更新 `data_requirement` 提示：最近 N 天、吃奶多 id、limit 加大
- [x] 2.3 （可选但推荐）按日薄聚合文本注入汇总题；或至少保证窗口内记录足够
- [x] 2.4 更新 `clinic_answer`：点查必须念可读时间；汇总据记录谈变化

## 3. 校验

- [x] 3.1 核对：上次睡眠开始有可读时间；「总结最近7天吃奶变化」非 feeding 且回答有记录依据
