"""
API数据模型

定义API请求和响应的数据结构。
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStatus(str, Enum):
    """Agent状态"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class TaskCreateRequest(BaseModel):
    """创建任务请求"""
    task: str = Field(..., description="任务描述")
    agents: Optional[List[str]] = Field(None, description="指定Agent列表")
    config: Optional[Dict[str, Any]] = Field(None, description="任务配置")


class TaskCreateResponse(BaseModel):
    """创建任务响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="任务状态")
    message: str = Field(default="任务已创建", description="消息")


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str = Field(..., description="任务ID")
    status: TaskStatus = Field(..., description="任务状态")
    progress: float = Field(default=0.0, description="进度(0-100)")
    current_agent: Optional[str] = Field(None, description="当前执行的Agent")
    message: Optional[str] = Field(None, description="状态消息")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")


class TaskProgressResponse(BaseModel):
    """任务进度响应"""
    task_id: str = Field(..., description="任务ID")
    progress: float = Field(..., description="总进度(0-100)")
    agents: List[AgentProgress] = Field(default_factory=list, description="各Agent进度")
    started_at: datetime = Field(default_factory=datetime.now, description="开始时间")
    elapsed_seconds: float = Field(default=0.0, description="已用时间(秒)")


class AgentProgress(BaseModel):
    """Agent进度"""
    name: str = Field(..., description="Agent名称")
    status: AgentStatus = Field(..., description="状态")
    progress: float = Field(default=0.0, description="进度(0-100)")
    message: Optional[str] = Field(None, description="状态消息")


class TaskResultResponse(BaseModel):
    """任务结果响应"""
    task_id: str = Field(..., description="任务ID")
    success: bool = Field(..., description="是否成功")
    content: str = Field(default="", description="最终输出内容")
    saved_files: List[str] = Field(default_factory=list, description="保存的文件列表")
    duration: float = Field(default=0.0, description="总耗时(秒)")
    agent_results: List[AgentResult] = Field(default_factory=list, description="各Agent结果")


class AgentResult(BaseModel):
    """Agent结果"""
    agent_name: str = Field(..., description="Agent名称")
    success: bool = Field(..., description="是否成功")
    content: str = Field(default="", description="输出内容")
    duration: float = Field(default=0.0, description="耗时(秒)")
    saved_files: List[str] = Field(default_factory=list, description="保存的文件")


class AgentControlRequest(BaseModel):
    """Agent控制请求"""
    action: str = Field(..., description="动作: pause/resume/stop")
    agent_name: Optional[str] = Field(None, description="指定Agent名称")


class AgentControlResponse(BaseModel):
    """Agent控制响应"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(default="", description="消息")


class NotificationMessage(BaseModel):
    """通知消息"""
    type: str = Field(..., description="消息类型: progress/complete/error")
    task_id: str = Field(..., description="任务ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="消息数据")
    timestamp: datetime = Field(default_factory=datetime.now, description="时间戳")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str = Field(default="ok", description="服务状态")
    version: str = Field(default="1.0.0", description="版本号")
    uptime: float = Field(default=0.0, description="运行时间(秒)")
