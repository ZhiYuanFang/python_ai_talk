# llm-care-alert-daily — Python 契约（来自 Flutter 主变更）

主规格与任务在兄弟仓 `flutter_ai_talk`：`openspec/changes/llm-care-alert-daily/`。
Go 编排契约见 `go_ai_talk/openspec/changes/llm-care-alert-daily/CONTRACT.md`。

本文件供 Python 实现对照；路由挂在统一前缀 `/v1` 下（与 tip/clinic/intent 一致）。

**飞轮语义（care-alert-prompt-flywheel）**：不再走通识质量分；改为全局本地 prompt 对比样例飞轮（Docker 挂载卷）。旧变更 `care-alert-knowledge-flywheel` 的 care_alert 通识加减分路径已由本方向取代。

## 职责

- 接收 Go 编排请求：宝宝月龄、近期历史、（可选）知识图谱上下文、**模型标识**（DeepSeek / Zhipu）。
- 拉取近史 + 画像 + LLM 分析，产出「值得留意」items 列表（可映射 Flutter / Go DTO）。
- **不**调用通识向量检索；**不**将 `kg_context` 硬塞进判定。
- **不**与 clinic 配额耦合；**不**做忽略/追问自由文本 NLP。
- 准确优先：仅凭清晰史信号出项，不足则 `items` 可为 []。
- 飞轮：analyze 写入 `suggestionId → 建议快照`；feedback 固定意图写入本地 ledger，按阈值重写全局 `contrastive_examples` 并落盘。

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

### `POST /v1/care-alert/feedback`（全局 prompt 飞轮）

```json
{
  "device_no": "...",
  "suggestion_id": "<uuid>",
  "intent": "ignore|follow_up",
  "day": "2026-08-08"
}
```

固定意图；**无**自由文本 NLP。  
- `follow_up` / `ignore`：写入本地 ledger，驱动对比样例重写（同类相反反馈保留张力）  
- **不**更新 `mother_baby_knowledge` 质量分  
- 无快照：仅日志，仍返回 `{ "ok": true }`  
Go 在本接口失败时仍对客户端返回成功（**best-effort**）。

## 约束

- 语气「值得留意」，非医疗诊断。
- 返回 **列表**（驱动跑马灯），非仅 Top1。
- 有近两日记录且事件对照表可用时：**至少 1 条** item（LLM 空则软兜底）；无史或无对照表仍可空。
- 判定 **必须结合宝宝月龄**（已知则写入 reasons.ageMonths；未知不编造常模）。
- 每项必须有可原样传入陪伴的 `followUpPrompt`（缺省时 Go 会补齐）。
- LLM 结合本机近史 + 月龄 + 本地全局 prompt（含可选对比样例）；月龄/历史仅运行时注入，不写死进落盘 prompt。
- Prompt / ledger 目录须挂载（默认 `/app/data/care_alert`），重启不丢。

## 状态

- [x] 分析接口 + 历史拼装（`POST /v1/care-alert/analyze`）
- [x] 按 Go 传入模型执行 LLM
- [x] 输出对齐 DTO（含 followUpPrompt / suggestionId）
- [x] prompt 飞轮 `POST /v1/care-alert/feedback`（固定意图 → ledger / 对比样例；suggestion→快照）
- [x] 无通识检索；不硬塞 kg_context
- [x] 有史至少一条 + 月龄约束（含软兜底）

## Flutter 备注

主变更任务 **6.2**（手工路径验收）仍为手动，未自动勾选。
