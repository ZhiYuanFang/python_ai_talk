## 1. Intent / Clinic 入站模型



- [x] 1.1 修改 `app/feeding/schemas/intent.py` 中 `IntentRequest.device_no`：以 snake 为准，采用 `populate_by_name` + `AliasChoices("device_no", "deviceNo")`（或去掉只认 camel 的 alias），保证 Go 发 `device_no` 可通过校验

- [x] 1.2 同样修正 `ClinicRequest.device_no`（同上策略）

- [x] 1.3 更新相关文件/类级中文注释：说明 Go↔Python 内部契约为 snake_case，camel 仅为过渡双收（若保留）



## 2. Tip 入站模型



- [x] 2.1 修改 `app/tip/schemas/tip.py` 中 `TipRequest` 的 `device_no`、`baby_age_months`、`current_time`：接受 snake 键（可双收 `deviceNo` / `babyAgeMonths` / `currentTime`）

- [x] 2.2 更新 `app/api/routes/tip.py`（及 clinic/intent 路由若文档仍写死 camel 必填）中文注释，避免再暗示「必须传 camel」



## 3. 文档矛盾与回归



- [x] 3.1 在本仓与 `d:\work\go_ai_talk\openspec\changes\` 内 grep「只认 camel / 必须 deviceNo alias」等矛盾表述；若有「应发 device_no 但 Py 只认 camel」类文字，改为「内部 JSON MUST snake；Python MUST 接受 snake（可双收 camel）」

- [x] 3.2 **禁止**修改 `go_ai_talk/internal/services/voice/python_ai_client.go` 的 JSON 标签为 camel

- [x] 3.3 手测或用现有调用路径验证：Intent（或 stream）、Clinic stream、Tip stream 使用 Go snake body 不再 422（本阶段不新增自动化测试文件）

