"""
协议基类模块

定义大模型API协议的统一接口。
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List

if TYPE_CHECKING:
    from src.core.message import ChatChunk, Message


class BaseProtocol(ABC):
    """
    协议基类
    
    所有LLM协议必须实现此接口。
    
    Attributes:
        base_url: API基础URL
        api_key: API密钥
        default_model: 默认模型
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        default_model: str
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.default_model = default_model
    
    @abstractmethod
    async def chat(
        self,
        messages: List["Message"],
        model: str = None,
        stream: bool = True,
        **kwargs
    ) -> AsyncIterator["ChatChunk"]:
        """
        对话接口
        
        Args:
            messages: 消息列表
            model: 模型名称
            stream: 是否流式输出
            **kwargs: 其他参数
            
        Yields:
            ChatChunk响应块
        """
        pass
    
    @abstractmethod
    def format_messages(self, messages: List["Message"]) -> List[Dict[str, str]]:
        """
        格式化消息为协议特定格式
        
        Args:
            messages: 消息列表
            
        Returns:
            格式化后的消息列表
        """
        pass
    
    def get_headers(self) -> Dict[str, str]:
        """
        获取请求头
        
        Returns:
            请求头字典
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    @property
    def name(self) -> str:
        """协议名称"""
        return self.__class__.__name__.replace("Protocol", "").lower()
