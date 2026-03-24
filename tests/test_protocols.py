"""
协议测试模块
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.protocols.base import BaseProtocol
from src.protocols.deepseek import DeepSeekProtocol
from src.protocols.qwen import QwenProtocol
from src.protocols.glm import GLMProtocol
from src.protocols.minimax import MiniMaxProtocol
from src.protocols import create_protocol


class TestProtocolFactory:
    """协议工厂测试"""
    
    def test_create_deepseek_protocol(self):
        """测试创建DeepSeek协议"""
        protocol = create_protocol("deepseek", api_key="test_key")
        assert isinstance(protocol, DeepSeekProtocol)
        assert protocol.api_key == "test_key"
    
    def test_create_qwen_protocol(self):
        """测试创建Qwen协议"""
        protocol = create_protocol("qwen", api_key="test_key")
        assert isinstance(protocol, QwenProtocol)
        assert protocol.api_key == "test_key"
    
    def test_create_glm_protocol(self):
        """测试创建GLM协议"""
        protocol = create_protocol("glm", api_key="test_key")
        assert isinstance(protocol, GLMProtocol)
        assert protocol.api_key == "test_key"
    
    def test_create_minimax_protocol(self):
        """测试创建MiniMax协议"""
        protocol = create_protocol("minimax", api_key="test_key", group_id="test_group")
        assert isinstance(protocol, MiniMaxProtocol)
        assert protocol.api_key == "test_key"
        assert protocol.group_id == "test_group"
    
    def test_create_unknown_protocol(self):
        """测试创建未知协议"""
        with pytest.raises(ValueError):
            create_protocol("unknown")


class TestDeepSeekProtocol:
    """DeepSeek协议测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = DeepSeekProtocol(api_key="test_key")
        assert protocol.base_url == "https://api.deepseek.com"
        assert protocol.default_model == "deepseek-chat"
    
    def test_get_headers(self):
        """测试获取请求头"""
        protocol = DeepSeekProtocol(api_key="test_key")
        headers = protocol.get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_key"
    
    def test_format_messages(self):
        """测试消息格式化"""
        from src.core.message import Message
        
        protocol = DeepSeekProtocol(api_key="test_key")
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi"),
        ]
        
        formatted = protocol.format_messages(messages)
        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"


class TestQwenProtocol:
    """Qwen协议测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = QwenProtocol(api_key="test_key")
        assert protocol.base_url == "https://dashscope.aliyuncs.com/compatible-mode/v1"
        assert protocol.default_model == "qwen-plus"


class TestGLMProtocol:
    """GLM协议测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = GLMProtocol(api_key="test_key")
        assert protocol.base_url == "https://open.bigmodel.cn/api/paas/v4"
        assert protocol.default_model == "glm-4"


class TestMiniMaxProtocol:
    """MiniMax协议测试"""
    
    def test_init(self):
        """测试初始化"""
        protocol = MiniMaxProtocol(api_key="test_key", group_id="test_group")
        assert protocol.base_url == "https://api.minimax.chat/v1"
        assert protocol.default_model == "abab6.5-chat"
        assert protocol.group_id == "test_group"
    
    def test_get_headers(self):
        """测试获取请求头（包含group_id）"""
        protocol = MiniMaxProtocol(api_key="test_key", group_id="test_group")
        headers = protocol.get_headers()
        assert "X-Group-Id" in headers
        assert headers["X-Group-Id"] == "test_group"
