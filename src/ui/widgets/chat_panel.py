"""
对话面板
支持多回合对话、模型切换、进度显示
"""

from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from PyQt5.QtCore import Qt, pyqtSignal, QThread
from PyQt5.QtGui import QFont, QColor, QTextCharFormat
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QComboBox,
    QLabel,
    QSplitter,
    QProgressBar,
    QScrollArea,
    QFrame,
    QSizePolicy,
)

from src.core.message import Message
from src.core.context import Context


class MessageBubble(QFrame):
    """消息气泡组件"""
    
    def __init__(self, role: str, content: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._role = role
        self._content = content
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        role_label = QLabel(self._get_role_display())
        role_label.setStyleSheet(f"font-weight: bold; color: {self._get_role_color()};")
        layout.addWidget(role_label)
        
        content_label = QLabel(self._content)
        content_label.setWordWrap(True)
        content_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(content_label)
        
        self.setStyleSheet(f"""
            MessageBubble {{
                background-color: {self._get_bg_color()};
                border: 1px solid #ddd;
                border-radius: 8px;
                margin: 4px;
            }}
        """)
    
    def _get_role_display(self) -> str:
        role_map = {
            "user": "用户",
            "assistant": "助手",
            "system": "系统",
            "analyst": "分析师",
            "architect": "架构师",
            "coder": "程序员",
            "tester": "测试员",
            "tool": "🔧 工具调用",
            "tool_result": "📋 执行结果",
        }
        return role_map.get(self._role, self._role)
    
    def _get_role_color(self) -> str:
        color_map = {
            "user": "#1976d2",
            "assistant": "#388e3c",
            "system": "#757575",
            "analyst": "#7b1fa2",
            "architect": "#f57c00",
            "coder": "#d32f2f",
            "tester": "#0288d1",
            "tool": "#00695c",
            "tool_result": "#455a64",
        }
        return color_map.get(self._role, "#333333")
    
    def _get_bg_color(self) -> str:
        bg_map = {
            "user": "#e3f2fd",
            "tool": "#e0f2f1",
            "tool_result": "#eceff1",
        }
        return bg_map.get(self._role, "#ffffff")


class ChatPanel(QWidget):
    """
    对话面板组件
    
    支持：
    - 多回合对话历史
    - 模型切换
    - 进度显示
    - 上下文维护
    """
    
    message_sent = pyqtSignal(str)
    model_changed = pyqtSignal(str)
    task_started = pyqtSignal(str)
    task_completed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._messages: List[Message] = []
        self._context: Optional[Context] = None
        self._current_model: str = ""
        self._available_models: List[Dict[str, str]] = []
        self._setup_ui()
        self._load_models()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 4)
        
        self.title_label = QLabel("对话面板")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        model_label = QLabel("模型:")
        header_layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.model_combo.setMinimumWidth(150)
        self.model_combo.currentTextChanged.connect(self._on_model_changed)
        header_layout.addWidget(self.model_combo)
        
        layout.addLayout(header_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(4)
        layout.addWidget(self.progress_bar)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet("QScrollArea { border: 1px solid #ddd; background-color: #f9f9f9; }")
        
        self.messages_container = QWidget()
        self.messages_layout = QVBoxLayout(self.messages_container)
        self.messages_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.messages_layout.setContentsMargins(4, 4, 4, 4)
        self.messages_layout.setSpacing(8)
        
        self.scroll_area.setWidget(self.messages_container)
        layout.addWidget(self.scroll_area, 1)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; padding: 4px; font-size: 11px;")
        layout.addWidget(self.status_label)
        
        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(4, 4, 4, 4)
        
        self.input_edit = QLineEdit()
        self.input_edit.setPlaceholderText("输入消息...")
        self.input_edit.returnPressed.connect(self._send_message)
        self.input_edit.setStyleSheet("padding: 8px; border: 1px solid #ddd; border-radius: 4px;")
        input_layout.addWidget(self.input_edit, 1)
        
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedWidth(80)
        self.send_btn.clicked.connect(self._send_message)
        self.send_btn.setStyleSheet("padding: 8px;")
        input_layout.addWidget(self.send_btn)
        
        self.clear_btn = QPushButton("清空")
        self.clear_btn.setFixedWidth(60)
        self.clear_btn.clicked.connect(self._clear_messages)
        input_layout.addWidget(self.clear_btn)
        
        layout.addLayout(input_layout)
        
        self.setMinimumWidth(300)
    
    def _load_models(self):
        self._available_models = [
            {"id": "deepseek-chat", "name": "DeepSeek Chat", "provider": "deepseek"},
            {"id": "deepseek-reasoner", "name": "DeepSeek Reasoner", "provider": "deepseek"},
            {"id": "qwen-plus", "name": "通义千问 Plus", "provider": "qwen"},
            {"id": "qwen-turbo", "name": "通义千问 Turbo", "provider": "qwen"},
            {"id": "glm-4", "name": "智谱 GLM-4", "provider": "glm"},
            {"id": "glm-4-flash", "name": "智谱 GLM-4-Flash", "provider": "glm"},
            {"id": "abab6.5-chat", "name": "MiniMax abab6.5", "provider": "minimax"},
        ]
        
        self.model_combo.clear()
        for model in self._available_models:
            self.model_combo.addItem(model["name"], model["id"])
        
        if self._available_models:
            self._current_model = self._available_models[0]["id"]
    
    def _on_model_changed(self, text: str):
        index = self.model_combo.currentIndex()
        if index >= 0:
            self._current_model = self.model_combo.itemData(index)
            self.model_changed.emit(self._current_model)
    
    def _send_message(self):
        text = self.input_edit.text().strip()
        if not text:
            return
        
        self.input_edit.clear()
        self.add_message("user", text)
        self.message_sent.emit(text)
    
    def add_message(self, role: str, content: str):
        bubble = MessageBubble(role, content)
        self.messages_layout.addWidget(bubble)
        
        self._messages.append(Message(role=role, content=content))
        
        self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        )
    
    def add_assistant_message(self, content: str, agent_name: str = "assistant"):
        self.add_message(agent_name, content)
    
    def _clear_messages(self):
        while self.messages_layout.count():
            item = self.messages_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._messages.clear()
    
    def set_context(self, context: Context):
        self._context = context
    
    def get_messages(self) -> List[Message]:
        return self._messages.copy()
    
    def get_current_model(self) -> str:
        return self._current_model
    
    def show_progress(self, visible: bool = True):
        self.progress_bar.setVisible(visible)
    
    def set_status(self, status: str):
        self.status_label.setText(status)
    
    def set_input_enabled(self, enabled: bool):
        self.input_edit.setEnabled(enabled)
        self.send_btn.setEnabled(enabled)
