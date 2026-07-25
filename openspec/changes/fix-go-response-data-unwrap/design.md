## Context

已确认 history-service `GET /device/history/api/event/options` 实际响应为：

```json
{ "code": 0, "message": "", "data": { "list": [ /* events */ ] } }
```

`HttpClient.get_event_dictionary` 使用 `response.json().get("list", [])`，在根对象取 `list` 得到 `[]`，启动预热日志「获取到的事件字典为空」。同文件内 `get_history_events`、`get_filtered_history_events` 存在相同模式；`get_baby_profile` 直接返回整段 JSON，生日字段同样应在 `data` 内。

## Goals / Non-Goals

**Goals:**

- 所有兄弟仓 GoFrame 包装响应统一先解包 `data`
- 事件字典解析正确，启动可初始化喂养事件向量库（在其它条件满足时）
- 历史列表 / 筛选 / 宝宝画像解析与真实响应一致

**Non-Goals:**

- 不修改 Go 响应格式或路径
- 不改变事件字段 camelCase→snake_case 映射规则（仅修正取列表的层级）
- 不在本 change 处理 OOM / 自动构建向量库策略
- 不强制编写自动测试文件（遵循项目约束）

## Decisions

### D1: 抽取 `_unwrap_go_data(body) -> Any`

**决定**：私有辅助函数：若 `body` 为 `dict` 且含 `data` 键，返回 `body["data"]`；否则返回 `body`（兼容极少数未包装响应）。列表类方法再对解包结果 `.get("list", [])` 或在 `data` 本身已是 list 时直接使用。

**备选**：每个方法手写 `response.json()["data"]["list"]` → 否决，易再漏。

### D2: 列表接口统一路径

**决定**：

```text
body = response.json()
payload = _unwrap_go_data(body)
raw_list = payload.get("list", []) if isinstance(payload, dict) else (payload or [])
```

用于：`get_event_dictionary`、`get_history_events`、`get_filtered_history_events`。

### D3: 宝宝画像返回 `data` 对象

**决定**：`get_baby_profile` 在 200 时返回 `_unwrap_go_data(response.json())`（期望为含 `babyName`/`birthday`/`sex` 的 dict），不再返回带 `code`/`message` 的根对象。

### D4: 不在此变更校验 `code != 0`

**决定**：仍以 HTTP 状态为主；`code != 0` 的业务错误处理可后续增强。当前先修层级，避免范围膨胀。

## Risks / Trade-offs

- [某接口 `data` 直接是 list 而非 `{list:[]}`] → 辅助函数兼容 `payload` 为 list
- [调用方已依赖错误的根结构] → 画像此前若误读根对象本就异常；修正后行为对齐真实契约
- [align-python-http-api-with-go 文案写 `data["list"]`] → 语义澄清为「业务 data 内的 list」，实现以本 change 为准

## Migration Plan

1. 修改 `http_client.py` 并本地重启 uvicorn
2. 确认日志出现「成功获取并缓存事件字典，包含 N 个事件」（N>0）
3. 回滚：恢复旧解析（仅当 Go 改为根级 `list` 时才需要）

## Open Questions

- （无）响应形状已由线上接口确认
