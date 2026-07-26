## Context

Python AI 服务从 Go history-service 拉取事件字典时，`id` 为 JSON number（int64），`http_client.get_event_dictionary` 原样写入 `event_id`。下游却按场景混用类型：

- Intent 响应 / 向量库注解：`str`
- Tip 请求：`int`（与 Go `TipStreamRequest.EventID string` 冲突）
- `judge_data_requirement` / filter：`List[int]`

集合差集与 `in` 校验在 `52` vs `"52"` 时会静默出错。本变更在字典入口强制 `str`，并沿链路统一 API 与内部签名。

## Goals / Non-Goals

**Goals:**

- 全仓 `event_id`（含 tip 入站、意图出站、字典条目）权威类型为 `str`
- `event_ids` 列表权威类型为 `List[str]`
- 同源标识 `parent_id` 在字典归一化时一并转 `str`，避免同类漂移
- 比较、缓存、向量元数据、membership 校验均在字符串空间进行
- 调用 Go filter 时继续用逗号分隔字符串传 `eventIds`（行为不变）

**Non-Goals:**

- 不修改 Go history-service 的 DB 列类型或 filter SQL（仍为 int64）
- 不改 Chroma collection 重建；仅保证新写入 metadata 为 str（已有 int 元数据若存在，靠比较前规范化或自然汰换）
- 不引入新外部依赖
- 不改意图业务语义（匹配、确认、多事件逻辑）

## Decisions

### 1. 源头归一：`http_client.get_event_dictionary`

- **选择**：映射时 `event_id = str(item["id"]) if id is not None else ""`（`parent_id` 同理；None 保持空串或省略策略与现网一致）
- **理由**：一处修复，缓存/向量/prompt/意图匹配全部受益
- **备选**：各消费点各自 `str()` — 易漏、重复，拒绝作为主路径

### 2. Tip 与 Intent 契约均为 `str`

- **选择**：`TipRequest.event_id: str`；Intent 侧保持已有 `str`
- **理由**：与 Go tip/intent 客户端字符串字段一致
- **备选**：Tip 继续 int、仅文档说明 — 拒绝（与「全仓 str」冲突）

### 3. `event_ids: List[str]` + 解析宽容

- **选择**：judge 解析与 valid 集合统一 `str`；LLM 返回 number 时 `str(int)` / `str(eid).strip()`；filter 签名 `Optional[List[str]]`，join 不变
- **理由**：prompt 可逐步改为 `["1","2"]`，解析不依赖 LLM 严格输出字符串
- **备选**：内部仍 int、仅 API str — 拒绝（membership 坑仍在）

### 4. 向量 / 缓存防御

- **选择**：`_resolve_event_id_name` 返回值 `str(...)`；cache 差集用已归一字典即可；同步删除 ID 列表类型保持 `List[str]`
- **理由**：入口 + 解析双保险，旧测试夹具带 int 也不会炸

### 5. 出站 Go filter

- **选择**：不在 Python 侧再 `int()`；`",".join(event_ids)` 即可
- **理由**：Go 已按逗号分隔字符串解析为 int64；Python 保持 str 更干净

## Risks / Trade-offs

- [Tip 调用方仍发 JSON number] → Pydantic v2 通常可将 number 强制为 str；加一次 tip 入站回归；必要时 `BeforeValidator` 显式 `str`
- [Chroma 存量 metadata 仍为 int] → where 等值查询可能漏删；`_remove_event_by_id` 路径评估是否需双查或全量扫；短期可接受若字典 ID 稳定且以标准条目重建为主
- [LLM 仍输出数字数组] → 解析侧强制 `str`，prompt 示例同步改字符串降低混淆
- [过度转换空值] → `None` / 缺失不得变成 `"None"`；仅对真实标量做 `str`

## Migration Plan

1. 先改 `http_client` 归一化 + Tip schema + judge/filter 签名
2. 再改 prompt 示例与类型注解
3. 本地/容器回归：事件字典加载、intent 单/多事件、tip stream、clinic/history 筛选
4. 回滚：还原上述文件即可；无 DB migration

## Open Questions

- 无阻塞项。若线上 tip 调用方无法发 string，再加显式 coercion validator（实现阶段按需）。
