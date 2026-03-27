# 交互式工作流使用指南

## 概述

交互式工作流（InteractiveWorkflow）允许用户在每个Agent执行前审查和确认其工作计划，提供更好的控制和透明度。

## 工作流程

```
用户提交任务
    ↓
需求分析师生成计划 → 用户确认 → 执行
    ↓
系统架构师生成计划 → 用户确认 → 执行
    ↓
代码开发者生成计划 → 用户确认 → 执行
    ↓
调试员生成计划（如需要）→ 用户确认 → 执行
    ↓
测试员生成计划 → 用户确认 → 执行
    ↓
完成
```

## 使用方式

### 方式1: 命令行交互

```python
from src.core.workflow_interactive import InteractiveWorkflow

# 创建工作流
workflow = InteractiveWorkflow(
    base_output_dir=Path("./output"),
    on_plan_ready=on_plan_ready_callback,
    on_stage_complete=on_stage_complete_callback
)

# 添加Agent
workflow.add_agent(AnalystAgent(protocol=protocol))
workflow.add_agent(ArchitectAgent(protocol=protocol))
workflow.add_agent(CoderAgent(protocol=protocol))
workflow.add_agent(TesterAgent(protocol=protocol))

# 启动工作流
await workflow.start("实现一个计算器")

# 在回调中处理用户确认
def on_plan_ready(agent_name, stage_name, plan):
    print(f"计划: {plan}")
    user_input = input("是否批准? (y/n): ")
    if user_input == 'y':
        await workflow.approve_plan()
    else:
        await workflow.reject_plan()
```

### 方式2: WebSocket API

**服务器端**:
```python
from fastapi import FastAPI, WebSocket
from src.api.interactive_workflow_ws import interactive_workflow_endpoint

app = FastAPI()

@app.websocket("/ws/interactive-workflow")
async def websocket_endpoint(websocket: WebSocket):
    await interactive_workflow_endpoint(websocket)
```

**客户端**:
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/interactive-workflow");

// 启动任务
ws.send(JSON.stringify({
    type: "start",
    task: "实现一个待办事项管理系统"
}));

// 接收计划
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    if (message.type === "plan_ready") {
        console.log("Agent:", message.agent_name);
        console.log("计划:", message.plan);

        // 用户确认后批准
        ws.send(JSON.stringify({
            type: "approve"
        }));
    }

    if (message.type === "stage_complete") {
        console.log("完成:", message.agent_name);
    }

    if (message.type === "completed") {
        console.log("项目目录:", message.project_dir);
    }
};
```

## 消息协议

### 客户端 → 服务器

#### 启动任务
```json
{
    "type": "start",
    "task": "任务描述"
}
```

#### 批准计划
```json
{
    "type": "approve",
    "modifications": "可选的修改建议"
}
```

#### 拒绝计划
```json
{
    "type": "reject",
    "reason": "可选的拒绝原因"
}
```

#### 修改并批准
```json
{
    "type": "modify",
    "new_plan": "新的计划内容"
}
```

### 服务器 → 客户端

#### 计划准备好
```json
{
    "type": "plan_ready",
    "agent_name": "需求分析师",
    "stage_name": "阶段1: 需求分析",
    "plan": "## 工作计划\n..."
}
```

#### 阶段完成
```json
{
    "type": "stage_complete",
    "agent_name": "需求分析师",
    "success": true,
    "result": {
        "content": "...",
        "duration": 12.5,
        "saved_files": ["..."],
        "error": null
    }
}
```

#### 进度更新
```json
{
    "type": "progress",
    "current": 2,
    "total": 5,
    "percent": 40,
    "stage": "executing"
}
```

#### 完成
```json
{
    "type": "completed",
    "project_dir": "/path/to/project"
}
```

#### 错误
```json
{
    "type": "error",
    "message": "错误信息"
}
```

## 计划格式

每个Agent生成的计划包含以下部分：

```markdown
## 工作计划

### 1. 分析阶段
- [ ] 分析任务需求
- [ ] 确定工作范围
- [ ] 识别关键要点

### 2. 执行阶段
- [ ] 具体步骤1
- [ ] 具体步骤2
- [ ] 具体步骤3

### 3. 输出阶段
- [ ] 生成文档/代码
- [ ] 验证输出质量
- [ ] 保存到指定目录

### 4. 预期产出
- 文件1: requirements.md - 需求文档
- 文件2: architecture.md - 架构文档

### 5. 预计耗时
约 5-10 分钟
```

## API参考

### InteractiveWorkflow

#### 构造函数
```python
InteractiveWorkflow(
    base_output_dir: Path = None,
    use_existing_project: bool = False,
    max_retry_per_stage: int = 3,
    on_plan_ready: Callable = None,
    on_stage_complete: Callable = None
)
```

#### 方法

**start(task, task_id=None)**
- 启动工作流
- 参数: task (任务描述), task_id (可选)

**approve_plan(modifications=None)**
- 批准当前计划并执行
- 参数: modifications (可选的修改建议)

**reject_plan(reason=None)**
- 拒绝当前计划，重新生成
- 参数: reason (可选的拒绝原因)

**modify_and_approve(new_plan)**
- 修改计划并批准
- 参数: new_plan (新的计划内容)

**get_progress()**
- 获取工作流进度
- 返回: 进度信息字典

**get_all_plans()**
- 获取所有计划
- 返回: AgentPlan列表

**get_project_dir()**
- 获取项目目录
- 返回: Path对象

#### 属性

**current_stage**
- 当前阶段 (WorkflowStage枚举)

**current_plan**
- 当前计划 (AgentPlan对象)

**agents**
- Agent列表

## 示例

### 完整示例

参见 `examples/interactive_workflow_example.py`

运行示例:
```bash
python examples/interactive_workflow_example.py
```

### Web界面示例

1. 启动服务器:
```bash
python -m src.api.server
```

2. 连接WebSocket:
```javascript
const ws = new WebSocket("ws://localhost:8000/ws/interactive-workflow");
```

3. 发送任务并处理计划确认

## 与自动工作流的对比

| 特性 | 自动工作流 | 交互式工作流 |
|------|-----------|-------------|
| 用户控制 | ❌ 无 | ✅ 每步确认 |
| 计划可见性 | ❌ 不可见 | ✅ 完全可见 |
| 修改能力 | ❌ 不可修改 | ✅ 可修改 |
| 执行速度 | ✅ 快速 | 🟡 需等待确认 |
| 适用场景 | 简单任务 | 复杂/重要任务 |

## 最佳实践

1. **仔细审查计划** - 确保Agent理解了任务需求
2. **提供具体的修改建议** - 如果计划不够详细，提供补充信息
3. **拒绝不合理的计划** - 如果计划偏离目标，及时拒绝
4. **保存重要计划** - 可以将计划保存为文档供后续参考

## 故障排除

### 问题: 计划生成失败
**解决**: 检查API密钥配置，确保网络连接正常

### 问题: WebSocket连接断开
**解决**: 检查服务器状态，重新建立连接

### 问题: 计划内容不够详细
**解决**: 使用 `reject_plan()` 拒绝并重新生成，或使用 `approve_plan(modifications="...")` 提供补充信息

## 未来改进

- [ ] 支持计划模板
- [ ] 支持计划历史记录
- [ ] 支持多用户协作审批
- [ ] 支持计划版本对比
- [ ] 集成项目管理工具
