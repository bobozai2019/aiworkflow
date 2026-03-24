"""
协议交互日志记录器

记录所有API请求和响应，用于调试和问题排查。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional
from threading import Lock


@dataclass
class ProtocolLogEntry:
    """协议日志条目"""
    timestamp: datetime
    provider: str
    direction: str
    url: str
    method: str
    request_data: Optional[Dict[str, Any]] = None
    response_data: Optional[Dict[str, Any]] = None
    status: str = "pending"
    duration_ms: Optional[float] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "provider": self.provider,
            "direction": self.direction,
            "url": self.url,
            "method": self.method,
            "request_data": self.request_data,
            "response_data": self.response_data,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


class ProtocolLogger:
    """
    协议交互日志记录器（单例）
    
    记录所有API请求和响应，支持实时订阅更新。
    """
    
    _instance: Optional[ProtocolLogger] = None
    _lock: Lock = Lock()
    
    def __new__(cls) -> ProtocolLogger:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._logs: List[ProtocolLogEntry] = []
        self._max_logs: int = 1000
        self._subscribers: List[Callable[[ProtocolLogEntry], None]] = []
        self._subscribers_lock = Lock()
    
    def log_request(
        self,
        provider: str,
        url: str,
        method: str,
        request_data: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        记录请求
        
        Returns:
            日志条目ID（时间戳字符串）
        """
        entry = ProtocolLogEntry(
            timestamp=datetime.now(),
            provider=provider,
            direction="request",
            url=url,
            method=method,
            request_data=self._sanitize_data(request_data),
            status="pending",
        )
        
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]
        
        self._notify_subscribers(entry)
        return entry.timestamp.isoformat()
    
    def log_response(
        self,
        provider: str,
        url: str,
        response_data: Optional[Dict[str, Any]] = None,
        status: str = "success",
        duration_ms: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        """记录响应"""
        entry = ProtocolLogEntry(
            timestamp=datetime.now(),
            provider=provider,
            direction="response",
            url=url,
            method="",
            response_data=self._sanitize_data(response_data),
            status=status,
            duration_ms=duration_ms,
            error=error,
        )
        
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]
        
        self._notify_subscribers(entry)
    
    def log_stream_chunk(
        self,
        provider: str,
        url: str,
        chunk_data: Dict[str, Any],
    ) -> None:
        """记录流式响应块"""
        entry = ProtocolLogEntry(
            timestamp=datetime.now(),
            provider=provider,
            direction="stream",
            url=url,
            method="",
            response_data=chunk_data,
            status="streaming",
        )
        
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]
        
        self._notify_subscribers(entry)
    
    def log_tool_call(
        self,
        tool_name: str,
        params: Dict[str, Any],
    ) -> str:
        """记录工具调用"""
        entry = ProtocolLogEntry(
            timestamp=datetime.now(),
            provider="tool",
            direction="tool_call",
            url="",
            method=tool_name,
            request_data=params,
            status="pending",
        )
        
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]
        
        self._notify_subscribers(entry)
        return entry.timestamp.isoformat()
    
    def log_tool_result(
        self,
        tool_name: str,
        result: str,
        success: bool = True,
        error: Optional[str] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """记录工具执行结果"""
        entry = ProtocolLogEntry(
            timestamp=datetime.now(),
            provider="tool",
            direction="tool_result",
            url="",
            method=tool_name,
            response_data={"result": result[:5000] if len(result) > 5000 else result},
            status="success" if success else "error",
            duration_ms=duration_ms,
            error=error,
        )
        
        with self._lock:
            self._logs.append(entry)
            if len(self._logs) > self._max_logs:
                self._logs = self._logs[-self._max_logs:]
        
        self._notify_subscribers(entry)
    
    def get_logs(self, limit: int = 100) -> List[ProtocolLogEntry]:
        """获取日志列表"""
        with self._lock:
            return self._logs[-limit:]
    
    def clear_logs(self) -> None:
        """清空日志"""
        with self._lock:
            self._logs.clear()
    
    def subscribe(self, callback: Callable[[ProtocolLogEntry], None]) -> None:
        """订阅日志更新"""
        with self._subscribers_lock:
            self._subscribers.append(callback)
    
    def unsubscribe(self, callback: Callable[[ProtocolLogEntry], None]) -> None:
        """取消订阅"""
        with self._subscribers_lock:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
    
    def _notify_subscribers(self, entry: ProtocolLogEntry) -> None:
        """通知订阅者"""
        with self._subscribers_lock:
            for callback in self._subscribers:
                try:
                    callback(entry)
                except Exception as e:
                    import sys
                    print(f"[ProtocolLogger] 订阅者回调异常: {e}", file=sys.stderr)
    
    def _sanitize_data(self, data: Any) -> Any:
        """清理敏感数据"""
        if not isinstance(data, dict):
            return data
        
        result = data.copy()
        sensitive_keys = ["api_key", "apikey", "authorization", "token", "password"]
        
        for key in list(result.keys()):
            if key.lower() in sensitive_keys:
                result[key] = "***REDACTED***"
            elif isinstance(result[key], dict):
                result[key] = self._sanitize_data(result[key])
        
        return result


protocol_logger = ProtocolLogger()


__all__ = ["ProtocolLogger", "ProtocolLogEntry", "protocol_logger"]
