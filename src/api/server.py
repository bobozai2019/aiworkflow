"""
FastAPI服务器

提供移动端API服务。
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.api.routes import router as api_router, set_notification_manager
from src.communication.notification import NotificationManager
from src.communication.websocket import WebSocketHandler


_notification_manager: Optional[NotificationManager] = None
_ws_handler: Optional[WebSocketHandler] = None
_start_time: datetime = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _notification_manager, _ws_handler, _start_time
    
    _start_time = datetime.now()
    _notification_manager = NotificationManager()
    _ws_handler = WebSocketHandler(_notification_manager)
    
    set_notification_manager(_notification_manager)
    
    logger.info("API服务器启动")
    
    yield
    
    logger.info("API服务器关闭")


app = FastAPI(
    title="Multi-Agent System API",
    description="多Agent协作系统API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    """根路径"""
    return {
        "name": "Multi-Agent System API",
        "version": "1.0.0",
        "status": "running",
        "uptime": (datetime.now() - _start_time).total_seconds() if _start_time else 0
    }


@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket):
    """WebSocket通知端点"""
    if _ws_handler:
        await _ws_handler.handle(websocket)


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """运行服务器"""
    import uvicorn
    
    logger.info(f"启动API服务器: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
