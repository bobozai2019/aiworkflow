"""
DeepSeek协议模块

实现DeepSeek API的调用协议。
"""

from __future__ import annotations

import json
import time
from typing import Any, AsyncIterator, Dict, List

from loguru import logger

from src.communication.http_client import HttpClient
from src.core.message import ChatChunk, Message
from src.protocols.base import BaseProtocol
from src.utils.protocol_logger import protocol_logger


class DeepSeekProtocol(BaseProtocol):
    """
    DeepSeek协议
    
    实现DeepSeek API的调用，支持流式输出和推理模型。
    
    API文档: https://platform.deepseek.com/api-docs/
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        default_model: str = "deepseek-chat"
    ) -> None:
        super().__init__(base_url, api_key, default_model)
        self._client = HttpClient(headers=self.get_headers())
    
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
        
        logger.debug(f"[DeepSeek] Request: model={payload['model']}, messages={len(messages)}")
        
        protocol_logger.log_request(
            provider="deepseek",
            url=url,
            method="POST",
            request_data=payload,
        )
        
        start_time = time.time()
        
        try:
            if stream:
                full_content = ""
                full_reasoning = ""
                async for chunk in self._stream_chat(url, payload):
                    if chunk.content:
                        full_content += chunk.content
                    if chunk.reasoning_content:
                        full_reasoning += chunk.reasoning_content
                    yield chunk
                
                duration_ms = (time.time() - start_time) * 1000
                protocol_logger.log_response(
                    provider="deepseek",
                    url=url,
                    response_data={
                        "content": full_content[:1000] + "..." if len(full_content) > 1000 else full_content,
                        "reasoning_content": full_reasoning[:500] + "..." if len(full_reasoning) > 500 else full_reasoning,
                        "stream": True,
                    },
                    status="success",
                    duration_ms=duration_ms,
                )
            else:
                response = await self._client.post(url, json=payload)
                data = response.json()
                choice = data["choices"][0]
                message = choice.get("message", {})
                content = message.get("content", "")
                reasoning = message.get("reasoning_content", "")
                logger.debug(f"[DeepSeek] Response: {content[:100]}...")
                
                duration_ms = (time.time() - start_time) * 1000
                protocol_logger.log_response(
                    provider="deepseek",
                    url=url,
                    response_data=data,
                    status="success",
                    duration_ms=duration_ms,
                )
                
                yield ChatChunk(content=content, reasoning_content=reasoning)
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            protocol_logger.log_response(
                provider="deepseek",
                url=url,
                response_data=None,
                status="error",
                duration_ms=duration_ms,
                error=str(e),
            )
            raise
    
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
        logger.debug(f"[DeepSeek] _stream_chat started, url={url}")
        chunk_count = 0
        try:
            async for line in self._client.stream("POST", url, json=payload):
                if not line.startswith("data: "):
                    continue
                
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    logger.debug(f"[DeepSeek] Stream done, total chunks: {chunk_count}")
                    break
                
                try:
                    data = json.loads(data_str)
                    delta = data.get("choices", [{}])[0].get("delta", {})
                    
                    content = delta.get("content", "")
                    reasoning = delta.get("reasoning_content", "")
                    
                    if content or reasoning:
                        chunk_count += 1
                        yield ChatChunk(
                            content=content,
                            reasoning_content=reasoning,
                            is_thinking=bool(reasoning)
                        )
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            logger.error(f"[DeepSeek] _stream_chat error: {e}")
            raise
        finally:
            logger.debug(f"[DeepSeek] _stream_chat finished")
    
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
            item = {"role": msg.role, "content": msg.content}
            if msg.reasoning_content:
                item["reasoning_content"] = msg.reasoning_content
            formatted.append(item)
        return formatted
