## REMOVED Requirements

### Requirement: 新增事件触发小贴士生成
**Reason**: tip Agent 退役；前端不再使用 tip SSE。
**Migration**: 见 `retire-tip-agent`；桌面/预测贴士改由 widget tip + Care Alert 产品面承担。

### Requirement: 1 小时去抖控制
**Reason**: tip 生成链路删除。
**Migration**: 删除 Go tip 去抖逻辑（若仍存在且无其它调用方）。

### Requirement: tip_ai 额度统一管理
**Reason**: tip Agent 删除后不再扣 tip_ai。
**Migration**: 额度配置中移除或停用 tip_ai 路径（跨仓 Go）。

### Requirement: Python tip_graph 生成小贴士
**Reason**: 删除 tip_graph 与 `/v1/tip/stream`。
**Migration**: 见 `retire-tip-agent`。

### Requirement: Go history service 透传 SSE 并存储
**Reason**: tip SSE 宿主删除。
**Migration**: 删除 TipStream/TipCtrl 及 tip 表写入（若仅服务 tip）。

### Requirement: Flutter 小贴士组件悬浮展示与关闭
**Reason**: tip SSE UI 已退役。
**Migration**: 删除 HomeTipPanel 等死代码；保留 widget_tip_*。
