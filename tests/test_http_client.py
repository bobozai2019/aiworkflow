"""
HTTP客户端模块测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.communication.http_client import HttpClient


class TestHttpClient:
    """HTTP客户端测试"""
    
    def test_init(self):
        """测试初始化"""
        client = HttpClient(timeout=30, max_retries=2)
        assert client.timeout == 30
        assert client.max_retries == 2
        assert client._headers == {}
    
    def test_init_with_headers(self):
        """测试带请求头初始化"""
        headers = {"Authorization": "Bearer test"}
        client = HttpClient(headers=headers)
        assert client._headers == headers
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """测试上下文管理器"""
        client = HttpClient()
        async with client as c:
            assert c is client
            assert client._client is not None
    
    @pytest.mark.asyncio
    async def test_close(self):
        """测试关闭连接"""
        client = HttpClient()
        await client._ensure_client()
        assert client._client is not None
        
        await client.close()
        assert client._client is None
    
    @pytest.mark.asyncio
    async def test_ensure_client(self):
        """测试确保客户端初始化"""
        client = HttpClient()
        assert client._client is None
        
        await client._ensure_client()
        assert client._client is not None
        
        await client.close()


class TestHttpClientRequests:
    """HTTP客户端请求测试"""
    
    @pytest.fixture
    def mock_client(self):
        """创建模拟客户端"""
        return HttpClient(timeout=10, max_retries=1)
    
    @pytest.mark.asyncio
    async def test_get_request(self, mock_client):
        """测试GET请求"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        
        with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            response = await mock_client.get("https://api.example.com/data")
            
            assert response.status_code == 200
            mock_request.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_post_request(self, mock_client):
        """测试POST请求"""
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 1}
        
        with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            response = await mock_client.post(
                "https://api.example.com/data",
                json={"name": "test"}
            )
            
            assert response.status_code == 201
    
    @pytest.mark.asyncio
    async def test_request_with_params(self, mock_client):
        """测试带参数的请求"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            await mock_client.get(
                "https://api.example.com/data",
                params={"page": 1, "limit": 10}
            )
            
            call_args = mock_request.call_args
            assert "params" in call_args.kwargs


class TestHttpClientRetry:
    """HTTP客户端重试测试"""
    
    @pytest.fixture
    def retry_client(self):
        """创建带重试的客户端"""
        return HttpClient(timeout=5, max_retries=2)
    
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self, retry_client):
        """测试超时重试"""
        with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.TimeoutException("Timeout")
            
            with pytest.raises(httpx.TimeoutException):
                await retry_client.get("https://api.example.com/data")
            
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_on_server_error(self, retry_client):
        """测试服务器错误重试"""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=mock_response
        )
        
        with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                await retry_client.get("https://api.example.com/data")
            
            assert mock_request.call_count == 2
    
    @pytest.mark.asyncio
    async def test_no_retry_on_client_error(self, retry_client):
        """测试客户端错误不重试"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Bad Request", request=MagicMock(), response=mock_response
        )
        
        with patch.object(httpx.AsyncClient, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.return_value = mock_response
            
            with pytest.raises(httpx.HTTPStatusError):
                await retry_client.get("https://api.example.com/data")
            
            assert mock_request.call_count == 1
