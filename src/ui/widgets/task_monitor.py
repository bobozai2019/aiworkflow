"""
任务监控组件

显示任务执行进度和状态。
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QFrame,
    QGroupBox,
)

from src.agents.base_agent import AgentState


class AgentProgressCard(QFrame):
    """Agent进度卡片"""
    
    def __init__(self, agent_name: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._agent_name = agent_name
        self._start_time: Optional[datetime] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        
        self.name_label = QLabel(self._agent_name)
        self.name_label.setStyleSheet("font-weight: bold;")
        header_layout.addWidget(self.name_label)
        
        header_layout.addStretch()
        
        self.status_label = QLabel("等待中")
        self.status_label.setStyleSheet("color: #999;")
        header_layout.addWidget(self.status_label)
        
        layout.addLayout(header_layout)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)
        layout.addWidget(self.progress_bar)
        
        self.time_label = QLabel("")
        self.time_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(self.time_label)
        
        self.setStyleSheet("""
            AgentProgressCard {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
        """)
    
    def start(self):
        """开始执行"""
        self._start_time = datetime.now()
        self.status_label.setText("执行中")
        self.status_label.setStyleSheet("color: #2196f3;")
        self.progress_bar.setValue(0)
    
    def update_progress(self, progress: float):
        """更新进度"""
        self.progress_bar.setValue(int(progress))
        
        if self._start_time:
            elapsed = (datetime.now() - self._start_time).total_seconds()
            self.time_label.setText(f"已用时: {elapsed:.1f}秒")
    
    def complete(self, success: bool = True):
        """完成"""
        self.progress_bar.setValue(100)
        
        if success:
            self.status_label.setText("完成")
            self.status_label.setStyleSheet("color: #4caf50;")
        else:
            self.status_label.setText("失败")
            self.status_label.setStyleSheet("color: #f44336;")
        
        if self._start_time:
            elapsed = (datetime.now() - self._start_time).total_seconds()
            self.time_label.setText(f"耗时: {elapsed:.1f}秒")
    
    def reset(self):
        """重置"""
        self._start_time = None
        self.status_label.setText("等待中")
        self.status_label.setStyleSheet("color: #999;")
        self.progress_bar.setValue(0)
        self.time_label.setText("")


class TaskMonitor(QWidget):
    """
    任务监控组件
    
    显示任务执行进度和各Agent状态。
    """
    
    stop_clicked = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._agent_cards: Dict[str, AgentProgressCard] = {}
        self._task_start_time: Optional[datetime] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 4)
        
        title_label = QLabel("任务监控")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.task_time_label = QLabel("")
        self.task_time_label.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(self.task_time_label)
        
        layout.addLayout(header_layout)
        
        self.total_progress = QProgressBar()
        self.total_progress.setRange(0, 100)
        self.total_progress.setValue(0)
        self.total_progress.setFixedHeight(16)
        self.total_progress.setFormat("总进度: %p%")
        layout.addWidget(self.total_progress)
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("QScrollArea { border: 1px solid #ddd; background-color: #f5f5f5; }")
        
        self.cards_container = QWidget()
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.cards_layout.setContentsMargins(4, 4, 4, 4)
        self.cards_layout.setSpacing(8)
        
        scroll_area.setWidget(self.cards_container)
        layout.addWidget(scroll_area, 1)
        
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(4, 4, 4, 4)
        
        self.stop_btn = QPushButton("停止任务")
        self.stop_btn.clicked.connect(self.stop_clicked.emit)
        btn_layout.addWidget(self.stop_btn)
        
        self.reset_btn = QPushButton("重置")
        self.reset_btn.clicked.connect(self.reset_task)
        btn_layout.addWidget(self.reset_btn)
        
        layout.addLayout(btn_layout)
        
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_time)
        
        self.setMinimumWidth(200)
    
    def set_agents(self, agent_names: list):
        """设置要监控的Agent列表"""
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self._agent_cards.clear()
        
        for name in agent_names:
            card = AgentProgressCard(name)
            self._agent_cards[name] = card
            self.cards_layout.addWidget(card)
    
    def start_task(self):
        """开始任务"""
        self._task_start_time = datetime.now()
        self._timer.start(100)
        self.total_progress.setValue(0)
    
    def update_agent_progress(self, agent_name: str, progress: float, status: str = ""):
        """更新Agent进度"""
        if agent_name in self._agent_cards:
            card = self._agent_cards[agent_name]
            
            if status == "start":
                card.start()
            elif status == "complete":
                card.complete()
            else:
                card.update_progress(progress)
        
        total = sum(c.progress_bar.value() for c in self._agent_cards.values())
        count = len(self._agent_cards)
        if count > 0:
            self.total_progress.setValue(total // count)
    
    def complete_task(self, success: bool = True):
        """完成任务"""
        self._timer.stop()
        
        for card in self._agent_cards.values():
            card.complete(success)
        
        self.total_progress.setValue(100)
    
    def reset_task(self):
        """重置任务"""
        self._task_start_time = None
        self._timer.stop()
        self.total_progress.setValue(0)
        self.task_time_label.setText("")
        
        for card in self._agent_cards.values():
            card.reset()
    
    def _update_time(self):
        """更新时间显示"""
        if self._task_start_time:
            elapsed = (datetime.now() - self._task_start_time).total_seconds()
            self.task_time_label.setText(f"运行时间: {elapsed:.1f}秒")
