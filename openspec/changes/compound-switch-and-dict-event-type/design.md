## Context

Python 意图路径已能把 `events[]` 打进一次 Go batch；`action=end` 会映射为 `item_op=end`。Go 按 `eventId` 结束该叶子最近一条进行中记录，Python 不必查进行中、不必填 `history_id`。

缺口在分类与落库前改写：

- 提示未教「不 X 了改 Y」拆成 end + start；多事件确认写成「记录 A、B」，会把停爬当成再记一条爬练习。
- create 默认 `endTime=0`，一次性/计数会被当成计时进行中。
- ASR 同音（怕/爬、做/坐、该/改）无提示。分类前注入进行中摘要已否决（无限补丁）。

约束：经 HTTP 调兄弟仓；`feeding` 不得导入 `clinic`；中文注释；不写测试。类型以字典 `event_type`（`one|time|number`）为准，不由 LLM 返回。

## Goals / Non-Goals

**Goals:**

- 复合句拆到 `events[]`，每件自带 `action`（end 与 start/one 分开）。
- 结束计时只交叶子 id + `action=end`；Go 补最近一条结束时间。
- 同音靠分类提示；偶发认错可接受。
- 多事件确认点出每件名称与动作。
- 落库前按字典类型盖时间：非 `time` 则 `endTime = startTime`；`time` + start 才 `endTime=0`。
- batch 先 end 后 create。

**Non-Goals:**

- 不向分类注入进行中历史或探针。
- 不在 Python 侧查 latest / 填 `history_id` 来结束计时。
- 不改查记录模板、父消歧、意图缓存飞轮。
- 不改 Go end-latest 实现、clinic/tip。
- 不生成测试文件。

## Decisions

### 1. 复合句由分类拆 `events[]`，不靠进行中摘要

- **选择**：提示增加规则：不 X 了 / 改 Y 了 / 换成 / 现在不…了 → 按子句拆，每件填字典叶子 id 与对应 `action`（先 end 后 start/one）。顶层 `action=multi`，`op=create`。不注入当前进行中列表。
- **原因**：Go 已能按 id 结束最近一条；Python 只要拆对 id 和 action。进行中摘要会随口误种类无限打补丁。
- **备选否决**：分类前拉进行中再塞进 prompt — 用户否决。

### 2. 同音只写提示，失败可接受

- **选择**：提示写明常见同音应对字典真名（怕≈爬、做≈坐、该≈改）；对上再填 id，对不上 `missing_events` 或闲聊，禁止发明「怕练习」。不做拼音匹配器。
- **原因**：ASR 错字种类开放；规则引擎覆盖不全。偶发当闲聊优于乱记。
- **备选否决**：拼音/编辑距离自动改写 — 误伤真词（怕黑、该吃药）。

### 3. 结束计时：只交 `eventId + action=end`

- **选择**：`collect_event_items` 对 `action=end` 继续 `op=end`，`id`（history_id）保持 0。MUST NOT 为 end 调 filter/latest。
- **原因**：Go 已实现按事件结束最近一条。
- **备选否决**：Python 先查进行中再带 history_id — 与 Go 重复且多一次往返。

### 4. 类型只认字典，落库前盖时间

- **选择**：叶子表提示可带 `type=one|time|number`，仅帮模型选 start/end/one。写库前用字典 `event_type` 覆盖，忽略 LLM 的 `event_type`。

| 字典类型 | 子项 action | 发给 Go |
|---|---|---|
| `time` + `end` | 保留 | `op=end`，`eventId`，不填 history_id |
| `time` + 非 end | 视为开始 | `create`，`endTime=0` |
| `one` / `number` | 一律当瞬时 | `create`，`endTime = startTime`（即使模型写了 start/end） |

- **原因**：非计时 `endTime=0` 会被当成进行中计时。
- **备选否决**：让模型返回 `event_type` — 会把一次性记成计时。

### 5. 确认话术带动作；batch 先 end

- **选择**：多事件由 Python 覆盖 LLM 确认句，按子项 action 拼：结束「爬练习」并开始「坐练习」。`end` 映射「结束」，`start` 映射「开始」，其余「记录」。提交 batch 前把 `op=end` 排到 `create` 前面。
- **原因**：现句「记录以下事件：爬练习、坐练习」会让用户以为再记一条爬。先 end 后 create 避免短暂双开。
- **备选否决**：沿用只列名称的确认句。

## Risks / Trade-offs

- [同音仍拆错] → 接受偶发闲聊/确认点错名；用户取消即可。不为此加进行中探针。
- [模型把 end+start 揉成两条 one] → 提示写死每件自带 action；确认句暴露动作便于用户否决。
- [字典缺 `event_type`] → 按非 `time` 处理（`endTime=startTime`），避免误开计时。
- [time 事件被说成「记录一次」] → 按上表走 start（进行中），不擅自瞬时结束。

## Migration Plan

1. 只发 Python 镜像；Go 契约不变。
2. 回滚：回退镜像；旧 batch 仍可用，非计时可能再出现 `endTime=0`。

## Open Questions

- （无。计时被说成「记录一次」按 Decision 4 走 start。）
