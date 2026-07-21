# Python AI Talk 项目全局约束

本文档定义了 Python AI Talk 项目的全局代码生成约束。所有变更提案和代码实现都必须遵循这些约束。

## 一、代码生成约束

### 1.1 不生成测试文件

- **禁止生成测试文件**：不需要为功能代码创建单元测试、集成测试或其他测试文件
- **原因**：测试由开发者手动编写，避免自动生成的测试文件质量参差不齐
- **适用范围**：所有变更提案中的任务不得包含"创建测试"或"编写测试用例"等任务

### 1.2 业务逻辑中文注释

- **强制要求**：所有生成的代码必须包含详细的业务逻辑中文注释
- **注释层级**：
  - 文件级：模块说明、业务说明、设计思路、使用场景
  - 类级：业务说明、设计思路、核心属性
  - 方法/函数级：业务逻辑、Args、Returns、Side Effects
  - 行级：关键业务逻辑分支必须有中文注释
- **注释语言**：中文
- **注释格式**：文件/类/方法级使用 `"""` 三引号，行级使用 `#` 单行注释

### 1.3 功能代码按业务逻辑分离

- **强制要求**：所有功能代码必须按业务逻辑分离到不同的文件夹，不可散乱
- **目录结构**：
  ```
  app/
  ├── feeding/           # 喂养动作模块
  │   ├── graphs/        # LangGraph 图定义
  │   │   ├── nodes/     # 图节点
  │   │   │   └── prompts/  # 提示词模板
  │   │   └── states/    # 图状态
  │   ├── schemas/       # 数据模型
  │   └── services/      # 业务服务
  ├── clinic/            # 喂养建议模块
  │   ├── graphs/
  │   │   ├── nodes/
  │   │   │   └── prompts/
  │   │   └── states/
  │   ├── schemas/
  │   └── services/
  ├── shared/            # 跨模块共享服务
  └── config/            # 全局配置
  ```
- **禁止跨模块直接导入**：
  - `feeding` 模块不能直接导入 `clinic` 模块的代码
  - `clinic` 模块不能直接导入 `feeding` 模块的代码
  - 需要共享的代码必须放在 `shared` 模块

## 二、技术栈

- **语言**：Python 3.11+
- **Web 框架**：FastAPI
- **图编排**：LangGraph
- **向量数据库**：Chroma（BGE-small-zh-v1.5 嵌入模型）
- **HTTP 客户端**：httpx（调用兄弟仓 API）
- **缓存**：cachetools.TTLCache（24小时 TTL）
- **LLM**：DeepSeek / Zhipu 双提供商

## 三、架构约束

- Python 服务作为"智能内核"，被 go_ai_talk 调用，不独立对外服务
- 必须通过 HTTP 调用兄弟仓 API，不能直接访问数据库/Redis
- 向量数据库 volume 在运行时挂载，首次启动时构建
- 服务运行在端口 8000

## 四、命名规范

- 文件命名：小写字母 + 下划线（如 `classify_intent.py`）
- 类命名：PascalCase（如 `IntentGraph`）
- 方法/函数命名：snake_case（如 `match_event_by_vector`）
- 变量命名：snake_case，避免缩写

## 五、API 规范

- 喂养动作 API：`/v1/feeding/` 前缀
- 喂养建议 API：`/v1/clinic/` 前缀
- 统一响应格式：`{"code": 0, "message": "success", "data": {...}}`

## 六、向量数据库规范

- 喂养事件向量库：`feeding_events` Collection
- 母婴知识向量库：`mother_baby_knowledge` Collection
- 两个 Collection 物理隔离，避免数据紊乱

## 七、详细规范参考

详细的代码生成规范请参考 [docs/coding-standard.md](../docs/coding-standard.md)。
