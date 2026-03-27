"""
WebSocket通信模块

实现WebSocket连接管理。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, List, Optional

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

if TYPE_CHECKING:
    from src.communication.notification import NotificationManager


class WebSocketHandler:
    """
    WebSocket处理器
    
    管理WebSocket连接和消息分发。
    """
    
    def __init__(self, notification_manager: "NotificationManager" = None):
        self._notification_manager = notification_manager
        self._connections: List[WebSocket] = []
    
    async def handle(self, websocket: WebSocket):
        """
        处理WebSocket连接
        
        Args:
            websocket: WebSocket连接
        """
        await websocket.accept()
        self._connections.append(websocket)
        
        if self._notification_manager:
            self._notification_manager.add_connection(websocket)
        
        logger.info(f"WebSocket连接建立，当前连接数: {len(self._connections)}")
        
        try:
            while True:
                data = await websocket.receive_text()
                await self._on_message(websocket, data)
        except WebSocketDisconnect:
            self._disconnect(websocket)
        except Exception as e:
            logger.error(f"WebSocket错误: {e}")
            self._disconnect(websocket)
    
    async def _on_message(self, websocket: WebSocket, data: str):
        """
        处理接收的消息
        
        Args:
            websocket: WebSocket连接
            data: 消息数据
        """
        try:
            message = json.loads(data)
            msg_type = message.get("type", "unknown")
            
            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
            elif msg_type == "subscribe":
                task_id = message.get("task_id")
                if task_id:
                    await websocket.send_json({
                        "type": "subscribed",
                        "task_id": task_id
                    })
            else:
                logger.debug(f"收到WebSocket消息: {msg_type}")
                
        except json.JSONDecodeError:
            logger.warning(f"无效的JSON消息: {data[:100]}")
    
    def _disconnect(self, websocket: WebSocket):
        """
        处理断开连接
        
        Args:
            websocket: WebSocket连接
        """
        if websocket in self._connections:
            self._connections.remove(websocket)
        
        if self._notification_manager:
            self._notification_manager.remove_connection(websocket)
        
        logger.info(f"WebSocket连接断开，当前连接数: {len(self._connections)}")
    
    async def broadcast(self, message: dict):
        """
        广播消息到所有连接
        
        Args:
            message: 消息内容
        """
        for connection in self._connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return len(self._connections)
    
    @property
    def connections(self) -> List[WebSocket]:
        """当前连接列表"""
        return self._connections.copy()
