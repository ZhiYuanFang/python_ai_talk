# llm-care-alert-daily — Python 契约（来自 Flutter 主变更）

主规格与任务在兄弟仓 `flutter_ai_talk`：`openspec/changes/llm-care-alert-daily/`。
Go 编排契约见 `go_ai_talk/openspec/changes/llm-care-alert-daily/CONTRACT.md`。

本文件供 Python 实现对照；路由挂在统一前缀 `/v1` 下（与 tip/clinic/intent 一致）。

## 职责

- 接收 Go 编排请求：宝宝月龄、近期历史、知识图谱上下文、**模型标识**（DeepSeek / Zhipu）。
- 执行 KG + LLM 分析，产出「值得留意」items 列表（可映射 Flutter / Go DTO）。
- **不**与 clinic 配额耦合；**不**做忽略/追问自由文本 NLP（飞轮仅固定意图 ACK）。

## Go → Python 接口（与 Go `PythonAIClient` 对齐）

### `POST /v1/care-alert/analyze`

请求示例（snake_case；`model` 为简写，`model_cfg` 为完整执行配置）：

```json
{
  "device_no": "...",
  "day": "2026-08-08",
  "model": "deepseek|zhipu",
  "model_cfg": {
    "provider": "deepseek|zhipu",
    "name": "deepseek-v4-flash|glm-4.7-flash",
    "max_in_flight": 1
  },
  "age_months": 3,
  "history_summary": {},
  "kg_context": {}
}
```

响应示例（Go 再补 `suggestionId` / `followUpPrompt` 亦可由 Python 生成）：

```json
{
  "items": [
    {
      "eventId": "...",
      "eventName": "...",
      "summaryLine": "...",
      "followUpPrompt": "家长可直接发给树洞的追问原文",
      "reasons": [
        {
          "type": "elongatedInterval",
          "score": 1.0,
          "expectationUsed": true,
          "ageMonths": 3,
          "medianGapMs": 14400000,
          "lastGapMs": 21600000,
          "expectGapMaxMs": 18000000,
          "detailLines": ["可选中文说明"]
        }
      ]
    }
  ]
}
```

亦兼容外层 envelope `{ "code": 0, "data": { "items": [...] } }`。

### `POST /v1/care-alert/feedback`（飞轮 ACK）

```json
{
  "device_no": "...",
  "suggestion_id": "<uuid>",
  "intent": "ignore|follow_up",
  "day": "2026-08-08"
}
```

固定意图；**无**自由文本 NLP、**不** invent 质量分映射（尚无 suggestion→知识 doc 接线）。  
实现：校验枚举后日志 + `{ "ok": true }`。  
Go 在本接口失败时仍对客户端返回成功（本地已记日志；**best-effort**）。

## 约束

- 语气「值得留意」，非医疗诊断。
- 返回 **列表**（驱动跑马灯），非仅 Top1。
- 每项必须有可原样传入陪伴的 `followUpPrompt`（缺省时 Go 会补齐）。

## 状态

- [x] 分析接口 + KG/历史拼装（`POST /v1/care-alert/analyze`）
- [x] 按 Go 传入模型执行 LLM
- [x] 输出对齐 DTO（含 followUpPrompt）
- [x] 飞轮 ACK `POST /v1/care-alert/feedback`（无 NLP）

## Flutter 备注

主变更任务 **6.2**（手工路径验收）仍为手动，未自动勾选。
