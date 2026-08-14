## 1. 共享未定槽位检测

- [x] 1.1 将 `_unresolved_slots`（或 `has_unresolved_event_slots`）导出供路由与节点共用，中文注释说明「有名无 id」判定
- [x] 1.2 `resolve_remark_event` 使用共享检测；保留无槽位防御性早退，但注释标明主门控在路由

## 2. 分类后条件路由

- [x] 2.1 实现 `route_after_classify`：有未定槽位 → `resolve_remark_event`；否则复用与 `route_after_remark_resolve` 相同的确认/read/CUD/END 判定（可抽公共函数）
- [x] 2.2 更新 `classify_intent` 的 conditional_edges 映射，包含反查与直达落点；更新图模块中文说明

## 3. 验收

- [x] 3.1 手工核对：字典已定 id 的 create/read 不出现备注反查 thinking、不调备注 filter；专名 AD 仍进反查
- [x] 3.2 `openspec validate conditional-remark-resolve-route --strict` 通过
