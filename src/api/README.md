# api - 移动端API

本目录包含移动端通信的API服务。

## 文件说明

| 文件 | 职责 |
|------|------|
| `server.py` | FastAPI服务启动和配置 |
| `routes.py` | API路由定义 |
| `schemas.py` | 请求/响应数据模型 |

## API端点

### REST API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/task` | 创建新任务 |
| GET | `/api/task/status` | 获取当前任务状态 |
| GET | `/api/task/progress` | 获取开发进度 |
| POST | `/api/agent/control` | Agent控制指令 |

### WebSocket

| 路径 | 说明 |
|------|------|
| `/ws/notifications` | 实时通知推送 |

## 数据模型

```python
class TaskCreate(BaseModel):
    requirement: str      # 需求描述
    agents: List[str]     # 使用的Agent列表
    
class TaskStatus(BaseModel):
    task_id: str          # 任务ID
    status: str           # 状态: pending/running/completed/failed
    progress: float       # 进度 0-100
    current_agent: str    # 当前执行的Agent
    result: Optional[str] # 结果（完成后）
```

## 使用示例

```python
# 创建任务
POST /api/task
{
    "requirement": "实现一个用户登录功能",
    "agents": ["analyst", "coder"]
}

# WebSocket连接
ws://localhost:8000/ws/notifications
```

## 开发顺序（MVP之后）

1. `schemas.py` - 数据模型
2. `routes.py` - API路由
3. `server.py` - 服务启动
