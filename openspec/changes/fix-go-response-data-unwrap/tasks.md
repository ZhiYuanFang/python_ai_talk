## 1. 解包辅助与列表接口

- [x] 1.1 在 `app/shared/http_client.py` 增加 `_unwrap_go_data`（或等价私有方法），从响应根提取 `data` 载荷
- [x] 1.2 修正 `get_event_dictionary`：从解包后的载荷读取 `list`，再做既有字段映射
- [x] 1.3 修正 `get_history_events` 与 `get_filtered_history_events`：同样从 `data.list` 取列表

## 2. 画像接口

- [x] 2.1 修正 `get_baby_profile`：HTTP 200 时返回解包后的 `data` 对象，而非整段根 JSON

## 3. 验证

- [x] 3.1 本地重启服务，确认启动日志能获取到非空事件字典（或手动调用 `get_event_dictionary` 得到 N>0）
- [x] 3.2 确认不再出现因空字典而「跳过喂养事件向量库初始化」（在事件接口有数据的前提下）
