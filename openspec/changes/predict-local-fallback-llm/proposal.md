## Why

R·predict 在 Go active-eta / imminent 无数据时仅「暂时估不准」，无法回答间隔、用量、时长及预约下次等问法；产品需要在保留 Go 热路径模板的前提下，用与 Flutter 对齐的本地预测算法 + 语境史 + LLM 兜底，避免模型空想数字。

## What Changes

- Go 命中（非预约 Redis 锚点）时 **保留** 现有 `speak_predict` 模板播报（clock/remain）。
- Go miss、不够答、或 **预约事件**（约定不进 predict Redis）时进入兜底：
  - **算法轨**：非预约固定近 7 日史 → Python 封装 Flutter `event_next_predictor` 思路，输出 interval / nextAt / 用量 / 时长；预约根旁路间隔，读 `appointment/next` 约定 nextAt。
  - **LLM 语境轨**：用与查史 **同一套** TIME 方法解用户语境窗 → 拉史 → `build_feeding_history_prompt_blocks`（共享）拼块。
  - 终答：LLM（原话 + 紧凑史 + 算法/约定 JSON）；SSE `stream(thinking_enabled=True)`，中文 reasoning；提示词落 `prompts/system.py`。
- 样本不足（非预约）→ 直接「数据量太少，无法预测」，不进 LLM 编造；预约无约定 → 明确无下次约定类降级。
- 算法结果 **Redis 设备快照**，TTL **10 分钟**；意图 **C/U/D（含改史的 end）落库成功** 后主动 DEL；不写入意图/时间分类飞轮。
- 算法窗 **不受** 用户语境 TIME 影响；语境 TIME 只服务 LLM 史块。
- 孪生 Go：预约约定 **internal GET**（对齐 App `appointment/next`）；目录需可读 `isAppointment`。

## Capabilities

### New Capabilities

- `intent-predict-algo-fallback`：预测 Go miss / 预约兜底——本地算法与预约约定、双轨史、LLM 终答、Redis 算法快照与 CUD 失效

### Modified Capabilities

- `intent-predict-qa`：`speak_predict` 在无 Go 锚点时 MUST NOT 仅以「估不准」结束；MUST 进入算法/预约兜底路径（Go 命中模板行为保留）

## Impact

- 本仓：`speak_predict`、预测工具模块（feeding）、Redis 快照（复用 `create_async_redis_client`）、CUD 落库后清快照、事件目录 `isAppointment`、`http_client` 预约 internal GET、兜底 LLM 提示词、TIME 在兜底分支解窗（查史同方法）
- 孪生：`go_ai_talk` device internal appointment next GET；Flutter 算法为参考，本仓按场景封装，不改 Flutter
- 依赖：既有近史 filter/list、共享 `feeding_history_compact`、既有 Redis（闸门/companion 旁新前缀）
- 不写测试文件；不回写 Go imminent Redis（预约仍不驱动 predict Redis）
