## REMOVED Requirements

### Requirement: ENV-gated one-shot standard rebuild
**Reason**: `feeding_events` 与标准事件名向量已拆除，该开关无实现目标且易与意图缓存清库混淆。
**Migration**: 从环境文件、compose、settings、deploy-guide 删除 `REBUILD_FEEDING_STANDARD_EVENTS`。若需丢掉测脏的意图缓存，使用 `CLEAR_FEEDING_INTENTS_ON_STARTUP`。
