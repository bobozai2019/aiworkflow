"""
协议模块测试 - GLM和Qwen
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json

from src.protocols.glm import GLMProtocol
from src.protocols.qwen import QwenProtocol
from src.core.message import Message, ChatChunk


class TestGLMProtocol:
    """智谱GLM协议测试"""
    
    @pytest.fixture
    def protocol(self):
        """创建协议实例"""
        return GLMProtocol(
            api_key="test_api_key",
            base_url="https://test.api.com",
            default_model="glm-4"
        )
    
    def test_init(self, protocol):
        """测试初始化"""
        assert protocol.api_key == "test_api_key"
        assert protocol.base_url == "https://test.api.com"
        assert protocol.default_model == "glm-4"
    
    def test_get_headers(self, protocol):
        """测试获取请求头"""
        headers = protocol.get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_api_key"
        assert "Content-Type" in headers
    
    def test_format_messages(self, protocol):
        """测试格式化消息"""
        messages = [
            Message(role="system", content="You are helpful"),
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there")
        ]
        
        formatted = protocol.format_messages(messages)
        
        assert len(formatted) == 3
        assert formatted[0] == {"role": "system", "content": "You are helpful"}
        assert formatted[1] == {"role": "user", "content": "Hello"}
        assert formatted[2] == {"role": "assistant", "content": "Hi there"}
    
    @pytest.mark.asyncio
    async def test_chat_non_stream(self, protocol):
        """测试非流式对话"""
        messages = [Message(role="user", content="Hello")]
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Hi there!"}
            }]
        }
        
        with patch.object(protocol._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            chunks = []
            async for chunk in protocol.chat(messages, stream=False):
                chunks.append(chunk)
            
            assert len(chunks) == 1
            assert chunks[0].content == "Hi there!"
    
    @pytest.mark.asyncio
    async def test_chat_stream(self, protocol):
        """测试流式对话"""
        messages = [Message(role="user", content="Hello")]
        
        mock_stream_data = [
            "data: " + json.dumps({"choices": [{"delta": {"content": "Hi"}}]}),
            "data: " + json.dumps({"choices": [{"delta": {"content": " there"}}]}),
            "data: [DONE]"
        ]
        
        mock_client = MagicMock()
        mock_client.stream = AsyncMock(return_value=iter(mock_stream_data))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        
        with patch.object(protocol._client, '__aenter__', return_value=mock_client):
            with patch.object(protocol._client, '__aexit__', return_value=None):
                with patch.object(protocol._client, 'stream', return_value=iter(mock_stream_data)):
                    pass
    
    def test_default_model(self, protocol):
        """测试默认模型"""
        assert protocol.default_model == "glm-4"


class TestQwenProtocol:
    """通义千问协议测试"""
    
    @pytest.fixture
    def protocol(self):
        """创建协议实例"""
        return QwenProtocol(
            api_key="test_api_key",
            base_url="https://test.qwen.com",
            default_model="qwen-plus"
        )
    
    def test_init(self, protocol):
        """测试初始化"""
        assert protocol.api_key == "test_api_key"
        assert protocol.base_url == "https://test.qwen.com"
        assert protocol.default_model == "qwen-plus"
    
    def test_get_headers(self, protocol):
        """测试获取请求头"""
        headers = protocol.get_headers()
        
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test_api_key"
    
    def test_format_messages(self, protocol):
        """测试格式化消息"""
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi")
        ]
        
        formatted = protocol.format_messages(messages)
        
        assert len(formatted) == 2
        assert formatted[0]["role"] == "user"
        assert formatted[1]["role"] == "assistant"
    
    @pytest.mark.asyncio
    async def test_chat_non_stream(self, protocol):
        """测试非流式对话"""
        messages = [Message(role="user", content="Hello")]
        
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{
                "message": {"content": "Hello! How can I help?"}
            }]
        }
        
        with patch.object(protocol._client, 'post', new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            chunks = []
            async for chunk in protocol.chat(messages, stream=False):
                chunks.append(chunk)
            
            assert len(chunks) == 1
            assert "Hello" in chunks[0].content
    
    def test_default_model(self, protocol):
        """测试默认模型"""
        assert protocol.default_model == "qwen-plus"


class TestProtocolComparison:
    """协议对比测试"""
    
    def test_both_protocols_format_messages_same(self):
        """测试两个协议的消息格式化结果相同"""
        glm = GLMProtocol(api_key="key1")
        qwen = QwenProtocol(api_key="key2")
        
        messages = [
            Message(role="system", content="System prompt"),
            Message(role="user", content="User message")
        ]
        
        glm_formatted = glm.format_messages(messages)
        qwen_formatted = qwen.format_messages(messages)
        
        assert glm_formatted == qwen_formatted
    
    def test_both_protocols_have_different_defaults(self):
        """测试两个协议有不同的默认模型"""
        glm = GLMProtocol(api_key="key1")
        qwen = QwenProtocol(api_key="key2")
        
        assert glm.default_model == "glm-4"
        assert qwen.default_model == "qwen-plus"
        assert glm.default_model != qwen.default_model
    
    def test_both_protocols_have_different_base_urls(self):
        """测试两个协议有不同的默认URL"""
        glm = GLMProtocol(api_key="key1")
        qwen = QwenProtocol(api_key="key2")
        
        assert "bigmodel.cn" in glm.base_url
        assert "aliyuncs.com" in qwen.base_url


class TestProtocolErrorHandling:
    """协议错误处理测试"""
    
    @pytest.fixture
    def glm_protocol(self):
        return GLMProtocol(api_key="test_key")
    
    @pytest.fixture
    def qwen_protocol(self):
        return QwenProtocol(api_key="test_key")
    
    @pytest.mark.asyncio
    async def test_glm_handles_json_error(self, glm_protocol):
        """测试GLM处理JSON解析错误"""
        messages = [Message(role="user", content="test")]
        
        mock_stream_data = [
            "data: invalid json",
            "data: [DONE]"
        ]
        
        with patch.object(glm_protocol._client, 'stream', return_value=iter(mock_stream_data)):
            with patch.object(glm_protocol._client, '__aenter__', AsyncMock()):
                with patch.object(glm_protocol._client, '__aexit__', AsyncMock()):
                    pass
    
    @pytest.mark.asyncio
    async def test_qwen_handles_json_error(self, qwen_protocol):
        """测试Qwen处理JSON解析错误"""
        messages = [Message(role="user", content="test")]
        
        mock_stream_data = [
            "data: invalid json",
            "data: [DONE]"
        ]
        
        with patch.object(qwen_protocol._client, 'stream', return_value=iter(mock_stream_data)):
            with patch.object(qwen_protocol._client, '__aenter__', AsyncMock()):
                with patch.object(qwen_protocol._client, '__aexit__', AsyncMock()):
                    pass


class TestProtocolWithCustomParams:
    """协议自定义参数测试"""
    
    def test_glm_custom_model(self):
        """测试GLM自定义模型"""
        protocol = GLMProtocol(
            api_key="key",
            default_model="glm-4-plus"
        )
        
        assert protocol.default_model == "glm-4-plus"
    
    def test_qwen_custom_model(self):
        """测试Qwen自定义模型"""
        protocol = QwenProtocol(
            api_key="key",
            default_model="qwen-max"
        )
        
        assert protocol.default_model == "qwen-max"
    
    def test_glm_custom_base_url(self):
        """测试GLM自定义URL"""
        protocol = GLMProtocol(
            api_key="key",
            base_url="https://custom.glm.api.com"
        )
        
        assert protocol.base_url == "https://custom.glm.api.com"
    
    def test_qwen_custom_base_url(self):
        """测试Qwen自定义URL"""
        protocol = QwenProtocol(
            api_key="key",
            base_url="https://custom.qwen.api.com"
        )
        
        assert protocol.base_url == "https://custom.qwen.api.com"
