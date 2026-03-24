"""
UI组件模块
包含各种UI面板和控件
"""

from src.ui.widgets.project_explorer import ProjectExplorer
from src.ui.widgets.chat_panel import ChatPanel
from src.ui.widgets.code_editor import CodeEditor
from src.ui.widgets.agent_panel import AgentPanel
from src.ui.widgets.task_monitor import TaskMonitor
from src.ui.widgets.config_panel import ConfigPanel

__all__ = [
    "ProjectExplorer",
    "ChatPanel",
    "CodeEditor",
    "AgentPanel",
    "TaskMonitor",
    "ConfigPanel",
]
