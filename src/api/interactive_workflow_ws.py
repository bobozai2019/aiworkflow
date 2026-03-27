"""
基于WebSocket的交互式工作流API

提供Web界面的交互式工作流支持。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger

from src.agents.analyst import AnalystAgent
from src.agents.architect import ArchitectAgent
from src.agents.coder import CoderAgent
from src.agents.debugger import DebuggerAgent
from src.agents.tester import TesterAgent
from src.core.workflow_interactive import InteractiveWorkflow, WorkflowStage
from src.protocols.deepseek import DeepSeekProtocol
from src.utils.config import Config


class InteractiveWorkflowWebSocket:
    """
    基于WebSocket的交互式工作流

    消息格式:
    - 客户端 -> 服务器:
      {"type": "start", "task": "任务描述"}
      {"type": "approve", "modifications": "修改建议（可选）"}
      {"type": "reject", "reason": "拒绝原因（可选）"}
      {"type": "modify", "new_plan": "新计划内容"}

    - 服务器 -> 客户端:
      {"type": "plan_ready", "agent_name": "...", "stage_name": "...", "plan": "..."}
      {"type": "stage_complete", "agent_name": "...", "success": true, "result": {...}}
      {"type": "progress", "current": 1, "total": 5, "percent": 20}
      {"type": "completed", "project_dir": "..."}
      {"type": "error", "message": "..."}
    """

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.workflow: Optional[InteractiveWorkflow] = None
        self.protocol: Optional[DeepSeekProtocol] = None

    async def connect(self):
        """建立WebSocket连接"""
        await self.websocket.accept()
        logger.info("[InteractiveWS] Client connected")

        # 初始化协议
        config = Config.load("config")
        protocol_config = config.get_protocol("deepseek")

        self.protocol = DeepSeekProtocol(
            api_key=protocol_config.get("api_key", ""),
            base_url=protocol_config.get("base_url", "https://api.deepseek.com"),
            default_model=protocol_config.get("default_model", "deepseek-chat")
        )

    async def handle_messages(self):
        """处理客户端消息"""
        try:
            while True:
                # 接收消息
                data = await self.websocket.receive_text()
                message = json.loads(data)

                msg_type = message.get("type")
                logger.info(f"[InteractiveWS] Received: {msg_type}")

                if msg_type == "start":
                    await self.handle_start(message)
                elif msg_type == "approve":
                    await self.handle_approve(message)
                elif msg_type == "reject":
                    await self.handle_reject(message)
                elif msg_type == "modify":
                    await self.handle_modify(message)
                else:
                    await self.send_error(f"Unknown message type: {msg_type}")

        except WebSocketDisconnect:
            logger.info("[InteractiveWS] Client disconnected")
        except Exception as e:
            logger.error(f"[InteractiveWS] Error: {e}")
            await self.send_error(str(e))

    async def handle_start(self, message: dict):
        """处理启动请求"""
        task = message.get("task")
        if not task:
            await self.send_error("Task is required")
            return

        # 创建工作流
        output_dir = Path("./output")
        self.workflow = InteractiveWorkflow(
            base_output_dir=output_dir,
            max_retry_per_stage=3,
            on_plan_ready=self.on_plan_ready,
            on_stage_complete=self.on_stage_complete
        )

        # 添加Agent
        self.workflow.add_agent(AnalystAgent(protocol=self.protocol, temperature=0.7))
        self.workflow.add_agent(ArchitectAgent(protocol=self.protocol, temperature=0.5))
        self.workflow.add_agent(CoderAgent(protocol=self.protocol, temperature=0.3))
        self.workflow.add_agent(TesterAgent(protocol=self.protocol, temperature=0.4))

        # 启动工作流
        await self.workflow.start(task)

        # 发送进度
        await self.send_progress()

    async def handle_approve(self, message: dict):
        """处理批准请求"""
        if not self.workflow:
            await self.send_error("Workflow not started")
            return

        modifications = message.get("modifications")
        await self.workflow.approve_plan(modifications)

        # 发送进度
        await self.send_progress()

    async def handle_reject(self, message: dict):
        """处理拒绝请求"""
        if not self.workflow:
            await self.send_error("Workflow not started")
            return

        reason = message.get("reason")
        await self.workflow.reject_plan(reason)

    async def handle_modify(self, message: dict):
        """处理修改请求"""
        if not self.workflow:
            await self.send_error("Workflow not started")
            return

        new_plan = message.get("new_plan")
        if not new_plan:
            await self.send_error("New plan is required")
            return

        await self.workflow.modify_and_approve(new_plan)

        # 发送进度
        await self.send_progress()

    def on_plan_ready(self, agent_name: str, stage_name: str, plan: str):
        """计划准备好的回调"""
        asyncio.create_task(self.send_message({
            "type": "plan_ready",
            "agent_name": agent_name,
            "stage_name": stage_name,
            "plan": plan
        }))

    def on_stage_complete(self, agent_name: str, result):
        """阶段完成的回调"""
        asyncio.create_task(self.send_message({
            "type": "stage_complete",
            "agent_name": agent_name,
            "success": result.success,
            "result": {
                "content": result.content[:500] + "..." if len(result.content) > 500 else result.content,
                "duration": result.duration,
                "saved_files": result.saved_files,
                "error": result.error
            }
        }))

        # 检查是否完成
        if self.workflow.current_stage == WorkflowStage.COMPLETED:
            asyncio.create_task(self.send_message({
                "type": "completed",
                "project_dir": str(self.workflow.get_project_dir())
            }))

    async def send_progress(self):
        """发送进度信息"""
        if not self.workflow:
            return

        progress = self.workflow.get_progress()
        await self.send_message({
            "type": "progress",
            "current": progress["current_stage"],
            "total": progress["total_stages"],
            "percent": progress["progress_percent"],
            "stage": progress["stage"]
        })

    async def send_message(self, message: dict):
        """发送消息给客户端"""
        try:
            await self.websocket.send_text(json.dumps(message, ensure_ascii=False))
        except Exception as e:
            logger.error(f"[InteractiveWS] Failed to send message: {e}")

    async def send_error(self, error: str):
        """发送错误消息"""
        await self.send_message({
            "type": "error",
            "message": error
        })


async def interactive_workflow_endpoint(websocket: WebSocket):
    """
    WebSocket端点

    用法:
    ws = new WebSocket("ws://localhost:8000/ws/interactive-workflow");
    ws.send(JSON.stringify({type: "start", task: "实现一个计算器"}));
    """
    ws_handler = InteractiveWorkflowWebSocket(websocket)
    await ws_handler.connect()
    await ws_handler.handle_messages()


__all__ = ["InteractiveWorkflowWebSocket", "interactive_workflow_endpoint"]
