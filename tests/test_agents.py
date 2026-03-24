"""
Agent测试模块
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.base_agent import BaseAgent, AgentState
from src.agents.analyst import AnalystAgent
from src.agents.architect import ArchitectAgent
from src.agents.coder import CoderAgent
from src.agents.tester import TesterAgent


class MockProtocol:
    """模拟协议"""
    
    def __init__(self):
        self.base_url = "https://mock.api"
        self.api_key = "mock_key"
        self.default_model = "mock-model"
    
    async def chat(self, messages, model=None, stream=True, **kwargs):
        from src.core.message import ChatChunk
        yield ChatChunk(content="测试响应")


class TestBaseAgent:
    """Agent基类测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = MockProtocol()
        agent = AnalystAgent(protocol=protocol)
        
        assert agent.name == "需求分析师"
        assert agent.state == AgentState.IDLE
        assert agent.protocol == protocol
    
    def test_info(self):
        """测试获取Agent信息"""
        protocol = MockProtocol()
        agent = AnalystAgent(protocol=protocol, model="test-model")
        
        info = agent.info
        assert info["name"] == "需求分析师"
        assert info["state"] == "idle"
        assert info["model"] == "test-model"


class TestAnalystAgent:
    """需求分析师测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = MockProtocol()
        agent = AnalystAgent(protocol=protocol)
        
        assert agent.name == "需求分析师"
        assert agent.temperature == 0.7
        assert "需求分析师" in agent.system_prompt


class TestArchitectAgent:
    """系统架构师测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = MockProtocol()
        agent = ArchitectAgent(protocol=protocol)
        
        assert agent.name == "系统架构师"
        assert agent.temperature == 0.5
        assert "系统架构师" in agent.system_prompt


class TestCoderAgent:
    """代码开发者测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = MockProtocol()
        agent = CoderAgent(protocol=protocol)
        
        assert agent.name == "代码开发者"
        assert agent.temperature == 0.3
        assert "代码开发者" in agent.system_prompt


class TestTesterAgent:
    """测试员测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = MockProtocol()
        agent = TesterAgent(protocol=protocol)
        
        assert agent.name == "测试员"
        assert agent.temperature == 0.4
        assert "测试工程师" in agent.system_prompt


@pytest.mark.asyncio
class TestAgentExecution:
    """Agent执行测试"""
    
    async def test_execute_success(self):
        """测试成功执行"""
        protocol = MockProtocol()
        agent = AnalystAgent(protocol=protocol)
        
        result = await agent.execute("测试任务")
        
        assert result.success
        assert result.agent_name == "需求分析师"
        assert result.content == "测试响应"
    
    async def test_execute_with_callback(self):
        """测试带回调执行"""
        protocol = MockProtocol()
        agent = AnalystAgent(protocol=protocol)
        
        chunks = []
        agent.on_chunk(lambda c: chunks.append(c))
        
        result = await agent.execute("测试任务")
        
        assert len(chunks) > 0
        assert result.success
