"""
Agent面板组件

显示Agent状态和控制。
"""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QGroupBox,
    QScrollArea,
    QFrame,
    QCheckBox,
)

from src.agents.base_agent import AgentState


class AgentCard(QFrame):
    """Agent卡片组件"""
    
    status_changed = pyqtSignal(str, str)
    configure_clicked = pyqtSignal(str)
    
    def __init__(self, agent_name: str, agent_info: Dict, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._agent_name = agent_name
        self._agent_info = agent_info
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        
        self.name_label = QLabel(self._agent_info.get("display_name", self._agent_name))
        self.name_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        self.status_label = QLabel("空闲")
        self.status_label.setStyleSheet("color: #4caf50;")
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)
        
        self.model_label = QLabel(f"模型: {self._agent_info.get('model', 'default')}")
        self.model_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.model_label)
        
        self.checkbox = QCheckBox("启用")
        self.checkbox.setChecked(True)
        layout.addWidget(self.checkbox)
    
    def update_status(self, status: AgentState):
        """更新状态显示"""
        status_map = {
            AgentState.IDLE: ("空闲", "#4caf50"),
            AgentState.RUNNING: ("运行中", "#2196f3"),
            AgentState.COMPLETED: ("已完成", "#8bc34a"),
            AgentState.ERROR: ("错误", "#f44336"),
        }
        
        text, color = status_map.get(status, ("未知", "#999"))
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color};")
    
    @property
    def is_enabled(self) -> bool:
        return self.checkbox.isChecked()


class AgentPanel(QWidget):
    """
    Agent面板
    
    显示所有Agent的状态和控制选项。
    """
    
    agents_changed = pyqtSignal(list)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._agent_cards: Dict[str, AgentCard] = {}
        self._setup_ui()
        self._load_agents()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 4)
        
        title_label = QLabel("Agent面板")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setFixedHeight(24)
        self.refresh_btn.clicked.connect(self._refresh_agents)
        header_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(header_layout)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: 1px solid #ddd; background-color: #fafafa; }")
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_layout.setSpacing(8)
        
        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area, 1)
        
        self.setMinimumWidth(200)
        self.setMaximumWidth(300)
    
    def _load_agents(self):
        """加载Agent配置"""
        agents_config = {
            "analyst": {
                "display_name": "需求分析师",
                "model": "deepseek-chat",
                "description": "分析需求，输出需求文档"
            },
            "architect": {
                "display_name": "系统架构师",
                "model": "deepseek-chat",
                "description": "设计架构，输出技术方案"
            },
            "coder": {
                "display_name": "程序员",
                "model": "deepseek-chat",
                "description": "编写代码，实现功能"
            },
            "tester": {
                "display_name": "测试员",
                "model": "deepseek-chat",
                "description": "编写测试，输出报告"
            },
        }
        
        for agent_name, agent_info in agents_config.items():
            card = AgentCard(agent_name, agent_info)
            self._agent_cards[agent_name] = card
            self.cards_layout.addWidget(card)
    
    def _refresh_agents(self):
        """刷新Agent状态"""
        pass
    
    def update_agent_status(self, agent_name: str, status: AgentState):
        """更新Agent状态"""
        if agent_name in self._agent_cards:
            self._agent_cards[agent_name].update_status(status)
    
    def get_enabled_agents(self) -> List[str]:
        """获取启用的Agent列表"""
        return [
            name for name, card in self._agent_cards.items()
            if card.is_enabled
        ]
