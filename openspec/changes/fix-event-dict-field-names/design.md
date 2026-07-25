## Context

事件字典经 `http_client.get_event_dictionary` 归一为 `{event_id, event_name, event_type, unit, extra_names, parent_id}`。意图分类、缓存变化检测、prompt 构建均已使用 `event_id` / `event_name`。唯独 `EventVectorStore.initialize_events` 与 `sync_events` 仍 `event.get("id")` / `event.get("name")`，启动预热时对每个事件打 WARNING「跳过无效事件」，标准向量条目无法写入。

## Goals / Non-Goals

**Goals:**

- 初始化与增量同步能正确读取当前事件字典字段
- 兼容遗留 `id` / `name`（若存在）
- 真正缺字段时 WARNING 可诊断

**Non-Goals:**

- 不改 `http_client` 归一化输出形状
- 不改 Chroma 元数据字段名（写入侧已是 `event_id` / `event_name`）
- 不做全量重建运维脚本（部署后空库会走现有 initialize 路径自动修复；非空库依赖后续 sync 或清库重启）

## Decisions

### 决策 1：在 vector store 读取处做 fallback，而非改 http_client 回退到 id/name

- **选择**：`event.get("event_id") or event.get("id")`（name 同理）
- **理由**：全仓契约已是 `event_id` / `event_name`；改 http_client 会倒退；与 prompt 侧已有 fallback 一致
- **备选**：只读 `event_id`（更干净，但丢失对旧测试夹具的兼容）— 拒绝作为唯一路径

### 决策 2：抽取小型私有解析辅助，避免 initialize / sync 两处漂移

- **选择**：同文件内 `_event_id_name(event) -> (id, name)`（或等价内联两处相同表达式）
- **理由**：`sync_events` 新增/修改分支与 `initialize_events` 有相同 bug
- **备选**：抽到独立 schema 模块 — 对本 bugfix 过重

### 决策 3：真正无效时仍跳过，但日志写明缺字段

- **选择**：`logger.warning("跳过无效事件: missing id/name, event=...")`
- **理由**：避免再次误读为业务数据质量问题

## Risks / Trade-offs

- [已有空标准库的运行实例] → 若集合非空但标准条目本就没写进去，`get_event_count()>0` 可能跳过 initialize；需依赖缓存刷新 sync，或清空标准数据后重启。缓解：sync 路径一并修好；必要时运维清 `source=standard` 或整库后重启。
- [event_id 为 int] → `_add_standard_event` 用 f-string 拼 id，int 可用；保持与现网一致即可。

## Migration Plan

1. 部署修复版本
2. 若喂养事件向量库为空：启动预热自动 `initialize_events`，应无「跳过无效」刷屏，并写入标准条目
3. 若库非空但标准数据缺失：等待缓存 TTL 触发 sync，或手动刷新/清标准数据后重启
4. 回滚：回退镜像即可

## Open Questions

- 无。字段契约以 `http_client` 输出为准。
