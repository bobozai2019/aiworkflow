"""
工作流对话状态机

管理工作流的对话式交互流程：
需求分析对话 -> 确认需求 -> 执行开发任务
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from loguru import logger

from src.core.context import Context, TaskResult
from src.core.message import Message
from src.utils.protocol_logger import protocol_logger

if TYPE_CHECKING:
    from src.agents.analyst import AnalystAgent
    from src.protocols.base import BaseProtocol


class WorkflowState(Enum):
    """工作流状态"""
    IDLE = "idle"
    ANALYZING = "analyzing"
    CONFIRMING = "confirming"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ConversationTurn:
    """对话轮次"""
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RequirementSession:
    """需求分析会话"""
    session_id: str
    project_path: Optional[Path] = None
    conversation_history: List[ConversationTurn] = field(default_factory=list)
    collected_requirements: Dict[str, Any] = field(default_factory=dict)
    confirmed: bool = False
    created_at: datetime = field(default_factory=datetime.now)


class WorkflowConversationMachine:
    """
    工作流对话状态机
    
    管理需求分析师与用户的对话流程：
    1. 用户输入初始需求
    2. 需求分析师提问、澄清（可使用工具查询信息）
    3. 用户确认需求
    4. 执行开发任务
    """
    
    CONFIRM_KEYWORDS = ["确认", "开始执行", "就这样", "可以开始", "执行吧", "开始开发", "没问题", "好的开始"]
    
    def __init__(
        self,
        protocol: "BaseProtocol",
        output_dir: Path = None,
        project_path: Path = None,
        on_message: Optional[Callable[[str, str], None]] = None,
        on_state_change: Optional[Callable[[WorkflowState], None]] = None,
        on_progress: Optional[Callable[[str, str, float], None]] = None,
    ):
        self._protocol = protocol
        self._output_dir = output_dir or Path("./output")
        self._project_path = project_path
        self._on_message = on_message
        self._on_state_change = on_state_change
        self._on_progress = on_progress
        
        self._state = WorkflowState.IDLE
        self._session: Optional[RequirementSession] = None
        self._analyst: Optional["AnalystAgent"] = None
        self._context: Optional[Context] = None
        self._confirmed_requirements: str = ""
    
    @property
    def state(self) -> WorkflowState:
        return self._state
    
    @property
    def session(self) -> Optional[RequirementSession]:
        return self._session
    
    @property
    def project_path(self) -> Optional[Path]:
        """获取当前项目路径"""
        return self._project_path
    
    def set_project_path(self, project_path: Path) -> None:
        """
        设置项目路径
        
        Args:
            project_path: 项目路径
        """
        self._project_path = project_path
        logger.info(f"[WorkflowMachine] Project path set to: {project_path}")
    
    def _set_state(self, state: WorkflowState) -> None:
        old_state = self._state
        self._state = state
        logger.info(f"[WorkflowMachine] State: {old_state.value} -> {state.value}")
        if self._on_state_change:
            self._on_state_change(state)
    
    def _emit_message(self, role: str, content: str) -> None:
        if self._on_message:
            self._on_message(role, content)
    
    async def start_session(self, project_path: Path = None) -> None:
        """
        开始新的需求分析会话
        
        Args:
            project_path: 项目路径
        """
        import uuid
        from src.agents.analyst import AnalystAgent
        from src.core.permission import get_permission_manager
        
        if project_path:
            self._project_path = project_path
        
        self._session = RequirementSession(
            session_id=str(uuid.uuid4())[:8],
            project_path=self._project_path
        )
        self._context = Context(task_id=self._session.session_id)
        
        analyst_output_dir = self._project_path if self._project_path else self._output_dir
        
        if self._project_path:
            self._project_path.mkdir(parents=True, exist_ok=True)
            
            requirements_dir = self._project_path / "requirements"
            code_dir = self._project_path / "code"
            tests_dir = self._project_path / "tests"
            
            requirements_dir.mkdir(exist_ok=True)
            code_dir.mkdir(exist_ok=True)
            tests_dir.mkdir(exist_ok=True)
            
            logger.info(f"[WorkflowMachine] Created directory structure:")
            logger.info(f"  - requirements/: 需求文档目录")
            logger.info(f"  - code/: 代码目录")
            logger.info(f"  - tests/: 测试目录")
            
            pm = get_permission_manager()
            pm.initialize(self._project_path)
            logger.info(f"[WorkflowMachine] Permission manager initialized")
        
        self._analyst = AnalystAgent(
            protocol=self._protocol,
            temperature=0.7,
            output_dir=analyst_output_dir
        )
        
        if self._project_path:
            self._analyst.set_work_dir(self._project_path)
        
        self._set_state(WorkflowState.ANALYZING)
        
        work_dir_info = f"\n\n当前工作目录: {self._project_path}" if self._project_path else ""
        welcome_message = f"""你好！我是需求分析师。{work_dir_info}

