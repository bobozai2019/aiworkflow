"""
PyQt界面模块
包含主窗口和UI组件
"""

from src.ui.main_window import MainWindow, run_gui
from src.ui.widgets import ProjectExplorer, ChatPanel, CodeEditor
from src.ui.widgets.agent_panel import AgentPanel, AgentCard
from src.ui.widgets.task_monitor import TaskMonitor, AgentProgressCard
from src.ui.widgets.config_panel import ConfigPanel

__all__ = [
    "MainWindow",
    "run_gui",
    "ProjectExplorer",
    "ChatPanel",
    "CodeEditor",
    "AgentPanel",
    "AgentCard",
    "TaskMonitor",
    "AgentProgressCard",
    "ConfigPanel",
]
