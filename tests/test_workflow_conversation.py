"""
工作流对话状态机测试
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from src.core.workflow_conversation import (
    WorkflowConversationMachine,
    WorkflowState,
    RequirementSession,
    ConversationTurn,
)


class MockProtocol:
    """模拟协议"""
    
    def __init__(self):
        self.base_url = "https://mock.api"
        self.api_key = "mock_key"
        self.default_model = "mock-model"
    
    async def chat(self, messages, model=None, stream=True, **kwargs):
        from src.core.message import ChatChunk
        
        content = "你好！请告诉我你想要开发什么项目？"
        
        for msg in messages:
            if msg.role == "user":
                if "确认" in msg.content or "开始执行" in msg.content:
                    content = """
## 需求确认文档

### 项目名称
测试项目

### 功能列表
1. 用户管理 - 优先级: 高
2. 登录功能 - 优先级: 高

### 技术要求
- Python + Flask

需求已确认，等待执行。
"""
                elif msg.content and "需求分析师" not in msg.content:
                    content = """
## 需求确认文档

### 项目名称
测试项目

### 功能列表
1. 用户管理 - 优先级: 高
2. 登录功能 - 优先级: 高

### 技术要求
- Python + Flask

需求已确认，等待执行。
"""
        
        yield ChatChunk(content=content)


class TestWorkflowState:
    """工作流状态测试"""
    
    def test_state_values(self):
        """测试状态值"""
        assert WorkflowState.IDLE.value == "idle"
        assert WorkflowState.ANALYZING.value == "analyzing"
        assert WorkflowState.CONFIRMING.value == "confirming"
        assert WorkflowState.EXECUTING.value == "executing"
        assert WorkflowState.COMPLETED.value == "completed"
        assert WorkflowState.ERROR.value == "error"


class TestConversationTurn:
    """对话轮次测试"""
    
    def test_creation(self):
        """测试创建对话轮次"""
        turn = ConversationTurn(role="user", content="测试消息")
        assert turn.role == "user"
        assert turn.content == "测试消息"
        assert turn.timestamp is not None


class TestRequirementSession:
    """需求会话测试"""
    
    def test_creation(self):
        """测试创建需求会话"""
        session = RequirementSession(session_id="test123")
        assert session.session_id == "test123"
        assert len(session.conversation_history) == 0
        assert session.confirmed == False


class TestWorkflowConversationMachine:
    """工作流对话状态机测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        
        assert machine.state == WorkflowState.IDLE
        assert machine.session is None
        assert machine.is_active() == False
        assert machine.can_send_message() == False
    
    @pytest.mark.asyncio
    async def test_start_session(self):
        """测试开始会话"""
        protocol = MockProtocol()
        messages = []
        
        def on_message(role, content):
            messages.append((role, content))
        
        machine = WorkflowConversationMachine(
            protocol=protocol,
            on_message=on_message
        )
        
        await machine.start_session()
        
        assert machine.state == WorkflowState.ANALYZING
        assert machine.is_active() == True
        assert machine.can_send_message() == True
        assert len(messages) > 0
        assert messages[0][0] == "analyst"
        assert "需求分析师" in messages[0][1]
    
    @pytest.mark.asyncio
    async def test_conversation_flow(self):
        """测试对话流程"""
        protocol = MockProtocol()
        messages = []
        
        def on_message(role, content):
            messages.append((role, content))
        
        machine = WorkflowConversationMachine(
            protocol=protocol,
            on_message=on_message
        )
        
        await machine.start_session()
        
        await machine.send_message("我想开发一个用户管理系统")
        
        assert len(messages) > 1
    
    @pytest.mark.asyncio
    async def test_confirm_and_execute(self):
        """测试确认后执行"""
        protocol = MockProtocol()
        messages = []
        
        def on_message(role, content):
            messages.append((role, content))
        
        def on_state_change(state):
            messages.append(("state", state.value))
        
        def on_progress(agent_name, status, progress):
            messages.append(("progress", (agent_name, status)))
        
        machine = WorkflowConversationMachine(
            protocol=protocol,
            on_message=on_message,
            on_state_change=on_state_change,
            on_progress=on_progress
        )
        
        await machine.start_session()
        
        await machine.send_message("我想开发一个用户管理系统")
        
        assert machine.state == WorkflowState.CONFIRMING
        
        await machine.send_message("确认")
        
        assert machine.state in [WorkflowState.EXECUTING, WorkflowState.COMPLETED, WorkflowState.ERROR]
    
    def test_cancel(self):
        """测试取消"""
        protocol = MockProtocol()
        messages = []
        
        def on_message(role, content):
            messages.append((role, content))
        
        machine = WorkflowConversationMachine(
            protocol=protocol,
            on_message=on_message
        )
        
        machine._state = WorkflowState.ANALYZING
        machine.cancel()
        
        assert machine.state == WorkflowState.IDLE
        assert machine.is_active() == False
        assert len(messages) == 1
        assert messages[0][0] == "system"


class TestWorkflowIntegration:
    """工作流集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_conversation_flow(self):
        """测试完整对话流程"""
        protocol = MockProtocol()
        states = []
        
        def on_state_change(state):
            states.append(state)
        
        machine = WorkflowConversationMachine(
            protocol=protocol,
            on_state_change=on_state_change
        )
        
        await machine.start_session()
        assert WorkflowState.ANALYZING in states
        
        await machine.send_message("开发一个博客系统")
        
        assert machine.state == WorkflowState.CONFIRMING
        
        await machine.send_message("确认")
        
        assert machine.state in [WorkflowState.EXECUTING, WorkflowState.COMPLETED, WorkflowState.ERROR]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