请描述你的需求，我会通过对话帮助你完善需求文档。"""
        
        self._emit_message("analyst", welcome_message)
        self._session.conversation_history.append(
            ConversationTurn(role="analyst", content=welcome_message)
        )
    
    async def send_message(self, user_message: str) -> None:
        """
        发送用户消息并获取分析师回复
        
        Args:
            user_message: 用户消息
        """
        if not self._session or self._state not in [WorkflowState.ANALYZING, WorkflowState.CONFIRMING]:
            logger.warning(f"[WorkflowMachine] Cannot send message in state: {self._state}")
            return
        
        self._session.conversation_history.append(
            ConversationTurn(role="user", content=user_message)
        )
        
        is_confirm = any(kw in user_message for kw in self.CONFIRM_KEYWORDS)
        
        if is_confirm and self._state == WorkflowState.CONFIRMING:
            await self._execute_workflow()
            return
        
        messages = self._build_conversation_messages()
        
        try:
            iteration = 0
            
            while True:
                iteration += 1
                logger.debug(f"[WorkflowMachine] 开始第 {iteration} 次迭代")
                
                response_content = ""
                chunk_count = 0
                async for chunk in self._protocol.chat(
                    messages,
                    model=self._analyst.model if self._analyst else None,
                    temperature=self._analyst.temperature if self._analyst else 0.7
                ):
                    if chunk.content:
                        response_content += chunk.content
                        chunk_count += 1
                
                logger.debug(f"[WorkflowMachine] 收到响应，chunk数: {chunk_count}, 内容长度: {len(response_content)}")
                logger.debug(f"[WorkflowMachine] 响应内容预览: {response_content[:200]}...")
                
                tool_calls = self._analyst.parse_tool_calls(response_content)
                logger.debug(f"[WorkflowMachine] 解析到 {len(tool_calls)} 个工具调用")
                
                if not tool_calls:
                    self._session.conversation_history.append(
                        ConversationTurn(role="analyst", content=response_content)
                    )
                    
                    if "需求已确认" in response_content:
                        req_file = self._project_path / "requirements" / "requirements.md" if self._project_path else None
                        if req_file and req_file.exists():
                            self._confirmed_requirements = req_file.read_text(encoding='utf-8')
                        else:
                            self._confirmed_requirements = response_content
                        self._set_state(WorkflowState.CONFIRMING)
                        self._emit_message("analyst", response_content + "\n\n---\n**请确认需求后输入\"确认\"或\"开始执行\"来启动开发任务。**")
                    else:
                        self._emit_message("analyst", response_content)
                    break
                
                for call in tool_calls:
                    params_str = ", ".join([f"{k}={v}" for k, v in call["params"].items()])
                    self._emit_message("tool", f"调用 {call['name']}({params_str})")
                
                tool_results = await self._analyst.execute_tools(tool_calls)
                logger.debug(f"[WorkflowMachine] 工具执行完成，结果数: {len(tool_results)}")
                for i, r in enumerate(tool_results):
                    logger.debug(f"[WorkflowMachine] 工具结果[{i}] {r['name']}: {r['result'][:100]}...")
                
                for r in tool_results:
                    result_preview = r['result']
                    if len(result_preview) > 500:
                        result_preview = result_preview[:500] + "...(已截断)"
                    self._emit_message("tool_result", f"结果: {result_preview}")
                
                file_write_success = False
                for call in tool_calls:
                    if call['name'] == 'file_write':
                        file_path = call['params'].get('file_path', '')
                        if 'requirements' in file_path and file_path.endswith('.md'):
                            file_write_success = True
                            break
                
                if file_write_success:
                    req_file = self._project_path / "requirements" / "requirements.md" if self._project_path else None
                    if req_file and req_file.exists():
                        self._confirmed_requirements = req_file.read_text(encoding='utf-8')
                    else:
                        for call in tool_calls:
                            if call['name'] == 'file_write':
                                self._confirmed_requirements = call['params'].get('content', '')
                                break
                    
                    self._session.conversation_history.append(
                        ConversationTurn(role="analyst", content=response_content)
                    )
                    self._set_state(WorkflowState.CONFIRMING)
                    self._emit_message("analyst", "✅ 需求文档已保存！\n\n---\n**请确认需求后输入\"确认\"或\"开始执行\"来启动开发任务。**")
                    break
                
                messages.append(Message(role="assistant", content=response_content))
                tool_result_content = f"工具执行结果:\n" + "\n\n".join([f"**{r['name']}**:\n{r['result']}" for r in tool_results])
                messages.append(Message(role="user", content=tool_result_content))
                logger.debug(f"[WorkflowMachine] 已添加工具结果到消息列表，当前消息数: {len(messages)}")
                logger.debug(f"[WorkflowMachine] 工具结果内容长度: {len(tool_result_content)}")
                
        except Exception as e:
            import traceback
            logger.error(f"[WorkflowMachine] Error in conversation: {e}")
            logger.error(f"[WorkflowMachine] Traceback: {traceback.format_exc()}")
            self._set_state(WorkflowState.ERROR)
            self._emit_message("system", f"对话出错: {str(e)}")
    
    def _build_conversation_messages(self) -> List[Message]:
        """构建对话消息列表"""
        system_prompt = self._analyst.system_prompt if self._analyst else ""
        messages = [Message(role="system", content=system_prompt)]
        
        for turn in self._session.conversation_history:
            role = turn.role
            if role == "analyst":
                role = "assistant"
            messages.append(Message(role=role, content=turn.content))
        
        return messages
    
    async def _execute_workflow(self) -> None:
        """执行工作流 - 需求确认后转交给架构师、程序员、测试员"""
        self._set_state(WorkflowState.EXECUTING)
        self._emit_message("system", "正在启动开发工作流...")
        self._emit_message("system", "📋 需求分析已完成，开始转交给后续团队...")
        
        try:
            from src.core.workflow import Workflow
            from src.core.context import TaskResult
            from src.agents.architect import ArchitectAgent
            from src.agents.coder import CoderAgent
            from src.agents.tester import TesterAgent
            
            use_existing = self._project_path is not None and self._project_path.exists()
            output_dir = self._project_path if use_existing else self._output_dir
            
            workflow = Workflow(
                base_output_dir=output_dir,
                use_existing_project=use_existing
            )
            
            agents = [
                ArchitectAgent(protocol=self._protocol, temperature=0.5, output_dir=output_dir),
                CoderAgent(protocol=self._protocol, temperature=0.3, output_dir=output_dir),
                TesterAgent(protocol=self._protocol, temperature=0.4, output_dir=output_dir),
            ]
            
            for agent in agents:
                if self._project_path:
                    agent.set_work_dir(self._project_path)
                workflow.add_agent(agent)
            
            def on_progress(agent_name: str, status: str, progress: float) -> None:
                if self._on_progress:
                    self._on_progress(agent_name, status, progress)
                
                if status == "start":
                    self._emit_message("system", f"🔄 {agent_name} 开始工作...")
                elif status == "complete":
                    self._emit_message("system", f"✅ {agent_name} 完成")
            
            workflow.on_progress = on_progress
            
            workflow.set_initial_context({
                "需求分析师": TaskResult(
                    success=True,
                    content=self._confirmed_requirements,
                    agent_name="需求分析师"
                )
            })
            
            task = "请开始工作。"
            
            result = await workflow.run(task)
            
            if result.success:
                self._set_state(WorkflowState.COMPLETED)
                self._emit_message("assistant", f"🎉 工作流执行完成！\n\n生成的文件：\n" + "\n".join(f"- {f}" for f in result.saved_files[:10]))
            else:
                self._set_state(WorkflowState.ERROR)
                self._emit_message("system", f"❌ 工作流执行失败: {result.error}")
                
        except Exception as e:
            import traceback
            logger.error(f"[WorkflowMachine] Error executing workflow: {e}")
            logger.error(f"[WorkflowMachine] Traceback: {traceback.format_exc()}")
            self._set_state(WorkflowState.ERROR)
            self._emit_message("system", f"执行出错: {str(e)}")
    
    def cancel(self) -> None:
        """取消当前会话"""
        self._set_state(WorkflowState.IDLE)
        self._session = None
        self._analyst = None
        self._context = None
        self._confirmed_requirements = ""
        self._emit_message("system", "会话已取消")
    
    def is_active(self) -> bool:
        """检查是否有活跃的会话"""
        return self._session is not None and self._state != WorkflowState.IDLE
    
    def can_send_message(self) -> bool:
        """检查是否可以发送消息"""
        return self._state in [WorkflowState.ANALYZING, WorkflowState.CONFIRMING]


__all__ = [
    "WorkflowState",
    "WorkflowConversationMachine",
    "RequirementSession",
    "ConversationTurn",
]
