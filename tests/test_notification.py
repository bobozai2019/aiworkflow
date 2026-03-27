"""
通知服务模块测试
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.communication.notification import NotificationManager


class TestNotificationManager:
    """通知管理器测试"""
    
    @pytest.fixture
    def manager(self):
        """创建通知管理器实例"""
        return NotificationManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """创建模拟WebSocket"""
        ws = MagicMock()
        ws.send_json = AsyncMock()
        return ws
    
    def test_init(self, manager):
        """测试初始化"""
        assert manager._connections == []
        assert manager._subscribers == {}
    
    def test_add_connection(self, manager, mock_websocket):
        """测试添加连接"""
        manager.add_connection(mock_websocket)
        assert mock_websocket in manager._connections
        assert manager.connection_count == 1
    
    def test_add_connection_duplicate(self, manager, mock_websocket):
        """测试重复添加连接"""
        manager.add_connection(mock_websocket)
        manager.add_connection(mock_websocket)
        assert manager.connection_count == 1
    
    def test_remove_connection(self, manager, mock_websocket):
        """测试移除连接"""
        manager.add_connection(mock_websocket)
        manager.remove_connection(mock_websocket)
        assert mock_websocket not in manager._connections
        assert manager.connection_count == 0
    
    def test_connection_count(self, manager, mock_websocket):
        """测试连接计数"""
        assert manager.connection_count == 0
        
        manager.add_connection(mock_websocket)
        assert manager.connection_count == 1
        
        ws2 = MagicMock()
        manager.add_connection(ws2)
        assert manager.connection_count == 2


class TestNotificationManagerSubscribe:
    """通知管理器订阅测试"""
    
    @pytest.fixture
    def manager(self):
        return NotificationManager()
    
    @pytest.fixture
    def mock_websocket(self):
        ws = MagicMock()
        ws.send_json = AsyncMock()
        return ws
    
    def test_subscribe(self, manager, mock_websocket):
        """测试订阅任务"""
        manager.subscribe("task_123", mock_websocket)
        assert "task_123" in manager._subscribers
        assert mock_websocket in manager._subscribers["task_123"]
    
    def test_subscribe_multiple(self, manager, mock_websocket):
        """测试多个WebSocket订阅同一任务"""
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()
        
        manager.subscribe("task_123", mock_websocket)
        manager.subscribe("task_123", ws2)
        
        assert len(manager._subscribers["task_123"]) == 2
    
    def test_subscribe_duplicate(self, manager, mock_websocket):
        """测试重复订阅"""
        manager.subscribe("task_123", mock_websocket)
        manager.subscribe("task_123", mock_websocket)
        
        assert len(manager._subscribers["task_123"]) == 1
    
    def test_unsubscribe(self, manager, mock_websocket):
        """测试取消订阅"""
        manager.subscribe("task_123", mock_websocket)
        manager.unsubscribe("task_123", mock_websocket)
        
        assert mock_websocket not in manager._subscribers.get("task_123", [])
    
    def test_remove_connection_clears_subscriptions(self, manager, mock_websocket):
        """测试移除连接时清除订阅"""
        manager.add_connection(mock_websocket)
        manager.subscribe("task_123", mock_websocket)
        manager.subscribe("task_456", mock_websocket)
        
        manager.remove_connection(mock_websocket)
        
        assert mock_websocket not in manager._subscribers.get("task_123", [])
        assert mock_websocket not in manager._subscribers.get("task_456", [])


class TestNotificationManagerNotify:
    """通知管理器通知测试"""
    
    @pytest.fixture
    def manager(self):
        return NotificationManager()
    
    @pytest.fixture
    def mock_websocket(self):
        ws = MagicMock()
        ws.send_json = AsyncMock()
        return ws
    
    @pytest.mark.asyncio
    async def test_notify(self, manager, mock_websocket):
        """测试发送通知"""
        manager.subscribe("task_123", mock_websocket)
        
        await manager.notify("task_123", "test_type", {"key": "value"})
        
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "test_type"
        assert call_args["task_id"] == "task_123"
        assert call_args["data"] == {"key": "value"}
        assert "timestamp" in call_args
    
    @pytest.mark.asyncio
    async def test_notify_no_subscribers(self, manager):
        """测试无订阅者时发送通知"""
        await manager.notify("task_123", "test_type", {"key": "value"})
    
    @pytest.mark.asyncio
    async def test_broadcast(self, manager, mock_websocket):
        """测试广播消息"""
        ws2 = MagicMock()
        ws2.send_json = AsyncMock()
        
        manager.add_connection(mock_websocket)
        manager.add_connection(ws2)
        
        await manager.broadcast({"type": "broadcast", "message": "hello"})
        
        assert mock_websocket.send_json.call_count == 1
        assert ws2.send_json.call_count == 1
    
    @pytest.mark.asyncio
    async def test_send_progress(self, manager, mock_websocket):
        """测试发送进度通知"""
        manager.subscribe("task_123", mock_websocket)
        
        await manager.send_progress("task_123", "Agent1", "running", 50.0)
        
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "progress"
        assert call_args["data"]["agent"] == "Agent1"
        assert call_args["data"]["progress"] == 50.0
    
    @pytest.mark.asyncio
    async def test_send_complete(self, manager, mock_websocket):
        """测试发送完成通知"""
        manager.subscribe("task_123", mock_websocket)
        
        await manager.send_complete("task_123", True, "任务完成")
        
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "complete"
        assert call_args["data"]["success"] is True
        assert call_args["data"]["result"] == "任务完成"
    
    @pytest.mark.asyncio
    async def test_send_error(self, manager, mock_websocket):
        """测试发送错误通知"""
        manager.subscribe("task_123", mock_websocket)
        
        await manager.send_error("task_123", "发生错误")
        
        mock_websocket.send_json.assert_called_once()
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "error"
        assert call_args["data"]["error"] == "发生错误"
    
    @pytest.mark.asyncio
    async def test_notify_handles_exception(self, manager, mock_websocket):
        """测试通知时处理异常"""
        mock_websocket.send_json.side_effect = Exception("连接已断开")
        manager.subscribe("task_123", mock_websocket)
        
        await manager.notify("task_123", "test_type", {"key": "value"})
    
    @pytest.mark.asyncio
    async def test_broadcast_handles_exception(self, manager, mock_websocket):
        """测试广播时处理异常"""
        mock_websocket.send_json.side_effect = Exception("连接已断开")
        manager.add_connection(mock_websocket)
        
        await manager.broadcast({"type": "test"})
