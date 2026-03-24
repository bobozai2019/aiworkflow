"""
MiniMax协议模块

实现MiniMax API的调用协议。
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Optional

from loguru import logger

from src.communication.http_client import HttpClient
from src.core.message import ChatChunk, Message
from src.protocols.base import BaseProtocol


class MiniMaxProtocol(BaseProtocol):
    """
    MiniMax协议
    
    实现MiniMax API的调用，支持流式输出。
    
    API文档: https://www.minimaxi.com/document/
    """
    
    def __init__(
        self,
        api_key: str,
        group_id: str,
        base_url: str = "https://api.minimax.chat/v1",
        default_model: str = "abab6.5-chat"
    ) -> None:
        super().__init__(base_url, api_key, default_model)
        self.group_id = group_id
        self._client = HttpClient(headers=self.get_headers())
    
    def get_headers(self) -> Dict[str, str]:
        """
        获取请求头
        
        Returns:
            请求头字典
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Group-Id": self.group_id
        }
    
    async def chat(
        self,
        messages: List[Message],
        model: str = None,
        stream: bool = True,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[ChatChunk]:
        """
        对话接口
        
        Args:
            messages: 消息列表
            model: 模型名称
            stream: 是否流式输出
            temperature: 温度参数
            **kwargs: 其他参数
            
        Yields:
            ChatChunk响应块
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model or self.default_model,
            "messages": self.format_messages(messages),
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }
        
        logger.debug(f"[MiniMax] Request: model={payload['model']}, messages={len(messages)}")
        
        if stream:
            async for chunk in self._stream_chat(url, payload):
                yield chunk
        else:
            response = await self._client.post(url, json=payload)
            data = response.json()
            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content", "")
            logger.debug(f"[MiniMax] Response: {content[:100]}...")
            yield ChatChunk(content=content)
    
    async def _stream_chat(
        self,
        url: str,
        payload: Dict[str, Any]
    ) -> AsyncIterator[ChatChunk]:
        """
        流式对话
        
        Args:
            url: API URL
            payload: 请求体
            
        Yields:
            ChatChunk响应块
        """
        async with self._client as client:
            async for line in client.stream("POST", url, json=payload):
                if not line.startswith("data: "):
                    continue
                
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    
                    if content:
                        yield ChatChunk(content=content)
                except json.JSONDecodeError:
                    continue
    
    def format_messages(self, messages: List[Message]) -> List[Dict[str, str]]:
        """
        格式化消息为OpenAI兼容格式
        
        Args:
            messages: 消息列表
            
        Returns:
            格式化后的消息列表
        """
        formatted = []
        for msg in messages:
            formatted.append({"role": msg.role, "content": msg.content})
        return formatted
