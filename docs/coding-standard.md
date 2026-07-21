# Python AI Talk 代码生成规范

## 一、目录结构规范

### 1.1 功能模块隔离

- 喂养动作相关代码统一放在 `app/feeding/` 目录下
- 喂养建议相关代码统一放在 `app/clinic/` 目录下
- 跨模块共享代码放在 `app/shared/` 目录下
- 全局配置放在 `app/config/` 目录下

### 1.2 模块内部结构

每个模块遵循如下目录结构：

```
{module}/
├── __init__.py
├── graphs/              # LangGraph图定义
│   ├── __init__.py
│   ├── {graph_name}_graph.py
│   ├── nodes/           # 图节点
│   │   ├── __init__.py
│   │   ├── prompts/     # 提示词模板
│   │   │   └── __init__.py
│   │   └── {node_name}.py
│   └── states/          # 图状态
│       ├── __init__.py
│       └── {state_name}_state.py
├── schemas/             # 数据模型
│   ├── __init__.py
│   └── {schema_name}.py
└── services/            # 业务服务
    ├── __init__.py
    └── {service_name}.py
```

### 1.3 禁止跨模块直接导入

- `feeding` 模块不能直接导入 `clinic` 模块的代码
- `clinic` 模块不能直接导入 `feeding` 模块的代码
- 需要共享的代码必须放在 `shared` 模块

## 二、代码注释规范

### 2.1 文件级注释

每个 Python 文件必须包含文件级 docstring，内容包含：

- **模块/文件说明**：简要说明该文件的用途
- **业务说明**：核心业务功能描述
- **设计思路**：技术选型原因、核心实现逻辑、与其他模块的关系
- **使用场景**：该模块在何时被使用

### 2.2 类级注释

每个类必须包含类级 docstring，内容包含：

- **业务说明**：该类在业务中的角色和职责
- **设计思路**：类的设计理念与实现策略
- **核心属性**：列出关键属性及其含义

### 2.3 方法/函数级注释

每个方法/函数必须包含 docstring，内容包含：

- **业务逻辑**：详细描述方法的执行步骤
- **Args**：每个参数的说明
- **Returns**：返回值说明
- **Side Effects**（如有）：副作用说明

### 2.4 代码行级注释

关键业务逻辑行**必须**添加中文注释：

- 每个业务逻辑分支必须有注释说明
- 避免无意义注释（不要注释显而易见的代码）
- 使用 `#` 单行注释

### 2.5 注释格式要求

- **语言**：中文
- 文件/类/方法级使用 `"""` 三引号
- 行级使用 `#` 单行注释
- 与代码保持一致的缩进

## 三、命名规范

### 3.1 文件命名

小写字母 + 下划线，如 `classify_intent.py`

### 3.2 类命名

PascalCase，如 `IntentGraph`

### 3.3 方法/函数命名

snake_case，如 `match_event_by_vector`

### 3.4 变量命名

snake_case，避免缩写

## 四、依赖管理规范

### 4.1 内部导入规则

- 同模块内导入使用**相对导入**
- 跨模块导入仅允许从 `shared/` 和 `config/`
- 禁止循环导入

### 4.2 外部依赖

- 通过 `pyproject.toml` 管理
- 严格控制版本号

## 五、向量数据库规范

### 5.1 Collection 命名

| 用途 | Collection 名称 |
|------|-----------------|
| 喂养事件 | `feeding_events` |
| 母婴知识 | `mother_baby_knowledge` |

### 5.2 元数据规范

**喂养事件元数据（feeding_events）**：

```json
{
  "baby_id": "string, 宝宝ID",
  "event_type": "string, 事件类型（如 feed/diaper/sleep）",
  "event_time": "string, 事件时间 ISO 8601",
  "source": "string, 数据来源"
}
```

**知识文档元数据（mother_baby_knowledge）**：

```json
{
  "category": "string, 知识分类（如 喂养知识/健康护理/生长发育）",
  "title": "string, 文档标题",
  "source": "string, 知识来源"
}
```

## 六、API 规范

### 6.1 路由组织

| 模块 | 路由前缀 | 说明 |
|------|----------|------|
| 喂养动作 | `/v1/feeding/` | 喂养事件相关接口 |
| 喂养建议 | `/v1/clinic/` | 门诊建议相关接口 |

### 6.2 响应格式

统一响应格式：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

- `code`：`0` 表示成功，非 `0` 表示失败
- `message`：响应描述
- `data`：业务数据

## 七、版本控制规范

### 7.1 提交信息格式

```
<type>(<scope>): <subject>

<body>
```

**type 类型**：

| 类型 | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | 修复缺陷 |
| `refactor` | 重构 |
| `docs` | 文档变更 |
| `style` | 格式调整 |
| `test` | 测试相关 |
| `chore` | 构建/工具变更 |

**示例**：

```
feat(feeding): 添加向量匹配节点

- 实现基于向量的事件匹配逻辑
- 支持置信度分层判定
- 添加完整的中文注释
```
