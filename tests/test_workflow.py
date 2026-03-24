"""
工作流测试模块
"""

import pytest
from unittest.mock import MagicMock

from src.core.workflow import Workflow
from src.core.context import Context, TaskResult
from src.core.message import Message


class MockProtocol:
    """模拟协议"""
    
    def __init__(self):
        self.base_url = "https://mock.api"
        self.api_key = "mock_key"
        self.default_model = "mock-model"
    
    async def chat(self, messages, model=None, stream=True, **kwargs):
        from src.core.message import ChatChunk
        yield ChatChunk(content="测试响应")


class TestWorkflow:
    """工作流测试"""
    
    def test_init(self):
        """测试初始化"""
        workflow = Workflow()
        assert len(workflow.agents) == 0
    
    def test_add_agent(self):
        """测试添加Agent"""
        workflow = Workflow()
        protocol = MockProtocol()
        
        from src.agents.analyst import AnalystAgent
        agent = AnalystAgent(protocol=protocol)
        
        workflow.add_agent(agent)
        
        assert len(workflow.agents) == 1
        assert workflow.agents[0] == agent
    
    def test_get_agent_names(self):
        """测试获取Agent名称列表"""
        workflow = Workflow()
        protocol = MockProtocol()
        
        from src.agents.analyst import AnalystAgent
        from src.agents.coder import CoderAgent
        
        workflow.add_agent(AnalystAgent(protocol=protocol))
        workflow.add_agent(CoderAgent(protocol=protocol))
        
        names = workflow.get_agent_names()
        
        assert len(names) == 2
        assert "需求分析师" in names
        assert "代码开发者" in names


class TestContext:
    """上下文测试"""
    
    def test_init(self):
        """测试初始化"""
        context = Context(task_id="test_001")
        assert context.task_id == "test_001"
        assert len(context.messages) == 0
    
    def test_add_message(self):
        """测试添加消息"""
        context = Context(task_id="test_001")
        message = Message(role="user", content="测试消息")
        
        context.add_message(message)
        
        assert len(context.messages) == 1
        assert context.messages[0].content == "测试消息"
    
    def test_set_get(self):
        """测试设置和获取数据"""
        context = Context(task_id="test_001")
        
        context.set("key1", "value1")
        context.set("key2", {"nested": "value"})
        
        assert context.get("key1") == "value1"
        assert context.get("key2")["nested"] == "value"
        assert context.get("nonexistent", "default") == "default"


class TestTaskResult:
    """任务结果测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = TaskResult(
            success=True,
            content="测试内容",
            agent_id="test_id",
            agent_name="测试Agent",
            duration=1.5
        )
        
        assert result.success
        assert result.content == "测试内容"
        assert result.error is None
    
    def test_failure_result(self):
        """测试失败结果"""
        result = TaskResult(
            success=False,
            content="",
            agent_id="test_id",
            agent_name="测试Agent",
            duration=0.5,
            error="测试错误"
        )
        
        assert not result.success
        assert result.error == "测试错误"
