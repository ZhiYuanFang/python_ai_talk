## 1. Dictionary entry normalization

- [x] 1.1 在 `http_client.get_event_dictionary` 将 `id`/`parentId` 映射为字符串 `event_id`/`parent_id`（缺失或 null → `""`，禁止 `"None"`）
- [x] 1.2 确认无其它 HTTP 路径仍把事件字典 ID 以 int 写入 state

## 2. API schemas

- [x] 2.1 将 `TipRequest.event_id` 从 `int` 改为 `str`，必要时加显式 string coercion
- [x] 2.2 复核 `IntentResponse` / `IntentEvent` 的 `event_id: str` 保持不变且能消化字典侧字符串 ID

## 3. Data requirement and filter

- [x] 3.1 更新 `data_requirement` prompt 示例为字符串 ID（如 `["1","2"]`）
- [x] 3.2 将 `judge_data_requirement` 解析与 `_extract_valid_event_ids` 改为 `List[str]`，membership 在字符串空间比较
- [x] 3.3 将 `get_filtered_history_events` 参数类型改为 `Optional[List[str]]`，保留逗号拼接出站

## 4. Vector store and cache

- [x] 4.1 在 `_resolve_event_id_name`（及写入 metadata 路径）对解析出的 `event_id` 强制 `str`
- [x] 4.2 确认 `event_cache` 差集/映射在字典已归一后按字符串比较；同步删除列表保持 `List[str]`

## 5. Verification

- [x] 5.1 全仓检索 `event_id: int` / `List[int]` 与强制 `int(eid)`，清理残留
- [x] 5.2 回归：字典加载、intent 单/多事件、tip stream、clinic/history 按 event_ids 筛选
