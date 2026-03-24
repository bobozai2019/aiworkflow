# communication - 通信层

本目录包含网络通信相关的封装。

## 文件说明

| 文件 | 职责 |
|------|------|
| `http_client.py` | 异步HTTP客户端封装，基于httpcore/httpx |
| `websocket.py` | WebSocket通信封装，用于实时通信 |
| `notification.py` | 通知服务，用于进度推送和事件通知 |

## HTTP客户端设计

```python
class HttpClient:
    """异步HTTP客户端"""
    
    async def get(url, params=None) -> Response:
        """GET请求"""
        pass
    
    async def post(url, json=None) -> Response:
        """POST请求"""
        pass
    
    async def stream(url, method='POST', json=None) -> AsyncIterator[bytes]:
        """流式请求"""
        pass
```

## 功能特性

- 异步请求支持
- 连接池管理
- 超时配置
- 自动重试机制
- 流式响应处理
- 请求/响应日志

## 配置项

```yaml
http:
  timeout: 60        # 请求超时（秒）
  max_retries: 3     # 最大重试次数
  pool_size: 5       # 连接池大小
```

## 开发顺序

1. `http_client.py` - HTTP客户端（优先）
2. `notification.py` - 通知服务（后续）
3. `websocket.py` - WebSocket（后续）
