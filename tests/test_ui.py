"""
UI模块测试

注意：UI测试需要PyQt5环境，使用pytest-qt插件进行测试。
如果环境不支持GUI，测试将被跳过。
"""

import pytest
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

# 检查PyQt5是否可用
pytest.importorskip("PyQt5", reason="PyQt5 not installed, skipping UI tests")


class TestUIModuleImports:
    """UI模块导入测试"""
    
    def test_import_main_window(self):
        """测试导入主窗口"""
        from src.ui import MainWindow
        assert MainWindow is not None
    
    def test_import_run_gui(self):
        """测试导入run_gui函数"""
        from src.ui import run_gui
        assert callable(run_gui)
    
    def test_import_widgets(self):
        """测试导入组件"""
        from src.ui import (
            ProjectExplorer,
            ChatPanel,
            CodeEditor,
            AgentPanel,
            AgentCard,
            TaskMonitor,
            AgentProgressCard,
            ConfigPanel,
        )
        
        assert ProjectExplorer is not None
        assert ChatPanel is not None
        assert CodeEditor is not None
        assert AgentPanel is not None
        assert TaskMonitor is not None
        assert ConfigPanel is not None


class TestMainWindowCreation:
    """主窗口创建测试"""
    
    @pytest.fixture
    def mock_qapplication(self):
        """模拟QApplication"""
        with patch('PyQt5.QtWidgets.QApplication') as mock_app:
            mock_app.instance.return_value = MagicMock()
            mock_app.exec_.return_value = 0
            yield mock_app
    
    def test_main_window_init(self, mock_qapplication, qtbot):
        """测试主窗口初始化"""
        from src.ui.main_window import MainWindow
        
        window = MainWindow()
        assert window is not None
        assert window.windowTitle() == "Multi-Agent System"
    
    def test_main_window_has_widgets(self, mock_qapplication, qtbot):
        """测试主窗口包含组件"""
        from src.ui.main_window import MainWindow
        
        window = MainWindow()
        
        assert hasattr(window, 'project_explorer')
        assert hasattr(window, 'chat_panel')
        assert hasattr(window, 'code_editor')
        assert hasattr(window, 'agent_panel')
        assert hasattr(window, 'task_monitor')


class TestWorkerThreads:
    """工作线程测试"""
    
    def test_agent_worker_creation(self):
        """测试Agent工作线程创建"""
        from src.ui.main_window import AgentWorker
        from src.core.context import Context
        
        context = Context()
        worker = AgentWorker("test message", "test-model", context)
        
        assert worker._message == "test message"
        assert worker._model == "test-model"
        assert worker._context == context
    
    def test_workflow_worker_creation(self):
        """测试工作流工作线程创建"""
        from src.ui.main_window import WorkflowWorker
        
        worker = WorkflowWorker(
            task="test task",
            agents=["analyst", "coder"],
            config_dir="config"
        )
        
        assert worker._task == "test task"
        assert worker._agents == ["analyst", "coder"]
        assert worker._config_dir == "config"


class TestConfigDialog:
    """配置对话框测试"""
    
    def test_config_dialog_creation(self, qtbot):
        """测试配置对话框创建"""
        from src.ui.main_window import ConfigDialog
        
        dialog = ConfigDialog()
        assert dialog is not None
        assert dialog.windowTitle() == "配置"


class TestChatPanel:
    """对话面板测试"""
    
    def test_chat_panel_creation(self, qtbot):
        """测试对话面板创建"""
        from src.ui.widgets.chat_panel import ChatPanel
        
        panel = ChatPanel()
        assert panel is not None
    
    def test_chat_panel_add_message(self, qtbot):
        """测试添加消息"""
        from src.ui.widgets.chat_panel import ChatPanel
        
        panel = ChatPanel()
        panel.add_message("user", "Hello")
        
        assert len(panel._messages) == 1
    
    def test_chat_panel_clear_messages(self, qtbot):
        """测试清空消息"""
        from src.ui.widgets.chat_panel import ChatPanel
        
        panel = ChatPanel()
        panel.add_message("user", "Hello")
        panel._clear_messages()
        
        assert len(panel._messages) == 0


