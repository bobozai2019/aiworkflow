"""
HTTP客户端模块

基于httpx的异步HTTP客户端封装，支持超时、重试和流式响应。
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, Optional

import httpx
from loguru import logger


class HttpClient:
    """
    异步HTTP客户端
    
    提供异步HTTP请求功能，支持连接池、超时、重试和流式响应。
    
    Attributes:
        timeout: 请求超时时间（秒）
        max_retries: 最大重试次数
    """
    
    def __init__(
        self,
        timeout: int = 60,
        max_retries: int = 3,
        headers: Optional[Dict[str, str]] = None
    ) -> None:
        self.timeout = timeout
        self.max_retries = max_retries
        self._headers = headers or {}
        self._client: Optional[httpx.AsyncClient] = None
    
    async def __aenter__(self) -> HttpClient:
        await self._ensure_client()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        pass
    
    async def _ensure_client(self) -> None:
        """确保客户端已初始化"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(
                    connect=30.0,
                    read=300.0,
                    write=30.0,
                    pool=30.0
                ),
                headers=self._headers
            )
    
    async def close(self) -> None:
        """关闭客户端连接"""
        if self._client:
            await self._client.aclose()
            self._client = None
    
    async def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """
        发送GET请求
        
        Args:
            url: 请求URL
            params: 查询参数
            headers: 请求头
            
        Returns:
            响应对象
        """
        return await self._request("GET", url, params=params, headers=headers)
    
    async def post(
        self,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """
        发送POST请求
        
        Args:
            url: 请求URL
            json: JSON请求体
            headers: 请求头
            
        Returns:
            响应对象
        """
        return await self._request("POST", url, json=json, headers=headers)
    
    async def _request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        发送请求（带重试）
        
        Args:
            method: 请求方法
            url: 请求URL
            **kwargs: 其他参数
            
        Returns:
            响应对象
        """
        await self._ensure_client()
        
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = await self._client.request(method, url, **kwargs)
                response.raise_for_status()
                return response
            except httpx.TimeoutException as e:
                last_error = e
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries}): {url}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(1 * (attempt + 1))
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    last_error = e
                    logger.warning(f"Server error (attempt {attempt + 1}/{self.max_retries}): {e.response.status_code}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(1 * (attempt + 1))
                else:
                    raise
        
        raise last_error or httpx.RequestError("Max retries exceeded")
    
    async def stream(
        self,
        method: str,
        url: str,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> AsyncIterator[str]:
        """
        流式请求
        
        Args:
            method: 请求方法
            url: 请求URL
            json: JSON请求体
            headers: 请求头
            
        Yields:
            响应数据块
        """
        await self._ensure_client()
        
        request_headers = {**self._headers, **(headers or {})}
        
        request = self._client.build_request(
            method,
            url,
            json=json,
            headers=request_headers,
        )
        
        logger.debug(f"[HttpClient] Sending stream request to {url}")
        response = await self._client.send(request, stream=True)
        
        try:
            response.raise_for_status()
            logger.debug(f"[HttpClient] Stream response started, status={response.status_code}")
            line_count = 0
            async for line in response.aiter_lines():
                if line.strip():
                    line_count += 1
                    yield line
            logger.debug(f"[HttpClient] Stream finished, total lines: {line_count}")
        except Exception as e:
            logger.error(f"[HttpClient] Stream error: {e}")
            raise
        finally:
            logger.debug(f"[HttpClient] Closing response")
            try:
                await response.aclose()
            except Exception as e:
                logger.debug(f"[HttpClient] 关闭响应时异常: {e}")
