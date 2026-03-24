"""
API模块测试

测试FastAPI服务端点。
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio


class TestAPIServer:
    """API服务器测试"""
    
    def test_server_import(self):
        """测试服务器模块导入"""
        from src.api.server import create_app
        assert create_app is not None
    
    def test_create_app(self):
        """测试创建应用"""
        from src.api.server import create_app
        
        app = create_app()
        assert app is not None
        assert hasattr(app, 'router')


class TestAPISchemas:
    """API数据模型测试"""
    
    def test_task_create_request(self):
        """测试任务创建请求模型"""
        from src.api.schemas import TaskCreateRequest
        
        request = TaskCreateRequest(
            task="实现一个登录功能",
            agents=["analyst", "coder"]
        )
        
        assert request.task == "实现一个登录功能"
        assert request.agents == ["analyst", "coder"]
    
    def test_task_create_response(self):
        """测试任务创建响应模型"""
        from src.api.schemas import TaskCreateResponse, TaskStatus
        
        response = TaskCreateResponse(
            task_id="abc123",
            status=TaskStatus.PENDING
        )
        
        assert response.task_id == "abc123"
        assert response.status == TaskStatus.PENDING
    
    def test_task_status_response(self):
        """测试任务状态响应模型"""
        from src.api.schemas import TaskStatusResponse, TaskStatus
        
        response = TaskStatusResponse(
            task_id="abc123",
            status=TaskStatus.RUNNING,
            progress=50.0,
            current_agent="analyst",
            message="正在分析需求..."
        )
        
        assert response.task_id == "abc123"
        assert response.status == TaskStatus.RUNNING
        assert response.progress == 50.0
    
    def test_task_status_enum(self):
        """测试任务状态枚举"""
        from src.api.schemas import TaskStatus
        
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"


class TestAPIRoutes:
    """API路由测试"""
    
    @pytest.fixture
    def app(self):
        """创建测试应用"""
        from src.api.server import create_app
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        return TestClient(app)
    
    def test_health_check(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
    
    def test_create_task(self, client):
        """测试创建任务"""
        response = client.post(
            "/api/task",
            json={
                "task": "实现一个登录功能",
                "agents": ["analyst", "coder"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "pending"
    
    def test_get_task_status_not_found(self, client):
        """测试获取不存在的任务状态"""
        response = client.get("/api/task/nonexistent")
        assert response.status_code == 404
    
    def test_list_protocols(self, client):
        """测试列出协议"""
        response = client.get("/api/protocols")
        assert response.status_code == 200
        data = response.json()
        assert "protocols" in data
    
    def test_list_agents(self, client):
        """测试列出Agent"""
        response = client.get("/api/agents")
        assert response.status_code == 200
        data = response.json()
        assert "agents" in data


class TestWebSocket:
    """WebSocket测试"""
    
    @pytest.fixture
    def app(self):
        """创建测试应用"""
        from src.api.server import create_app
        return create_app()
    
    def test_websocket_import(self):
        """测试WebSocket模块导入"""
        from src.communication.websocket import WebSocketHandler
        assert WebSocketHandler is not None
    
    def test_websocket_handler_init(self):
        """测试WebSocket处理器初始化"""
        from src.communication.websocket import WebSocketHandler
        
        handler = WebSocketHandler()
        assert handler is not None
        assert hasattr(handler, 'connections')


class TestNotification:
    """通知服务测试"""
    
    def test_notification_import(self):
        """测试通知模块导入"""
        from src.communication.notification import NotificationManager
        assert NotificationManager is not None
    
    def test_notification_manager_init(self):
        """测试通知管理器初始化"""
        from src.communication.notification import NotificationManager
        
        manager = NotificationManager()
        assert manager is not None
    
    @pytest.mark.asyncio
    async def test_notification_subscribe(self):
        """测试订阅通知"""
        from src.communication.notification import NotificationManager
        
        manager = NotificationManager()
        
        callback = AsyncMock()
        manager.subscribe("test_task", callback)
        
        assert "test_task" in manager._subscribers
        assert callback in manager._subscribers["test_task"]
    
    @pytest.mark.asyncio
    async def test_notification_unsubscribe(self):
        """测试取消订阅"""
        from src.communication.notification import NotificationManager
        
        manager = NotificationManager()
        
        callback = AsyncMock()
        manager.subscribe("test_task", callback)
        manager.unsubscribe("test_task", callback)
        
        assert callback not in manager._subscribers.get("test_task", [])


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def app(self):
        """创建测试应用"""
        from src.api.server import create_app
        return create_app()
    
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        from fastapi.testclient import TestClient
        return TestClient(app)
    
    def test_task_workflow(self, client):
        """测试任务工作流"""
        create_response = client.post(
            "/api/task",
            json={
                "task": "测试任务",
                "agents": ["analyst"]
            }
        )
        
        assert create_response.status_code == 200
        task_id = create_response.json()["task_id"]
        
        status_response = client.get(f"/api/task/{task_id}")
        
        assert status_response.status_code == 200
        data = status_response.json()
        assert data["task_id"] == task_id
