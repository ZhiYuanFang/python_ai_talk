## 1. 创建共享节点目录并移动共享文件

- [x] 1.1 创建 `app/shared/graphs/nodes/` 目录及 `__init__.py`
- [x] 1.2 移动 `fetch_history.py` 到 `app/shared/graphs/nodes/`
- [x] 1.3 移动 `search_vectors.py` 到 `app/shared/graphs/nodes/`
- [x] 1.4 移动 `fetch_baby_profile.py` 到 `app/shared/graphs/nodes/`
- [x] 1.5 移动 `judge_data_requirement.py` 到 `app/shared/graphs/nodes/`
- [x] 1.6 检查并更新共享节点内部的 import 路径

## 2. 创建 tip 模块目录并移动 tip 文件

- [x] 2.1 创建 `app/tip/` 目录结构及 `__init__.py`
- [x] 2.2 创建 `app/tip/graphs/` 目录及 `__init__.py`
- [x] 2.3 创建 `app/tip/graphs/nodes/` 目录及 `__init__.py`
- [x] 2.4 创建 `app/tip/graphs/states/` 目录及 `__init__.py`
- [x] 2.5 创建 `app/tip/schemas/` 目录及 `__init__.py`
- [x] 2.6 移动 `tip_graph.py` 到 `app/tip/graphs/`
- [x] 2.7 移动 `tip_state.py` 到 `app/tip/graphs/states/`
- [x] 2.8 移动 `schemas/tip.py` 到 `app/tip/schemas/`
- [x] 2.9 移动 `stream_tip_response.py` 到 `app/tip/graphs/nodes/`

## 3. 更新所有受影响的 import 路径

- [x] 3.1 更新 `app/tip/graphs/tip_graph.py` 中的 import 路径（共享节点 + tip_state）
- [x] 3.2 更新 `app/clinic/graphs/clinic_graph.py` 中的共享节点 import 路径
- [x] 3.3 更新 `app/api/routes/tip.py` 中的 import 路径
- [x] 3.4 全局搜索 `app.clinic.graphs.nodes` 引用并更新所有遗漏的 import

## 4. 验证测试

- [x] 4.1 验证服务可正常启动（无 ImportError）
- [x] 4.2 验证所有 tip 相关接口功能正常
- [x] 4.3 验证所有 clinic 相关接口功能正常
- [x] 4.4 验证所有共享节点功能正常
