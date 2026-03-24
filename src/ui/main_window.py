"""
主窗口
整合工程资源管理器、代码编辑器、对话面板、Agent面板、任务监控

交互流程：
1. 点击"运行工作流"启动需求分析对话
2. 需求分析师与用户对话，完善需求
3. 用户确认需求后，执行开发任务
"""

from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QCloseEvent, QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QSplitter,
    QStatusBar,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from src.agents.base_agent import AgentState
from src.core.context import Context, TaskResult
from src.core.message import Message
from src.core.workflow_conversation import WorkflowConversationMachine, WorkflowState
from src.ui.widgets.agent_panel import AgentPanel
from src.ui.widgets.chat_panel import ChatPanel
from src.ui.widgets.code_editor import CodeEditor
from src.ui.widgets.config_panel import ConfigPanel
from src.ui.widgets.project_explorer import ProjectExplorer
from src.ui.widgets.protocol_viewer import ProtocolViewerWindow
from src.ui.widgets.task_monitor import TaskMonitor
from src.utils.config import Config
from src.utils.logger import logger


class WorkflowConversationWorker(QThread):
    """工作流对话工作线程"""
    
    message_ready = pyqtSignal(str, str)
    state_changed = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    progress_updated = pyqtSignal(str, str, float)
    ready = pyqtSignal()
    
    def __init__(
        self,
        machine: WorkflowConversationMachine,
        auto_start_session: bool = False,
        project_path = None,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._machine = machine
        self._is_cancelled = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._auto_start_session = auto_start_session
        self._project_path = project_path
    
    def run(self) -> None:
        try:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            def on_message(role: str, content: str) -> None:
                self.message_ready.emit(role, content)
            
            def on_state_change(state: WorkflowState) -> None:
                self.state_changed.emit(state.value)
            
            def on_progress(agent_name: str, status: str, progress: float) -> None:
                self.progress_updated.emit(agent_name, status, progress)
            
            self._machine._on_message = on_message
            self._machine._on_state_change = on_state_change
            self._machine._on_progress = on_progress
            
            if self._auto_start_session:
                self._loop.create_task(self._machine.start_session(self._project_path))
            
            self.ready.emit()
            self._loop.run_forever()
            
        except Exception as e:
            logger.error(f"工作流对话错误: {e}")
            self.error_occurred.emit(str(e))
    
    def send_message(self, message: str) -> None:
        """从主线程调用，异步发送消息（不阻塞）"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._machine.send_message(message),
                self._loop
            )
    
    def start_session(self, project_path) -> None:
        """从主线程调用，异步启动会话（不阻塞）"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._machine.start_session(project_path),
                self._loop
            )
    
    def stop_loop(self) -> None:
        """停止事件循环"""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
    
    def cancel(self) -> None:
        self._is_cancelled = True
        self.stop_loop()


