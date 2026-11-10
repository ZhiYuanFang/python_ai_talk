## Context

语音意图 `predict_channel=next|active` 经 Go voice internal GET 取 imminent pending / active-eta。Go `predict-merge-predict-contract` 已定稿并实现：

- pending 可选 `parentEventName`（根字典权威 `name`）；不存、不投影 `expectLeafTitle`。
- active-eta：`expectEndAt` 省略/null/0 = 无预计结束；**不**带 `parentEventName`。
- 另有 Flutter 用的 `latest-by-event`；本仓语音「上一次」不消费。

今日 Python：`match_imminent_*` / `match_active_*` 主要按 leaf/root `eventId` 对齐条目；`match_active_expect_end` 在无正结束时返回空，易把「进行中无结束」打成未命中。

## Goals / Non-Goals

**Goals:**

- 与 Go 锁定字段名 `parentEventName`。
- next：`eventId` 优先；未中可用 `parentEventName` 做根名反推。
- active：识别无结束进行中；不编造结束钟点；不读 parent 字段。
- 忽略 `expectLeafTitle`（即便旧包偶发出现）。

**Non-Goals:**

- 不本地重算 mergePredict。
- 不强制用户话语必须带父名。
- 不接入 `latest-by-event`。
- 不在 Go 侧做名→id 解析（父名由 Flutter 写入、Go 原样投影）。

## Decisions

1. **字段名**  
   - 全文使用 `parentEventName`；禁止继续写 `parentEventId` 契约。  
   - 解析时 trim；空串视为无父（与 Go 一致）。

2. **next 匹配顺序**  
   - **先**用用户所指事件 id（目录解析到的子或根）与 pending.`eventId` 对齐（保留今日 leaf/root 与多条 nextAt 择优）。  
   - **若未命中**，且能得到用户所指根事件权威名（目录 `name`），则在 pending 中找 `parentEventName` 与该名相等（trim 后）的项；多条时沿用与 nextAt 相同的「最近未来否则最近过去」择优。  
   - 无 `parentEventName` 的旧包项：仅走 eventId 路径，行为与今日一致。  
   - 备选曾考虑只扩 eventId、不做名匹配 → 非合并子 pending 在用户说根名时必 miss，否决。

3. **播报 next**  
   - 名称优先条目 `title`，否则目录名；**不**读 leafTitle。  
   - expect 用量/时长若有则用既有格逻辑。

4. **active 匹配与播报**  
   - 身份匹配仍按 leaf/root/`eventId`（与今日一致）；**不**用 `parentEventName`。  
   - 命中项后：有正 `expectEndAt` → 既有 clock/remain 模板；无正结束 → MUST 仍视为进行中，走「进行中/已开始」类降级话术，MUST NOT 输出具体预计结束时刻。  
   - 备选：无结束直接冷路径本地算法 → 会丢掉「确实在进行」的 Go 信号，否决。

5. **发版**  
   - Go 已先发；本仓对齐读侧即可；旧 Redis 无父名仍可用。

## Risks / Trade-offs

- [同根多子、用户只说根名] → 按 nextAt 择优一条；若需指认具体子，依赖用户说子名（eventId 命中）。  
- [根改名后 parentEventName 短暂旧值] → 靠下次 Flutter pending PUT 刷新（Go 已接受）。  
- [名字符串弱相等] → trim + 与目录权威 name 对齐；不做模糊别名（非本仓职责）。

## Migration Plan

1. 更新本 change 产物与实现对齐 `parentEventName`。  
2. 部署 Python；旧包无父名、active 正结束仍成功。  
3. 回滚：勿再依赖 leafTitle；勿再强制「无结束=未命中」。

## Open Questions

- （无）字段名、仅 pending 带 parent、不接 latest-by-event 已与 Go 锁定。
