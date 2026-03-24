"""
核心模块
包含Agent基类、消息、上下文、工作流等核心组件
"""

from src.core.message import Message
from src.core.context import Context, TaskResult
from src.core.workflow_conversation import (
    WorkflowConversationMachine,
    WorkflowState,
    RequirementSession,
    ConversationTurn,
)

__all__ = [
    "Message",
    "Context",
    "TaskResult",
    "WorkflowConversationMachine",
    "WorkflowState",
    "RequirementSession",
    "ConversationTurn",
]
