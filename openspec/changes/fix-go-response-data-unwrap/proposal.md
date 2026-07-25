## Why

GoFrame 兄弟仓 HTTP 响应统一为 `{ "code", "message", "data": { ... } }`。Python `HttpClient` 把整段 JSON 根对象误当成业务 `data`，对事件字典等接口执行 `response.json().get("list", [])`，在根上取不到 `list` 时静默得到空列表。实际接口已返回 `data.list` 有数据，导致启动时「喂养事件向量库为空 / 事件字典为空」并跳过初始化。

## What Changes

- 统一从 Go 标准包装中解包：先取响应根的 `data`，再取业务字段（如 `list`）
- 修正 `get_event_dictionary`、`get_history_events`、`get_filtered_history_events` 的列表解析
- 修正 `get_baby_profile`：从根 JSON 改为返回 `data` 对象（生日等字段在 `data` 内）
- 抽取可复用的解包辅助函数，避免各方法再写错层级
- 同步修正 `align-python-http-api-with-go` 等相关表述中「`data["list"]`」易误解之处（以本 change spec 为准）

## Capabilities

### New Capabilities

- `go-http-response-unwrap`: 约定 Python 调用兄弟仓时如何解包 GoFrame `{code,message,data}` 响应并提取业务载荷

### Modified Capabilities

- （无）`openspec/specs/` 下暂无已归档能力；进行中的 `align-python-http-api-with-go` 路径对齐保留，解析层级以本 change 纠正

## Impact

- **代码**：`app/shared/http_client.py`（及依赖事件字典/历史/画像的启动预热与业务路径）
- **行为**：事件字典可正确填充 → 喂养事件向量库可初始化；历史/筛选/生日解析不再误空
- **不受影响**：Go 侧接口路径与响应格式；Python 对外 HTTP API
