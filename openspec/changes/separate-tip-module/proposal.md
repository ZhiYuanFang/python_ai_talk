## Why

当前 tip（小贴士）模块代码嵌套在 `app/clinic/` 目录下，与 clinic（诊疗）模块混在一起。这种组织方式存在三个问题：
1. **语义不清晰**：tip 是一个独立的业务模块，不是 clinic 的子功能，混放容易造成误解
2. **结构不一致**：feeding 模块有独立的 `app/feeding/` 目录，而 tip 没有，三个业务模块组织方式不统一
3. **共享代码位置错误**：tip 和 clinic 共享的数据准备节点（fetch_history、search_vectors 等）放在 clinic 目录下，但它们应该属于共享层

## What Changes

- 将 tip 相关代码从 `app/clinic/` 中拆分出来，建立独立的 `app/tip/` 目录
- 将 tip 和 clinic 共享的图节点（fetch_history、search_vectors、fetch_baby_profile、judge_data_requirement）移动到 `app/shared/` 目录
- 更新所有受影响的 import 路径
- 保持功能完全不变，仅调整代码组织结构

## Capabilities

### New Capabilities

无（本次变更是纯代码结构重构，不涉及新功能）

### Modified Capabilities

无（本次变更不改变任何业务行为，仅调整代码组织方式）

## Impact

- **受影响的文件**：
  - `app/clinic/graphs/tip_graph.py` → 移动到 `app/tip/graphs/tip_graph.py`
  - `app/clinic/graphs/states/tip_state.py` → 移动到 `app/tip/graphs/states/tip_state.py`
  - `app/clinic/schemas/tip.py` → 移动到 `app/tip/schemas/tip.py`
  - `app/clinic/graphs/nodes/stream_tip_response.py` → 移动到 `app/tip/graphs/nodes/stream_tip_response.py`
  - `app/clinic/graphs/nodes/fetch_history.py` → 移动到 `app/shared/graphs/nodes/fetch_history.py`
  - `app/clinic/graphs/nodes/search_vectors.py` → 移动到 `app/shared/graphs/nodes/search_vectors.py`
  - `app/clinic/graphs/nodes/fetch_baby_profile.py` → 移动到 `app/shared/graphs/nodes/fetch_baby_profile.py`
  - `app/clinic/graphs/nodes/judge_data_requirement.py` → 移动到 `app/shared/graphs/nodes/judge_data_requirement.py`
- **需要更新 import 路径的文件**：
  - `app/api/routes/tip.py`
  - `app/clinic/graphs/clinic_graph.py`
  - 所有引用了移动后节点的文件
- **无破坏性变更**：所有 API 接口、数据结构、业务逻辑保持不变
