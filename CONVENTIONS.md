# 项目开发约定

本文档定义了Multi-Agent系统开发过程中必须遵守的规范，重点在于系统架构和模块间交互。

---

## 一、系统架构约定

### 1.1 分层架构

```
┌─────────────────────────────────────────┐
│              UI Layer (PyQt)             │  ← 用户交互
├─────────────────────────────────────────┤
│          Workflow Engine                │  ← 任务编排
├─────────────────────────────────────────┤
│    Agent Layer (Analyst/Coder/...)      │  ← 角色执行
├─────────────────────────────────────────┤
│    Protocol Layer (DeepSeek/Qwen/...)   │  ← API适配
├─────────────────────────────────────────┤
│    Communication Layer (HTTP/WS)        │  ← 网络通信
└─────────────────────────────────────────┘
```

### 1.2 模块依赖规则

| 模块 | 可依赖 | 禁止依赖 |
|------|--------|----------|
| ui | core, agents, utils | protocols, communication |
| core | utils | agents, protocols |
| agents | core, protocols, utils | ui, api |
| protocols | communication, utils | agents, core, ui |
| communication | utils | 所有业务模块 |
| api | core, agents | ui |

**原则**: 上层可依赖下层，下层禁止依赖上层，同层模块尽量解耦。

---

## 二、核心数据结构

### 2.1 消息格式

```python
@dataclass
class Message:
    role: str        # "system" | "user" | "assistant"
    content: str     # 消息内容
    metadata: dict   # 扩展字段：token数、模型名等
```

### 2.2 Agent状态

```python
class AgentState(Enum):
    IDLE = "idle"           # 空闲
    RUNNING = "running"     # 执行中
    COMPLETED = "completed" # 已完成
    ERROR = "error"         # 错误
```

### 2.3 任务结果

```python
@dataclass
class TaskResult:
    success: bool           # 是否成功
    content: str            # 输出内容
    agent_id: str           # 执行的Agent
    duration: float         # 耗时(秒)
    error: Optional[str]    # 错误信息
```

---

## 三、模块间通信

### 3.1 Agent → Protocol

```python
# Agent调用协议
async def execute(self, task: str) -> TaskResult:
    messages = [
        Message(role="system", content=self.system_prompt),
        Message(role="user", content=task)
    ]
    
    # 流式获取响应
    async for chunk in self.protocol.chat(messages, stream=True):
        self.on_chunk(chunk)
```

### 3.2 Workflow → Agent

```python
# 工作流调度Agent
class Workflow:
    async def run(self, task: str) -> TaskResult:
        context = Context()
        
        for agent in self.agents:
            result = await agent.execute(task, context)
            context.set(agent.name, result)
            
        return context.final_result()
```

### 3.3 上下文传递

```python
# Agent间通过Context共享数据
class Context:
    def set(self, key: str, value: Any) -> None:
        """存储数据"""
        
    def get(self, key: str, default=None) -> Any:
        """获取数据"""
        
    def get_previous_result(self) -> Optional[TaskResult]:
        """获取上一个Agent的输出"""
```

---

## 四、协议层约定

### 4.1 协议接口

所有协议必须实现以下接口：

```python
class BaseProtocol(ABC):
    @abstractmethod
    async def chat(
        self, 
        messages: List[Message], 
        stream: bool = True
    ) -> AsyncIterator[str]:
        """对话接口"""
        pass
```

### 4.2 协议配置格式

```yaml
# config/protocols.yaml
protocols:
  deepseek:
    base_url: "https://api.deepseek.com"
    api_key: "${DEEPSEEK_API_KEY}"  # 必须使用环境变量
    default_model: "deepseek-chat"
```

### 4.3 错误处理

```python
# 协议层统一异常
class ProtocolError(Exception):
    def __init__(self, message: str, provider: str, status_code: int = None):
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)
```

---

## 五、Agent约定

### 5.1 Agent配置格式

```yaml
# config/agents.yaml
agents:
  analyst:
    name: "需求分析师"
    model: "deepseek-chat"
    protocol: "deepseek"      # 引用protocols.yaml中的配置
    system_prompt: |
      你是一位专业的需求分析师...
    temperature: 0.7
```

