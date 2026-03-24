"""
消息数据模块

定义Agent间通信的消息格式。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass
class ChatChunk:
    """
    聊天响应块
    
    用于流式输出时的单个响应块。
    
    Attributes:
        content: 内容块
        reasoning_content: 思考过程块
        is_thinking: 是否正在思考
    """
    
    content: str = ""
    reasoning_content: str = ""
    is_thinking: bool = False


@dataclass
class Message:
    """
    消息数据类
    
    用于Agent间通信和与LLM交互。
    
    Attributes:
        role: 消息角色 (system/user/assistant)
        content: 消息内容
        reasoning_content: 思考过程内容（DeepSeek推理模型）
        metadata: 扩展元数据
        timestamp: 时间戳
    """
    
    role: str
    content: str
    reasoning_content: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            字典表示
        """
        return {
            "role": self.role,
            "content": self.content,
            "reasoning_content": self.reasoning_content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        """
        从字典创建消息
        
        Args:
            data: 字典数据
            
        Returns:
            Message实例
        """
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            role=data["role"],
            content=data["content"],
            reasoning_content=data.get("reasoning_content", ""),
            metadata=data.get("metadata", {}),
            timestamp=timestamp
        )
    
    def __str__(self) -> str:
        return f"[{self.role}] {self.content[:100]}..."
