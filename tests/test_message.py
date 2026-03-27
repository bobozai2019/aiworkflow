"""
消息数据模块测试
"""

import pytest
from datetime import datetime

from src.core.message import Message, ChatChunk


class TestChatChunk:
    """聊天响应块测试"""
    
    def test_init_default(self):
        """测试默认初始化"""
        chunk = ChatChunk()
        assert chunk.content == ""
        assert chunk.reasoning_content == ""
        assert chunk.is_thinking is False
    
    def test_init_with_content(self):
        """测试带内容初始化"""
        chunk = ChatChunk(content="Hello", reasoning_content="Thinking...")
        assert chunk.content == "Hello"
        assert chunk.reasoning_content == "Thinking..."
    
    def test_init_thinking(self):
        """测试思考状态"""
        chunk = ChatChunk(content="", is_thinking=True)
        assert chunk.is_thinking is True


class TestMessage:
    """消息数据类测试"""
    
    def test_init_basic(self):
        """测试基本初始化"""
        msg = Message(role="user", content="Hello")
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.reasoning_content == ""
        assert msg.metadata == {}
        assert msg.timestamp is not None
    
    def test_init_with_all_fields(self):
        """测试完整初始化"""
        ts = datetime(2024, 1, 1, 12, 0, 0)
        msg = Message(
            role="assistant",
            content="Response",
            reasoning_content="Thinking...",
            metadata={"key": "value"},
            timestamp=ts
        )
        
        assert msg.role == "assistant"
        assert msg.content == "Response"
        assert msg.reasoning_content == "Thinking..."
        assert msg.metadata == {"key": "value"}
        assert msg.timestamp == ts
    
    def test_to_dict(self):
        """测试转换为字典"""
        ts = datetime(2024, 1, 1, 12, 0, 0)
        msg = Message(
            role="user",
            content="Hello",
            reasoning_content="Thinking",
            metadata={"key": "value"},
            timestamp=ts
        )
        
        data = msg.to_dict()
        
        assert data["role"] == "user"
        assert data["content"] == "Hello"
        assert data["reasoning_content"] == "Thinking"
        assert data["metadata"] == {"key": "value"}
        assert data["timestamp"] == "2024-01-01T12:00:00"
    
    def test_from_dict(self):
        """测试从字典创建"""
        data = {
            "role": "assistant",
            "content": "Response",
            "reasoning_content": "Reasoning",
            "metadata": {"model": "gpt-4"},
            "timestamp": "2024-01-01T12:00:00"
        }
        
        msg = Message.from_dict(data)
        
        assert msg.role == "assistant"
        assert msg.content == "Response"
        assert msg.reasoning_content == "Reasoning"
        assert msg.metadata == {"model": "gpt-4"}
        assert msg.timestamp == datetime(2024, 1, 1, 12, 0, 0)
    
    def test_from_dict_minimal(self):
        """测试从最小字典创建"""
        data = {"role": "user", "content": "Hello"}
        
        msg = Message.from_dict(data)
        
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.reasoning_content == ""
        assert msg.metadata == {}
    
    def test_from_dict_without_timestamp(self):
        """测试从无时间戳字典创建"""
        data = {"role": "user", "content": "Hello"}
        
        msg = Message.from_dict(data)
        
        assert msg.timestamp is None
    
    def test_str(self):
        """测试字符串表示"""
        msg = Message(role="user", content="This is a very long message that should be truncated in the string representation")
        
        s = str(msg)
        assert "[user]" in s
        assert "..." in s
    
    def test_str_short(self):
        """测试短消息字符串表示"""
        msg = Message(role="assistant", content="Hi")
        
        s = str(msg)
        assert "[assistant]" in s


class TestMessageRoles:
    """消息角色测试"""
    
    def test_system_role(self):
        """测试系统角色"""
        msg = Message(role="system", content="You are a helpful assistant.")
        assert msg.role == "system"
    
    def test_user_role(self):
        """测试用户角色"""
        msg = Message(role="user", content="Hello!")
        assert msg.role == "user"
    
    def test_assistant_role(self):
        """测试助手角色"""
        msg = Message(role="assistant", content="Hi there!")
        assert msg.role == "assistant"


class TestMessageSerialization:
    """消息序列化测试"""
    
    def test_round_trip(self):
        """测试序列化往返"""
        original = Message(
            role="user",
            content="Test message",
            reasoning_content="Some reasoning",
            metadata={"key": "value", "number": 42}
        )
        
        data = original.to_dict()
        restored = Message.from_dict(data)
        
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.reasoning_content == original.reasoning_content
        assert restored.metadata == original.metadata
    
    def test_metadata_preserved(self):
        """测试元数据保留"""
        metadata = {
            "model": "gpt-4",
            "tokens": {"prompt": 10, "completion": 20},
            "finish_reason": "stop"
        }
        
        msg = Message(role="assistant", content="Response", metadata=metadata)
        
        data = msg.to_dict()
        restored = Message.from_dict(data)
        
        assert restored.metadata == metadata
        assert restored.metadata["model"] == "gpt-4"
        assert restored.metadata["tokens"]["prompt"] == 10