### 5.2 Agent生命周期

```
初始化 → 接收任务 → 调用协议 → 流式输出 → 返回结果
    ↓                              ↓
  IDLE                          RUNNING
                                   ↓
                              COMPLETED/ERROR
```

### 5.3 Agent输出规范

每个Agent的输出应包含：
1. **摘要**: 一句话描述完成的工作
2. **详情**: 具体内容（需求文档/代码/测试报告等）
3. **建议**: 后续步骤建议（可选）

---

## 六、工作流约定

### 6.1 默认工作流

```
用户需求 → 需求分析师 → Coder → 完成
```

### 6.2 工作流配置

```yaml
# 未来扩展：config/workflow.yaml
workflows:
  default:
    steps:
      - agent: analyst
      - agent: coder
    on_error: stop  # stop | retry | skip
```

### 6.3 进度回调

```python
# 工作流进度通知
class ProgressCallback(Protocol):
    def on_agent_start(self, agent: str) -> None: ...
    def on_agent_chunk(self, agent: str, chunk: str) -> None: ...
    def on_agent_complete(self, agent: str, result: TaskResult) -> None: ...
```

---

## 七、配置管理

### 7.1 配置文件职责

| 文件 | 职责 |
|------|------|
| `config.yaml` | 应用配置（日志、HTTP等） |
| `agents.yaml` | Agent角色配置 |
| `protocols.yaml` | 模型协议配置 |

### 7.2 配置加载

```python
# 统一通过Config类加载
config = Config.load()  # 自动加载所有配置

# 获取配置
timeout = config.get("http.timeout", default=60)
agent_config = config.get_agent("analyst")
```

### 7.3 环境变量

敏感信息必须通过环境变量配置：

```bash
# .env
DEEPSEEK_API_KEY=sk-xxx
QWEN_API_KEY=sk-xxx
```

---

## 八、日志规范

### 8.1 日志级别使用

| 级别 | 场景 |
|------|------|
| DEBUG | 详细调试信息（API请求/响应） |
| INFO | 关键流程节点（Agent启动/完成） |
| WARNING | 可恢复的异常情况 |
| ERROR | 错误但系统可继续运行 |
| CRITICAL | 系统级错误 |

### 8.2 日志格式

```python
# 标准日志格式
logger.info(f"[{agent_name}] Task started: {task_id}")
logger.info(f"[{agent_name}] Task completed in {duration:.2f}s")
logger.error(f"[{agent_name}] Error: {error}", exc_info=True)
```

---

## 九、错误处理

### 9.1 异常层次

```
AgentError (基类)
├── ProtocolError    # API调用错误
├── WorkflowError    # 工作流错误
└── ConfigError      # 配置错误
```

### 9.2 错误传播

```python
# 协议层错误向上传播
try:
    response = await protocol.chat(messages)
except httpx.TimeoutError as e:
    raise ProtocolError(f"Timeout: {e}", provider=protocol.name)

# Agent层捕获并包装
try:
    result = await agent.execute(task)
except ProtocolError as e:
    return TaskResult(success=False, error=str(e))
```

---

## 十、扩展规范

### 10.1 新增协议

1. 在 `src/protocols/` 创建 `{name}.py`
2. 继承 `BaseProtocol`
3. 在 `protocols.yaml` 添加配置
4. 在 `__init__.py` 注册工厂

### 10.2 新增Agent

1. 在 `src/agents/` 创建 `{name}.py`
2. 继承 `BaseAgent`
3. 在 `agents.yaml` 添加配置
4. 定义系统提示词

### 10.3 新增工作流

1. 在 `src/core/workflow.py` 扩展
2. 支持条件分支、并行执行等

---

## 十一、禁止事项

- ❌ 禁止硬编码API密钥
- ❌ 禁止跨层直接调用（如UI直接调用Protocol）
- ❌ 禁止在Agent中直接使用httpx（必须通过Protocol）
- ❌ 禁止修改Context中其他Agent的数据
- ❌ 禁止阻塞异步操作

---

**遵守以上约定是参与本项目开发的前提条件。**