class TestCodeEditor:
    """代码编辑器测试"""
    
    def test_code_editor_creation(self, qtbot):
        """测试代码编辑器创建"""
        from src.ui.widgets.code_editor import CodeEditor
        
        editor = CodeEditor()
        assert editor is not None
    
    def test_code_editor_is_modified(self, qtbot):
        """测试修改状态"""
        from src.ui.widgets.code_editor import CodeEditor
        
        editor = CodeEditor()
        assert editor.is_modified() is False


class TestAgentPanel:
    """Agent面板测试"""
    
    def test_agent_panel_creation(self, qtbot):
        """测试Agent面板创建"""
        from src.ui.widgets.agent_panel import AgentPanel
        
        panel = AgentPanel()
        assert panel is not None
    
    def test_agent_panel_get_enabled_agents(self, qtbot):
        """测试获取启用的Agent"""
        from src.ui.widgets.agent_panel import AgentPanel
        
        panel = AgentPanel()
        agents = panel.get_enabled_agents()
        
        assert isinstance(agents, list)


class TestTaskMonitor:
    """任务监控测试"""
    
    def test_task_monitor_creation(self, qtbot):
        """测试任务监控创建"""
        from src.ui.widgets.task_monitor import TaskMonitor
        
        monitor = TaskMonitor()
        assert monitor is not None
    
    def test_task_monitor_set_agents(self, qtbot):
        """测试设置Agent列表"""
        from src.ui.widgets.task_monitor import TaskMonitor
        
        monitor = TaskMonitor()
        monitor.set_agents(["analyst", "coder"])
        
        assert len(monitor._agent_cards) == 2
    
    def test_task_monitor_update_progress(self, qtbot):
        """测试更新进度"""
        from src.ui.widgets.task_monitor import TaskMonitor
        
        monitor = TaskMonitor()
        monitor.set_agents(["analyst"])
        monitor.update_agent_progress("analyst", 50.0, "running")
        
        assert "analyst" in monitor._agent_cards


class TestProjectExplorer:
    """工程资源管理器测试"""
    
    def test_project_explorer_creation(self, qtbot):
        """测试工程资源管理器创建"""
        from src.ui.widgets.project_explorer import ProjectExplorer
        
        explorer = ProjectExplorer()
        assert explorer is not None


class TestConfigPanel:
    """配置面板测试"""
    
    def test_config_panel_creation(self, qtbot):
        """测试配置面板创建"""
        from src.ui.widgets.config_panel import ConfigPanel
        
        panel = ConfigPanel()
        assert panel is not None


class TestRunGUI:
    """运行GUI测试"""
    
    def test_run_gui_creates_application(self):
        """测试run_gui创建应用"""
        from src.ui import run_gui
        
        with patch('PyQt5.QtWidgets.QApplication') as mock_app:
            with patch('src.ui.MainWindow') as mock_window:
                mock_app.instance.return_value = None
                mock_app.exec_.return_value = 0
                
                run_gui()
                
                mock_app.assert_called_once()


class TestUISignals:
    """UI信号测试"""
    
    def test_chat_panel_message_signal(self, qtbot):
        """测试对话面板消息信号"""
        from src.ui.widgets.chat_panel import ChatPanel
        
        panel = ChatPanel()
        
        with qtbot.waitSignal(panel.message_sent, timeout=1000, raising=False) as blocker:
            panel.message_sent.emit("test message")
    
    def test_project_explorer_file_signal(self, qtbot):
        """测试工程资源管理器文件信号"""
        from src.ui.widgets.project_explorer import ProjectExplorer
        
        explorer = ProjectExplorer()
        
        with qtbot.waitSignal(explorer.file_selected, timeout=1000, raising=False) as blocker:
            explorer.file_selected.emit("/test/file.py")
