# llm-care-alert-daily — Python 契约（来自 Flutter 主变更）

主规格与任务在兄弟仓 `flutter_ai_talk`：`openspec/changes/llm-care-alert-daily/`。
Go 编排契约见 `go_ai_talk/openspec/changes/llm-care-alert-daily/CONTRACT.md`。

本文件供 Python 实现对照；路由挂在统一前缀 `/v1` 下（与 tip/clinic/intent 一致）。

通识飞轮增量见同仓变更 `care-alert-knowledge-flywheel`（本 CONTRACT 已对齐其行为）。

## 职责

- 接收 Go 编排请求：宝宝月龄、近期历史、知识图谱上下文、**模型标识**（DeepSeek / Zhipu）。
- 执行向量通识检索（过相似度/质量门槛）+ LLM 分析，产出「值得留意」items 列表（可映射 Flutter / Go DTO）。
- **不**与 clinic 配额耦合；**不**做忽略/追问自由文本 NLP。
- 通识：**准确优先**——未过门槛则 knowledge 为空，**不得**用未达标的 `kg_context` 硬塞进判定。
- 飞轮：analyze 写入 `suggestionId → knowledge_ids`；feedback 固定意图更新通识质量分。

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

响应示例（**请透传 Python 返回的 `suggestionId`** 供 feedback 飞轮映射）：

```json
{
  "items": [
    {
      "suggestionId": "<uuid>",
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

### `POST /v1/care-alert/feedback`（通识质量飞轮）

```json
{
  "device_no": "...",
  "suggestion_id": "<uuid>",
  "intent": "ignore|follow_up",
  "day": "2026-08-08"
}
```

固定意图；**无**自由文本 NLP。  
- `follow_up`：对 analyze 映射的通识文档质量分上调（同 clinic feedback=1）  
- `ignore`：质量分下调（同 feedback=-1）  
- 无映射或空 ids：仅日志，仍返回 `{ "ok": true }`  
Go 在本接口失败时仍对客户端返回成功（**best-effort**）。

## 约束

- 语气「值得留意」，非医疗诊断。
- 返回 **列表**（驱动跑马灯），非仅 Top1。
- 每项必须有可原样传入陪伴的 `followUpPrompt`（缺省时 Go 会补齐）。
- LLM 结合本机近史 + 合格通识判定；无合格通识不编造、宁缺毋滥。

## 状态

- [x] 分析接口 + KG/历史拼装（`POST /v1/care-alert/analyze`）
- [x] 按 Go 传入模型执行 LLM
- [x] 输出对齐 DTO（含 followUpPrompt / suggestionId）
- [x] 通识飞轮 `POST /v1/care-alert/feedback`（固定意图 → 质量分；suggestion→ids 映射）
- [x] 准确优先：不硬塞未过门槛知识

## Flutter 备注

主变更任务 **6.2**（手工路径验收）仍为手动，未自动勾选。
