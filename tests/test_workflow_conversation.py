"""
工作流对话状态机测试
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import os

from src.core.workflow_conversation import (
    WorkflowConversationMachine,
    WorkflowState,
    RequirementSession,
    ConversationTurn,
)
from src.core.message import Message


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


class TestRefactoredMethods:
    """测试重构后的私有方法"""
    
    def test_record_user_message(self):
        """测试记录用户消息"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        machine._session = RequirementSession(session_id="test")
        
        machine._record_user_message("测试消息")
        
        assert len(machine._session.conversation_history) == 1
        assert machine._session.conversation_history[0].content == "测试消息"
        assert machine._session.conversation_history[0].role == "user"
    
    def test_record_user_message_appends(self):
        """测试记录多条用户消息"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        machine._session = RequirementSession(session_id="test")
        
        machine._record_user_message("第一条消息")
        machine._record_user_message("第二条消息")
        
        assert len(machine._session.conversation_history) == 2
        assert machine._session.conversation_history[0].content == "第一条消息"
        assert machine._session.conversation_history[1].content == "第二条消息"
    
    def test_should_execute_workflow_true_in_confirming_state(self):
        """测试在确认状态下应该执行工作流"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        machine._state = WorkflowState.CONFIRMING
        
        assert machine._should_execute_workflow("确认") == True
        assert machine._should_execute_workflow("开始执行") == True
        assert machine._should_execute_workflow("就这样") == True
        assert machine._should_execute_workflow("可以开始") == True
        assert machine._should_execute_workflow("执行吧") == True
        assert machine._should_execute_workflow("开始开发") == True
        assert machine._should_execute_workflow("没问题") == True
        assert machine._should_execute_workflow("好的开始") == True
    
    def test_should_execute_workflow_false_in_analyzing_state(self):
        """测试在分析状态下不应该执行工作流"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        machine._state = WorkflowState.ANALYZING
        
        assert machine._should_execute_workflow("确认") == False
        assert machine._should_execute_workflow("开始执行") == False
    
    def test_should_execute_workflow_false_without_keyword(self):
        """测试没有关键词时不执行工作流"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        machine._state = WorkflowState.CONFIRMING
        
        assert machine._should_execute_workflow("普通消息") == False
        assert machine._should_execute_workflow("继续讨论") == False
    
    def test_check_requirement_confirmed_true(self):
        """测试检测到需求已确认"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        
        assert machine._check_requirement_confirmed("需求已确认") == True
        assert machine._check_requirement_confirmed("需求已确认，请查看") == True
        assert machine._check_requirement_confirmed("以上是需求，需求已确认。") == True
    
    def test_check_requirement_confirmed_false(self):
        """测试未检测到需求确认"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        
        assert machine._check_requirement_confirmed("还在分析中") == False
        assert machine._check_requirement_confirmed("需求文档") == False
        assert machine._check_requirement_confirmed("") == False
    
    def test_check_requirements_file_written_true(self):
        """测试检测到需求文件写入成功"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        
        tool_calls = [
            {"name": "file_write", "params": {"file_path": "requirements/requirements.md", "content": "test"}}
        ]
        assert machine._check_requirements_file_written(tool_calls) == True
        
        tool_calls = [
            {"name": "file_write", "params": {"file_path": "requirements/spec.md", "content": "test"}}
        ]
        assert machine._check_requirements_file_written(tool_calls) == True
    
    def test_check_requirements_file_written_false(self):
        """测试未检测到需求文件写入"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        
        tool_calls = [
            {"name": "file_read", "params": {"file_path": "requirements/test.md"}}
        ]
        assert machine._check_requirements_file_written(tool_calls) == False
        
        tool_calls = [
            {"name": "file_write", "params": {"file_path": "code/main.py", "content": "test"}}
        ]
        assert machine._check_requirements_file_written(tool_calls) == False
        
        tool_calls = [
            {"name": "file_write", "params": {"file_path": "test.txt", "content": "test"}}
        ]
        assert machine._check_requirements_file_written(tool_calls) == False
        
        tool_calls = []
        assert machine._check_requirements_file_written(tool_calls) == False
    
    def test_load_confirmed_requirements_with_file(self):
        """测试从文件加载已确认的需求"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            requirements_dir = project_path / "requirements"
            requirements_dir.mkdir()
            req_file = requirements_dir / "requirements.md"
            req_file.write_text("# 测试需求\n\n这是测试需求内容", encoding='utf-8')
            
            machine._project_path = project_path
            machine._load_confirmed_requirements()
            
            assert machine._confirmed_requirements == "# 测试需求\n\n这是测试需求内容"
    
    def test_load_confirmed_requirements_without_file(self):
        """测试没有需求文件时的加载"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            machine._project_path = project_path
            machine._load_confirmed_requirements()
            
            assert machine._confirmed_requirements == ""
    
    def test_load_confirmed_requirements_without_project_path(self):
        """测试没有项目路径时的加载"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        machine._project_path = None
        
        machine._load_confirmed_requirements()
        
        assert machine._confirmed_requirements == ""
    
    def test_build_conversation_messages(self):
        """测试构建对话消息列表"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        machine._session = RequirementSession(session_id="test")
        machine._session.conversation_history = [
            ConversationTurn(role="user", content="用户消息"),
            ConversationTurn(role="analyst", content="分析师回复"),
        ]
        
        from src.agents.analyst import AnalystAgent
        machine._analyst = AnalystAgent(protocol=protocol)
        
        messages = machine._build_conversation_messages()
        
        assert len(messages) == 3
        assert messages[0].role == "system"
        assert messages[1].role == "user"
        assert messages[1].content == "用户消息"
        assert messages[2].role == "assistant"
        assert messages[2].content == "分析师回复"
    
    def test_emit_tool_call_messages(self):
        """测试发送工具调用消息"""
        protocol = MockProtocol()
        messages = []
        
        def on_message(role, content):
            messages.append((role, content))
        
        machine = WorkflowConversationMachine(protocol=protocol, on_message=on_message)
        
        tool_calls = [
            {"name": "file_read", "params": {"file_path": "test.py"}},
            {"name": "file_write", "params": {"file_path": "output.txt", "content": "hello"}},
        ]
        
        machine._emit_tool_call_messages(tool_calls)
        
        assert len(messages) == 2
        assert messages[0][0] == "tool"
        assert "file_read" in messages[0][1]
        assert messages[1][0] == "tool"
        assert "file_write" in messages[1][1]
    
    def test_emit_tool_result_messages(self):
        """测试发送工具结果消息"""
        protocol = MockProtocol()
        messages = []
        
        def on_message(role, content):
            messages.append((role, content))
        
        machine = WorkflowConversationMachine(protocol=protocol, on_message=on_message)
        
        tool_results = [
            {"name": "file_read", "result": "文件内容"},
            {"name": "file_write", "result": "写入成功"},
        ]
        
        machine._emit_tool_result_messages(tool_results)
        
        assert len(messages) == 2
        assert messages[0][0] == "tool_result"
        assert "文件内容" in messages[0][1]
    
    def test_emit_tool_result_messages_truncation(self):
        """测试工具结果消息截断"""
        protocol = MockProtocol()
        messages = []
        
        def on_message(role, content):
            messages.append((role, content))
        
        machine = WorkflowConversationMachine(protocol=protocol, on_message=on_message)
        
        long_result = "x" * 1000
        tool_results = [{"name": "test", "result": long_result}]
        
        machine._emit_tool_result_messages(tool_results)
        
        assert len(messages) == 1
        assert "已截断" in messages[0][1]
        assert len(messages[0][1]) < len(long_result)


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
    
    def test_set_project_path(self):
        """测试设置项目路径"""
        protocol = MockProtocol()
        machine = WorkflowConversationMachine(protocol=protocol)
        
        test_path = Path("/test/project")
        machine.set_project_path(test_path)
        
        assert machine.project_path == test_path


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
