"""
API路由

定义REST API端点。
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from src.api.schemas import (
    AgentControlRequest,
    AgentControlResponse,
    AgentProgress,
    HealthResponse,
    TaskCreateRequest,
    TaskCreateResponse,
    TaskProgressResponse,
    TaskResultResponse,
    TaskStatus,
    TaskStatusResponse,
)
from src.communication.notification import NotificationManager

router = APIRouter()

_tasks: Dict[str, Dict] = {}
_notification_manager: Optional[NotificationManager] = None


def set_notification_manager(manager: NotificationManager):
    """设置通知管理器"""
    global _notification_manager
    _notification_manager = manager


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="ok",
        version="1.0.0",
        uptime=(datetime.now() - _start_time).total_seconds() if "_start_time" in globals() else 0.0
    )


_start_time = datetime.now()


@router.post("/task", response_model=TaskCreateResponse)
async def create_task(request: TaskCreateRequest):
    """创建新任务"""
    task_id = str(uuid.uuid4())[:8]
    
    _tasks[task_id] = {
        "task_id": task_id,
        "task": request.task,
        "status": TaskStatus.PENDING,
        "progress": 0.0,
        "current_agent": None,
        "agents": request.agents or ["analyst", "coder"],
        "config": request.config or {},
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }
    
    asyncio.create_task(_run_task(task_id))
    
    return TaskCreateResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="任务已创建"
    )


@router.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str):
    """获取任务（简化端点）"""
    return await get_task_status(task_id)


@router.get("/task/{task_id}/status", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = _tasks[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=task["progress"],
        current_agent=task.get("current_agent"),
        message=task.get("message"),
        created_at=task["created_at"],
        updated_at=task["updated_at"]
    )


@router.get("/task/{task_id}/progress", response_model=TaskProgressResponse)
async def get_task_progress(task_id: str):
    """获取任务进度"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = _tasks[task_id]
    agents_progress = task.get("agents_progress", [])
    
    return TaskProgressResponse(
        task_id=task_id,
        progress=task["progress"],
        agents=[AgentProgress(**a) for a in agents_progress],
        started_at=task["created_at"],
        elapsed_seconds=(datetime.now() - task["created_at"]).total_seconds()
    )


@router.get("/task/{task_id}/result", response_model=TaskResultResponse)
async def get_task_result(task_id: str):
    """获取任务结果"""
    if task_id not in _tasks:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = _tasks[task_id]
    
    if task["status"] not in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
        raise HTTPException(status_code=400, detail="任务尚未完成")
    
    return TaskResultResponse(
        task_id=task_id,
        success=task["status"] == TaskStatus.COMPLETED,
        content=task.get("content", ""),
        saved_files=task.get("saved_files", []),
        duration=(task["updated_at"] - task["created_at"]).total_seconds(),
        agent_results=task.get("agent_results", [])
    )


@router.post("/agent/control", response_model=AgentControlResponse)
async def control_agent(request: AgentControlRequest):
    """控制Agent"""
    valid_actions = ["pause", "resume", "stop"]
    if request.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"无效动作: {request.action}")
    
    return AgentControlResponse(
        success=True,
        message=f"Agent控制命令已发送: {request.action}"
    )


@router.get("/protocols")
async def list_protocols():
    """列出可用协议"""
    return {
        "protocols": [
            {"name": "deepseek", "description": "DeepSeek API"},
            {"name": "qwen", "description": "通义千问 API"},
            {"name": "glm", "description": "智谱 GLM API"},
            {"name": "minimax", "description": "MiniMax API"},
        ]
    }


@router.get("/agents")
async def list_agents():
    """列出可用Agent"""
    return {
        "agents": [
            {"name": "analyst", "description": "需求分析师"},
            {"name": "architect", "description": "系统架构师"},
            {"name": "coder", "description": "代码开发者"},
            {"name": "tester", "description": "测试员"},
        ]
    }


async def _run_task(task_id: str):
    """执行任务"""
    task = _tasks[task_id]
    task["status"] = TaskStatus.RUNNING
    task["updated_at"] = datetime.now()
    
    try:
        from src.core.workflow import Workflow
        from src.utils.config import Config
        from src.protocols import create_protocol
        
        config = Config.load()
        protocol_config = config.get_protocol("deepseek")
        
        if not protocol_config:
            raise ValueError("DeepSeek协议未配置")
        
        protocol = create_protocol(
            "deepseek",
            api_key=protocol_config.get("api_key", ""),
            base_url=protocol_config.get("base_url", "https://api.deepseek.com"),
            default_model=protocol_config.get("default_model", "deepseek-chat")
        )
        
        workflow = Workflow(base_output_dir=config.output_dir)
        
        agent_configs = {
            "analyst": ("AnalystAgent", "需求分析师"),
            "architect": ("ArchitectAgent", "系统架构师"),
            "coder": ("CoderAgent", "程序员"),
            "tester": ("TesterAgent", "测试员"),
        }
        
        for agent_key in task["agents"]:
            if agent_key in agent_configs:
                agent_class_name, agent_name = agent_configs[agent_key]
                
                from src.agents import AnalystAgent, ArchitectAgent, CoderAgent, TesterAgent
                agent_classes = {
                    "AnalystAgent": AnalystAgent,
                    "ArchitectAgent": ArchitectAgent,
                    "CoderAgent": CoderAgent,
                    "TesterAgent": TesterAgent,
                }
                
                agent_class = agent_classes.get(agent_class_name)
                if agent_class:
                    agent = agent_class(protocol=protocol)
                    workflow.add_agent(agent)
        
        def on_progress(agent_name: str, status: str, progress: float):
            task["current_agent"] = agent_name
            task["progress"] = progress
            task["updated_at"] = datetime.now()
            
            if _notification_manager:
                asyncio.create_task(
                    _notification_manager.broadcast({
                        "type": "progress",
                        "task_id": task_id,
                        "agent": agent_name,
                        "status": status,
                        "progress": progress
                    })
                )
        
        workflow.on_progress = on_progress
        
        result = await workflow.run(task["task"])
        
        task["status"] = TaskStatus.COMPLETED if result.success else TaskStatus.FAILED
        task["progress"] = 100.0
        task["content"] = result.content
        task["saved_files"] = result.saved_files
        task["updated_at"] = datetime.now()
        
        if _notification_manager:
            await _notification_manager.broadcast({
                "type": "complete",
                "task_id": task_id,
                "success": result.success
            })
        
    except Exception as e:
        task["status"] = TaskStatus.FAILED
        task["message"] = str(e)
        task["updated_at"] = datetime.now()
        
        if _notification_manager:
            await _notification_manager.broadcast({
                "type": "error",
                "task_id": task_id,
                "error": str(e)
            })