class AgentWorker(QThread):
    """Agent工作线程"""
    
    response_ready = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str)
    finished_signal = pyqtSignal()
    progress_updated = pyqtSignal(str, str, float)
    
    def __init__(
        self,
        message: str,
        model: str,
        context: Context,
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._message: str = message
        self._model: str = model
        self._context: Context = context
        self._is_cancelled: bool = False
    
    def run(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._process_message())
                if not self._is_cancelled:
                    self.response_ready.emit(result, self._model)
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Agent处理错误: {e}")
            self.error_occurred.emit(str(e))
        finally:
            self.finished_signal.emit()
    
    async def _process_message(self) -> str:
        from src.agents.base_agent import BaseAgent
        from src.protocols.deepseek import DeepSeekProtocol
        
        config = Config.load()
        protocol_config = config.get_protocol("deepseek") or {}
        protocol = DeepSeekProtocol(
            api_key=protocol_config.get("api_key", ""),
            base_url=protocol_config.get("base_url", "https://api.deepseek.com"),
            default_model=protocol_config.get("default_model", "deepseek-chat")
        )
        
        agent = BaseAgent(
            name="assistant",
            protocol=protocol,
            system_prompt="你是一个有帮助的AI助手。"
        )
        
        response = await agent.execute(self._message)
        
        self._context.add_message(Message(role="user", content=self._message))
        self._context.add_message(Message(role="assistant", content=response.content))
        
        return response.content
    
    def cancel(self) -> None:
        self._is_cancelled = True


class WorkflowWorker(QThread):
    """工作流工作线程"""
    
    task_completed = pyqtSignal(bool, str)
    agent_progress = pyqtSignal(str, str, float)
    error_occurred = pyqtSignal(str)
    
    def __init__(
        self,
        task: str,
        agents: List[str],
        config_dir: str = "config",
        parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(parent)
        self._task: str = task
        self._agents: List[str] = agents
        self._config_dir: str = config_dir
        self._is_cancelled: bool = False
    
    def run(self) -> None:
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            try:
                result = loop.run_until_complete(self._run_workflow())
                self.task_completed.emit(result.success, result.content or "")
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"工作流错误: {e}")
            self.error_occurred.emit(str(e))
    
    async def _run_workflow(self) -> TaskResult:
        from src.agents.analyst import AnalystAgent
        from src.agents.architect import ArchitectAgent
        from src.agents.coder import CoderAgent
        from src.agents.tester import TesterAgent
        from src.core.workflow import Workflow
        from src.protocols.deepseek import DeepSeekProtocol
        
        config = Config.load(self._config_dir)
        protocol_config = config.get_protocol("deepseek") or {}
        
        protocol = DeepSeekProtocol(
            api_key=protocol_config.get("api_key", ""),
            base_url=protocol_config.get("base_url", "https://api.deepseek.com"),
            default_model=protocol_config.get("default_model", "deepseek-chat")
        )
        
        workflow = Workflow(base_output_dir=config.output_dir)
        
        agent_classes: Dict[str, type] = {
            "analyst": AnalystAgent,
            "architect": ArchitectAgent,
            "coder": CoderAgent,
            "tester": TesterAgent,
        }
        
        agent_configs: Dict[str, Dict[str, Any]] = {
            "analyst": config.get_agent_with_replaced_prompt("analyst") or {},
            "architect": config.get_agent_with_replaced_prompt("architect") or {},
            "coder": config.get_agent_with_replaced_prompt("coder") or {},
            "tester": config.get_agent_with_replaced_prompt("tester") or {},
        }
        
        for agent_name in self._agents:
            if agent_name in agent_classes:
                agent_config = agent_configs.get(agent_name, {})
                agent = agent_classes[agent_name](
                    protocol=protocol,
                    system_prompt=agent_config.get("system_prompt", ""),
                    model=agent_config.get("model"),
                    temperature=agent_config.get("temperature", 0.7)
                )
                workflow.add_agent(agent)
        
        def on_progress(agent_name: str, status: str, progress: float) -> None:
            self.agent_progress.emit(agent_name, status, progress)
        
        workflow.on_progress = on_progress
        
        return await workflow.run(self._task)
    
    def cancel(self) -> None:
        self._is_cancelled = True


class ConfigDialog(QDialog):
    """配置对话框"""
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("配置")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        self.config_panel = ConfigPanel()
        layout.addWidget(self.config_panel)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        from PyQt5.QtWidgets import QPushButton
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        
        layout.addLayout(btn_layout)


class MainWindow(QMainWindow):
    """
    主窗口
    
    布局：
    ┌─────────────────────────────────────────────────────────────────┐
    │  菜单栏 / 工具栏                                                 │
    ├───────────────┬─────────────────┬───────────────────────────────┤
    │               │                 │                               │
    │  工程资源     │   代码编辑器    │    右侧面板                    │
    │  管理器       │                 │  ┌─────────────────────────┐  │
    │  ─────────    │                 │  │ 对话面板                │  │
    │  Agent面板    │                 │  └─────────────────────────┘  │
    │               │                 │  ┌─────────────────────────┐  │
    │               │                 │  │ 任务监控                │  │
    │               │                 │  └─────────────────────────┘  │
    └───────────────┴─────────────────┴───────────────────────────────┘
    
    交互流程：
    1. 点击"运行工作流"启动需求分析对话
    2. 需求分析师与用户对话，完善需求
    3. 用户确认需求后，执行开发任务
    """
    
    def __init__(self) -> None:
        super().__init__()
        
        self._context: Context = Context(task_id=datetime.now().strftime("%Y%m%d_%H%M%S"))
        self._worker: Optional[AgentWorker] = None
        self._workflow_worker: Optional[WorkflowWorker] = None
        self._project_path: Optional[Path] = None
        
        self._workflow_machine: Optional[WorkflowConversationMachine] = None
        self._conversation_worker: Optional[WorkflowConversationWorker] = None
        
        self._protocol_viewer: Optional[ProtocolViewerWindow] = None
        
        self._setup_ui()
        self._setup_menu()
        self._setup_toolbar()
        self._setup_statusbar()
        self._connect_signals()
        
        self._load_default_project()
    
    def _setup_ui(self) -> None:
        self.setWindowTitle("Multi-Agent System")
        self.setMinimumSize(1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.project_explorer = ProjectExplorer()
        left_splitter.addWidget(self.project_explorer)
        
        self.agent_panel = AgentPanel()
        left_splitter.addWidget(self.agent_panel)
        
        left_splitter.setSizes([300, 200])
        
        main_splitter.addWidget(left_splitter)
        
        self.code_editor = CodeEditor()
        main_splitter.addWidget(self.code_editor)
        
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        
        self.chat_panel = ChatPanel()
        right_layout.addWidget(self.chat_panel, 2)
        
        self.task_monitor = TaskMonitor()
        right_layout.addWidget(self.task_monitor, 1)
        
        main_splitter.addWidget(right_widget)
        
        main_splitter.setSizes([200, 500, 400])
        
        layout.addWidget(main_splitter)
    
    def _setup_menu(self) -> None:
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件(&F)")
        
        open_project_action = QAction("打开工程(&O)", self)
        open_project_action.setShortcut(QKeySequence("Ctrl+O"))
        open_project_action.triggered.connect(self._open_project)
        file_menu.addAction(open_project_action)
        
        new_project_action = QAction("新建工程(&N)", self)
        new_project_action.setShortcut(QKeySequence("Ctrl+Shift+N"))
        new_project_action.triggered.connect(self._new_project)
        file_menu.addAction(new_project_action)
        
        file_menu.addSeparator()
        
        save_action = QAction("保存(&S)", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._save_current_file)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        edit_menu = menubar.addMenu("编辑(&E)")
        
        clear_chat_action = QAction("清空对话(&C)", self)
        clear_chat_action.triggered.connect(self.chat_panel._clear_messages)
        edit_menu.addAction(clear_chat_action)
        
        settings_menu = menubar.addMenu("设置(&S)")
        
        config_action = QAction("配置(&C)", self)
        config_action.setShortcut(QKeySequence("Ctrl+,"))
        config_action.triggered.connect(self._show_config)
        settings_menu.addAction(config_action)
        
        help_menu = menubar.addMenu("帮助(&H)")
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("主工具栏")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        open_action = QAction("打开工程", self)
        open_action.triggered.connect(self._open_project)
        toolbar.addAction(open_action)
        
        toolbar.addSeparator()
        
        run_action = QAction("运行工作流", self)
        run_action.triggered.connect(self._run_workflow)
        toolbar.addAction(run_action)
        
        self.stop_action = QAction("停止", self)
        self.stop_action.setEnabled(False)
        self.stop_action.triggered.connect(self._stop_task)
        toolbar.addAction(self.stop_action)
        
        toolbar.addSeparator()
        
        refresh_action = QAction("刷新", self)
        refresh_action.triggered.connect(self._refresh_all)
        toolbar.addAction(refresh_action)
        
        toolbar.addSeparator()
        
        config_action = QAction("配置", self)
        config_action.triggered.connect(self._show_config)
        toolbar.addAction(config_action)
        
        toolbar.addSeparator()
        
        protocol_action = QAction("协议日志", self)
        protocol_action.triggered.connect(self._show_protocol_viewer)
        toolbar.addAction(protocol_action)
    
    def _setup_statusbar(self) -> None:
        self.statusBar().showMessage("就绪")
    
    def _connect_signals(self) -> None:
        self.project_explorer.file_selected.connect(self._on_file_selected)
        self.project_explorer.project_changed.connect(self._on_project_changed)
        
        self.chat_panel.message_sent.connect(self._on_message_sent)
        self.chat_panel.model_changed.connect(self._on_model_changed)
        
        self.code_editor.file_saved.connect(self._on_file_saved)
        
        self.task_monitor.stop_clicked.connect(self._stop_task)
        
        self.agent_panel.agents_changed.connect(self._on_agents_changed)
    
    def _load_default_project(self) -> None:
        config = Config.load()
        last_project = config.get_last_project()
        
        if last_project and Path(last_project).exists():
            self.project_explorer.set_project_path(last_project)
            logger.info(f"已加载上次项目: {last_project}")
        else:
            output_dir = os.environ.get("OUTPUT_DIR", "")
            if output_dir and Path(output_dir).exists():
                self.project_explorer.set_project_path(output_dir)
        
        enabled_agents = self.agent_panel.get_enabled_agents()
        self.task_monitor.set_agents(enabled_agents)
    
    def _open_project(self) -> None:
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择工程目录",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if dir_path:
            self.project_explorer.set_project_path(dir_path)
    
    def _new_project(self) -> None:
        dir_path = QFileDialog.getSaveFileName(
            self,
            "新建工程目录",
            str(Path.home()),
            ""
        )[0]
        if dir_path:
            path = Path(dir_path)
            path.mkdir(parents=True, exist_ok=True)
            self.project_explorer.set_project_path(str(path))
    
    def _save_current_file(self) -> None:
        self.code_editor._save_file()
    
    def _refresh_all(self) -> None:
        self.project_explorer.refresh()
        self.agent_panel._refresh_agents()
    
    def _on_file_selected(self, file_path: str) -> None:
        self.code_editor.open_file(file_path)
        self.statusBar().showMessage(f"已打开: {Path(file_path).name}")
    
    def _on_project_changed(self, project_path: str) -> None:
        self._project_path = Path(project_path)
        self._context.set("project_path", project_path)
        self.statusBar().showMessage(f"工程: {self._project_path.name}")
        
        if self._workflow_machine:
            self._workflow_machine.set_project_path(Path(project_path))
        
        config = Config.load()
        config.set_last_project(project_path)
        logger.info(f"已切换项目: {project_path}")
    
    def _on_message_sent(self, message: str) -> None:
        if self._workflow_machine and self._workflow_machine.can_send_message():
            self._send_workflow_message(message)
            return
        
        if self._worker and self._worker.isRunning():
            self.chat_panel.add_message("system", "请等待当前任务完成...")
            return
        
        self._start_agent_task(message)
    
    def _on_model_changed(self, model: str) -> None:
        self._context.set("current_model", model)
        self.statusBar().showMessage(f"模型切换: {model}")
    
    def _on_file_saved(self, file_path: str) -> None:
        self.statusBar().showMessage(f"已保存: {Path(file_path).name}")
        self.project_explorer.refresh()
    
    def _on_agents_changed(self, agents: List[str]) -> None:
        self.task_monitor.set_agents(agents)
    
    def _start_agent_task(self, message: str) -> None:
        current_model = self.chat_panel.get_current_model()
        
        self._worker = AgentWorker(message, current_model, self._context)
        self._worker.response_ready.connect(self._on_response_ready)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished_signal.connect(self._on_task_finished)
        
        self.chat_panel.show_progress(True)
        self.chat_panel.set_status("处理中...")
        self.chat_panel.set_input_enabled(False)
        self.stop_action.setEnabled(True)
        
        self._worker.start()
    
    def _run_workflow(self) -> None:
        if self._workflow_machine and self._workflow_machine.is_active():
            QMessageBox.information(self, "提示", "已有工作流对话在进行中")
            return
        
        from src.protocols import create_protocol
        
        config = Config.load()
        protocol_config = config.get_protocol("deepseek")
        
        if not protocol_config:
            QMessageBox.warning(self, "警告", "请先配置DeepSeek API密钥")
            return
        
        protocol = create_protocol(
            "deepseek",
            api_key=protocol_config.get("api_key", ""),
            base_url=protocol_config.get("base_url", "https://api.deepseek.com"),
            default_model=protocol_config.get("default_model", "deepseek-chat")
        )
        
        self._workflow_machine = WorkflowConversationMachine(
            protocol=protocol,
            output_dir=config.output_dir,
            project_path=self._project_path,
            on_message=self._on_workflow_message,
            on_state_change=self._on_workflow_state_change,
            on_progress=self._on_workflow_progress
        )
        
        self.chat_panel._clear_messages()
        self.chat_panel.set_input_enabled(True)
        self.chat_panel.set_status("启动工作流...")
        self.stop_action.setEnabled(True)
        
        self._conversation_worker = WorkflowConversationWorker(
            self._workflow_machine,
            auto_start_session=True,
            project_path=self._project_path
        )
        self._conversation_worker.message_ready.connect(self._on_conversation_message)
        self._conversation_worker.state_changed.connect(self._on_conversation_state)
        self._conversation_worker.error_occurred.connect(self._on_error)
        self._conversation_worker.ready.connect(lambda: self.chat_panel.set_status("需求分析对话中..."))
        self._conversation_worker.start()
    
    def _send_workflow_message(self, message: str) -> None:
        if not self._conversation_worker:
            return
        
        self.chat_panel.set_status("发送中...")
        self._conversation_worker.send_message(message)
    
    def _on_workflow_message(self, role: str, content: str) -> None:
        self.chat_panel.add_message(role, content)
    
    def _on_workflow_state_change(self, state: WorkflowState) -> None:
        self.statusBar().showMessage(f"工作流状态: {state.value}")
        
        if state == WorkflowState.EXECUTING:
            self.chat_panel.set_status("正在执行开发任务...")
            self.chat_panel.set_input_enabled(False)
        elif state == WorkflowState.COMPLETED:
            self.chat_panel.set_status("工作流完成")
            self.chat_panel.set_input_enabled(True)
            self.stop_action.setEnabled(False)
            if self._project_path:
                self.project_explorer.refresh()
        elif state == WorkflowState.ERROR:
            self.chat_panel.set_status("工作流出错")
            self.chat_panel.set_input_enabled(True)
            self.stop_action.setEnabled(False)
    
    def _on_workflow_progress(self, agent_name: str, status: str, progress: float) -> None:
        if status == "start":
            self.chat_panel.add_message("system", f"🔄 {agent_name} 开始工作...")
        elif status == "complete":
            self.chat_panel.add_message("system", f"✅ {agent_name} 完成")
    
    def _on_conversation_message(self, role: str, content: str) -> None:
        self.chat_panel.add_message(role, content)
    
    def _on_conversation_state(self, state: str) -> None:
        self.statusBar().showMessage(f"状态: {state}")
    
    def _on_agent_progress(self, agent_name: str, status: str, progress: float) -> None:
        self.task_monitor.update_agent_progress(agent_name, progress, status)
        
        if status == "start":
            self.agent_panel.update_agent_status(agent_name, AgentState.RUNNING)
        elif status == "complete":
            self.agent_panel.update_agent_status(agent_name, AgentState.COMPLETED)
    
    def _on_workflow_completed(self, success: bool, result: str) -> None:
        self.task_monitor.complete_task(success)
        self.stop_action.setEnabled(False)
        self.chat_panel.set_input_enabled(True)
        
        if success:
            self.statusBar().showMessage("工作流完成")
            display_result = result[:500] + "..." if len(result) > 500 else result
            self.chat_panel.add_message("assistant", f"工作流执行完成！\n\n{display_result}")
        else:
            self.statusBar().showMessage("工作流失败")
        
        if self._project_path:
            self.project_explorer.refresh()
    
    def _on_response_ready(self, response: str, model: str) -> None:
        self.chat_panel.add_assistant_message(response)
        self.chat_panel.set_status("完成")
    
    def _on_error(self, error: str) -> None:
        self.chat_panel.add_message("system", f"错误: {error}")
        self.chat_panel.set_status(f"错误: {error}")
        self.statusBar().showMessage(f"错误: {error}")
    
    def _on_task_finished(self) -> None:
        self.chat_panel.show_progress(False)
        self.chat_panel.set_input_enabled(True)
        self.stop_action.setEnabled(False)
    
    def _stop_task(self) -> None:
        if self._worker and self._worker.isRunning():
            self._worker.cancel()
            self._worker.terminate()
            self.chat_panel.add_message("system", "任务已取消")
            self._on_task_finished()
        
        if self._workflow_worker and self._workflow_worker.isRunning():
            self._workflow_worker.cancel()
            self._workflow_worker.terminate()
            self.task_monitor.reset_task()
            self.chat_panel.add_message("system", "工作流已取消")
            self.stop_action.setEnabled(False)
            self.chat_panel.set_input_enabled(True)
        
        if self._workflow_machine:
            self._workflow_machine.cancel()
            self._workflow_machine = None
            self.chat_panel.add_message("system", "工作流对话已取消")
            self.stop_action.setEnabled(False)
            self.chat_panel.set_input_enabled(True)
        
        if self._conversation_worker and self._conversation_worker.isRunning():
            self._conversation_worker.cancel()
            self._conversation_worker.terminate()
            self._conversation_worker = None
    
    def _show_config(self) -> None:
        dialog = ConfigDialog(self)
        dialog.exec_()
    
    def _show_protocol_viewer(self) -> None:
        """显示协议交互查看器"""
        if self._protocol_viewer is None:
            self._protocol_viewer = ProtocolViewerWindow()
            self._protocol_viewer.closed.connect(self._on_protocol_viewer_closed)
        
        self._protocol_viewer.show()
        self._protocol_viewer.raise_()
        self._protocol_viewer.activateWindow()
    
    def _on_protocol_viewer_closed(self) -> None:
        """协议查看器关闭回调"""
        pass
    
    def _show_about(self) -> None:
        QMessageBox.about(
            self,
            "关于",
            "Multi-Agent System v1.0.0\n\n"
            "一个多Agent协作系统\n"
            "支持多种国产大模型\n\n"
            "© 2024"
        )
    
    def closeEvent(self, event: QCloseEvent) -> None:
        if (self._worker and self._worker.isRunning()) or \
           (self._workflow_worker and self._workflow_worker.isRunning()):
            reply = QMessageBox.question(
                self,
                "确认退出",
                "有任务正在运行，确定要退出吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.No:
                event.ignore()
                return
            
            if self._worker:
                self._worker.cancel()
                self._worker.terminate()
                self._worker.wait()
            
            if self._workflow_worker:
                self._workflow_worker.cancel()
                self._workflow_worker.terminate()
                self._workflow_worker.wait()
        
        if self.code_editor.is_modified():
            reply = QMessageBox.question(
                self,
                "未保存的更改",
                "代码编辑器有未保存的更改，是否保存？",
                QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save
            )
            
            if reply == QMessageBox.StandardButton.Save:
                self.code_editor._save_file()
            elif reply == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
        
        if self._project_path and self._project_path.exists():
            config = Config.load()
            config.set_last_project(str(self._project_path))
            logger.info(f"已保存项目路径: {self._project_path}")
        
        event.accept()


def run_gui() -> None:
    """运行GUI应用"""
    import sys
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    app.setStyleSheet("""
        QMainWindow {
            background-color: #f5f5f5;
        }
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #ddd;
        }
        QToolBar {
            background-color: #ffffff;
            border-bottom: 1px solid #ddd;
            spacing: 4px;
            padding: 4px;
        }
        QStatusBar {
            background-color: #ffffff;
            border-top: 1px solid #ddd;
        }
        QPushButton {
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 4px 12px;
        }
        QPushButton:hover {
            background-color: #f0f0f0;
        }
        QPushButton:pressed {
            background-color: #e0e0e0;
        }
        QComboBox {
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 4px;
        }
        QLineEdit {
            background-color: #ffffff;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 4px;
        }
        QSplitter::handle {
            background-color: #ddd;
        }
    """)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    run_gui()
