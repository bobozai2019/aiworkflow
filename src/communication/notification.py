"""
通知服务模块

实现实时通知推送。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import WebSocket
from loguru import logger


class NotificationManager:
    """
    通知管理器
    
    管理WebSocket连接和通知推送。
    """
    
    def __init__(self):
        self._connections: List[WebSocket] = []
        self._subscribers: Dict[str, List[WebSocket]] = {}
    
    def add_connection(self, websocket: WebSocket):
        """
        添加连接
        
        Args:
            websocket: WebSocket连接
        """
        if websocket not in self._connections:
            self._connections.append(websocket)
            logger.debug(f"添加通知连接，当前连接数: {len(self._connections)}")
    
    def remove_connection(self, websocket: WebSocket):
        """
        移除连接
        
        Args:
            websocket: WebSocket连接
        """
        if websocket in self._connections:
            self._connections.remove(websocket)
        
        for task_id in list(self._subscribers.keys()):
            if websocket in self._subscribers[task_id]:
                self._subscribers[task_id].remove(websocket)
        
        logger.debug(f"移除通知连接，当前连接数: {len(self._connections)}")
    
    def subscribe(self, task_id: str, websocket: WebSocket):
        """
        订阅任务通知
        
        Args:
            task_id: 任务ID
            websocket: WebSocket连接
        """
        if task_id not in self._subscribers:
            self._subscribers[task_id] = []
        
        if websocket not in self._subscribers[task_id]:
            self._subscribers[task_id].append(websocket)
            logger.debug(f"订阅任务通知: {task_id}")
    
    def unsubscribe(self, task_id: str, websocket: WebSocket):
        """
        取消订阅任务通知
        
        Args:
            task_id: 任务ID
            websocket: WebSocket连接
        """
        if task_id in self._subscribers:
            if websocket in self._subscribers[task_id]:
                self._subscribers[task_id].remove(websocket)
    
    async def notify(self, task_id: str, notification_type: str, data: Dict[str, Any]):
        """
        发送任务通知
        
        Args:
            task_id: 任务ID
            notification_type: 通知类型
            data: 通知数据
        """
        message = {
            "type": notification_type,
            "task_id": task_id,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
        if task_id in self._subscribers:
            for websocket in self._subscribers[task_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"发送通知失败: {e}")
    
    async def broadcast(self, message: Dict[str, Any]):
        """
        广播消息到所有连接
        
        Args:
            message: 消息内容
        """
        message["timestamp"] = datetime.now().isoformat()
        
        for websocket in self._connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"广播消息失败: {e}")
    
    async def send_progress(self, task_id: str, agent: str, status: str, progress: float):
        """
        发送进度通知
        
        Args:
            task_id: 任务ID
            agent: Agent名称
            status: 状态
            progress: 进度
        """
        await self.notify(task_id, "progress", {
            "agent": agent,
            "status": status,
            "progress": progress
        })
    
    async def send_complete(self, task_id: str, success: bool, result: str = ""):
        """
        发送完成通知
        
        Args:
            task_id: 任务ID
            success: 是否成功
            result: 结果内容
        """
        await self.notify(task_id, "complete", {
            "success": success,
            "result": result
        })
    
    async def send_error(self, task_id: str, error: str):
        """
        发送错误通知
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        await self.notify(task_id, "error", {
            "error": error
        })
    
    @property
    def connection_count(self) -> int:
        """当前连接数"""
        return len(self._connections)
