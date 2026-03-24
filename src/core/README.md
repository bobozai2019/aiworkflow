# core - 核心模块

本目录包含系统的核心业务逻辑。

## 文件说明

| 文件 | 职责 |
|------|------|
| `agent.py` | Agent基类定义，包含状态管理、消息处理等核心接口 |
| `message.py` | 消息数据类定义，用于Agent间通信 |
| `context.py` | 上下文管理，用于Agent间共享状态 |
| `workflow.py` | 工作流引擎，负责Agent编排和任务调度 |

## 核心类设计

### Agent基类
```python
class BaseAgent:
    - id: str              # Agent唯一标识
    - name: str            # Agent名称
    - state: AgentState    # 当前状态
    - protocol: BaseProtocol  # 使用的协议
    
    + execute(task) -> Result  # 执行任务
    + on_message(msg)          # 处理消息
    + get_state()              # 获取状态
```

### 消息类
```python
class Message:
    - role: str           # system/user/assistant
    - content: str        # 消息内容
    - metadata: dict      # 元数据
    - timestamp: datetime # 时间戳
```

### 工作流类
```python
class Workflow:
    - agents: List[BaseAgent]  # Agent列表
    - state: WorkflowState     # 工作流状态
    
    + add_agent(agent)         # 添加Agent
    + run(task) -> Result      # 执行工作流
    + get_progress()           # 获取进度
```

## 开发顺序

1. `message.py` - 消息数据类（最基础）
2. `context.py` - 上下文管理
3. `agent.py` - Agent基类
4. `workflow.py` - 工作流引擎
