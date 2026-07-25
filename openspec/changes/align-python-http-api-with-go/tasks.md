## 1. Python 侧修复事件字典接口

- [x] 1.1 将 `get_event_dictionary()` 的请求路径改为 `GET /device/history/api/event/options`
- [x] 1.2 解析响应时从 `data["list"]` 提取列表（而非直接返回 response.json()）
- [x] 1.3 将每个事件的 camelCase 字段转换为 snake_case（`id`→`event_id`、`name`→`event_name`、`parentId`→`parent_id`，保留 `extraNames`、`unit`、`eventType`）

## 2. Python 侧修复全量历史接口

- [x] 2.1 将 `get_history_events()` 的请求路径改为 `GET /device/history/api/list`
- [x] 2.2 参数全部以 query 方式传递（`deviceNo`、`startTime`、`endTime`、`limit`）
- [x] 2.3 解析响应时从 `data["list"]` 提取历史列表

## 3. Python 侧修复筛选历史接口

- [x] 3.1 将 `get_filtered_history_events()` 的请求路径改为 `GET /device/history/api/filter`（已是正确路径）
- [x] 3.2 `event_ids` 列表转为逗号分隔字符串，作为 query 参数 `eventIds` 传递（已实现）
- [x] 3.3 解析响应时从 `data["list"]` 提取历史列表（已实现）
- [x] 3.4 验证降级逻辑（filter 失败时自动回退到全量 list + 本地过滤）仍然有效

## 4. Python 侧修复宝宝画像接口

- [x] 4.1 将 `get_baby_profile()` 的请求路径改为 `GET /device/history/api/birthday`
- [x] 4.2 `device_no` 改为 query 参数 `deviceNo`（不再用 path）
- [x] 4.3 保持 404 返回 None、其他错误抛出异常的逻辑不变

## 5. Go 侧新增历史筛选接口（在 go_ai_talk 项目中）

- [ ] 5.1 在 `api/v1/device_history_http.go` 新增 `DeviceHistoryFilterReq` / `DeviceHistoryFilterRes` 结构体，路径 `GET /device/history/api/filter`
- [ ] 5.2 在 `internal/services/history/` 新增 `ListHistoryFilter` 方法，支持 deviceNo、eventIds（多ID逗号分隔）、startTime、endTime、limit 参数
- [ ] 5.3 在 controller 层注册 filter 接口路由
- [ ] 5.4 eventIds 为空时跳过事件ID过滤，startTime/endTime 为空时跳过对应时间条件
- [ ] 5.5 结果按 startTime 倒序，limit 默认 100

## 6. Go 侧扩展全量历史接口（在 go_ai_talk 项目中）

- [ ] 6.1 扩展 `DeviceHistoryListReq`，增加 `StartTime`、`EndTime`、`Limit` 可选字段
- [ ] 6.2 在 `ListHistoryPage` 或新增方法中实现时间范围和 limit 支持
- [ ] 6.3 不传新参数时保持原有分页行为不变（向后兼容）
- [ ] 6.4 传了 limit 时优先使用 limit（替代 pageSize）

## 7. 验证测试

- [x] 7.1 Python 侧所有修改文件语法检查通过
- [x] 7.2 全局搜索确认所有旧路径引用已更新
- [x] 7.3 验证事件字典接口返回格式转换正确（代码审阅确认字段映射正确）
- [x] 7.4 验证 filter 降级逻辑仍然有效（fetch_history.py 中 try/except 降级逻辑保持不变）
