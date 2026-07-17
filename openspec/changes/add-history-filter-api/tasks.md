# Tasks: 新增历史记录筛选 API 和意图后处理

## 1. Go 侧 - API 模型定义

- [ ] 1.1 在 `internal/model/api/v1/` 中新增 `DeviceHistoryFilterReq` 请求模型（deviceNo, eventIds, startTime, endTime, limit）
- [ ] 1.2 在 `internal/model/api/v1/` 中新增 `DeviceHistoryFilterRes` 响应模型（list 字段）

## 2. Go 侧 - 服务层实现

- [ ] 2.1 在 `internal/services/contracts/` 中新增 `ListHistoryFilter` 方法声明
- [ ] 2.2 在 `internal/services/history/` 中实现 `ListHistoryFilter` 方法，支持多事件ID和时间范围筛选

## 3. Go 侧 - Controller 层

- [ ] 3.1 在 `internal/controller/device_history.go` 中新增 `Filter` 方法
- [ ] 3.2 验证请求参数（deviceNo 必填）
- [ ] 3.3 调用服务层 `ListHistoryFilter` 方法
- [ ] 3.4 返回标准响应格式

## 4. Go 侧 - 测试

- [ ] 4.1 测试正常筛选场景（事件ID + 时间范围）
- [ ] 4.2 测试边界场景（无效设备号、不存在的事件ID）
- [ ] 4.3 测试无参数场景（返回全部记录）

## 5. Python 侧 - HTTP 客户端

- [ ] 5.1 在 `app/services/http_client.py` 中新增 `get_filtered_history_events` 方法
- [ ] 5.2 支持参数：device_no, event_ids (List[int]), start_time, end_time, limit
- [ ] 5.3 调用 go 侧 `/device/history/api/filter` API

## 6. Python 侧 - LLM 数据需求判断

- [ ] 6.1 在 `app/api/routes.py` 中新增 `_build_data_requirement_prompt` 函数
- [ ] 6.2 构建系统提示词，引导 LLM 判断事件ID和时间范围
- [ ] 6.3 新增 `_parse_data_requirement_result` 函数，解析 LLM 返回的 JSON

## 7. Python 侧 - 意图后处理逻辑

- [ ] 7.1 修改 `analyze_intent` 函数，在意图分类后增加后处理阶段
- [ ] 7.2 实现 history 意图后处理：判断数据需求（事件ID+时间范围）→ 拉取历史 → LLM 生成回答
- [ ] 7.3 实现 suggest 意图后处理：判断数据需求（事件ID+时间范围）→ 拉取历史 + 向量检索 + 宝宝画像 → LLM 生成建议
- [ ] 7.4 保持 feeding 和 conversation 意图的原有逻辑不变
- [ ] 7.5 实现 fallback 策略（LLM 判断失败时使用默认配置）

## 8. Python 侧 - 测试

- [ ] 8.1 测试 history 意图后处理流程
- [ ] 8.2 测试 suggest 意图后处理流程
- [ ] 8.3 测试 fallback 策略（LLM 判断失败场景）
- [ ] 8.4 测试与 go 侧新 API 的连通性

## 9. 联调测试

- [ ] 9.1 部署 go_ai_talk 和 python_ai_talk
- [ ] 9.2 测试历史查询场景（"今天喝了多少奶粉"）
- [ ] 9.3 测试成长建议场景（"宝宝最近食量怎么样"）
- [ ] 9.4 验证返回的 JSON 结构与原有格式一致
