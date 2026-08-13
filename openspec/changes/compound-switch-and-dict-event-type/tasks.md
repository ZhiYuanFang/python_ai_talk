## 1. 分类提示

- [x] 1.1 叶子简表带上字典 `type`（`one|time|number`）；不注入进行中历史
- [x] 1.2 提示增加复合切换规则：不 X 了 / 改 Y / 换成 → `events[]` 每件自带 action（end 与 start/one 分开），顶层 `action=multi`
- [x] 1.3 提示增加同音提醒（怕≈爬、做≈坐、该≈改）；对不上字典则 missing 或闲聊，禁止编造事件名

## 2. 确认话术

- [x] 2.1 多事件确认由 Python 按子项 action 拼句（结束/开始/记录 + 字典名），覆盖「记录以下事件：A、B」
- [x] 2.2 单事件仍用现有开始/结束/记录话术；查记录点名规则不改

## 3. 落库组装

- [x] 3.1 `collect_event_items`：`action=end` 只带叶子 `eventId`，history id 为 0，不查 latest/filter
- [x] 3.2 按字典 `event_type` 盖时间：非 `time`（含缺省）`endTime=startTime`；`time` 且非 end 才允许 `endTime=0`；忽略 LLM 的 `event_type`
- [x] 3.3 提交 batch 前将全部 end 项排到 create 之前
- [x] 3.4 相关改动补全中文注释

## 4. 校验

- [x] 4.1 运行 `openspec validate compound-switch-and-dict-event-type --strict` 并修复规格问题
- [x] 4.2 对照规格手工核对：复合句拆 end+start、确认带动作、非计时 endTime=startTime、end 不填 history_id、不注入进行中
