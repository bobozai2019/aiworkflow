"""
协议交互查看器窗口

显示所有API请求和响应的详细信息，用于调试。
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, List

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QSyntaxHighlighter, QTextCharFormat
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QSplitter,
    QFrame,
    QComboBox,
    QLineEdit,
)

from src.utils.protocol_logger import ProtocolLogEntry, protocol_logger


class JsonHighlighter(QSyntaxHighlighter):
    """JSON语法高亮"""
    
    def __init__(self, document):
        super().__init__(document)
        
        self.key_format = QTextCharFormat()
        self.key_format.setForeground(QColor("#881391"))
        self.key_format.setFontWeight(700)
        
        self.string_format = QTextCharFormat()
        self.string_format.setForeground(QColor("#1a1aa6"))
        
        self.number_format = QTextCharFormat()
        self.number_format.setForeground(QColor("#1c6b48"))
        
        self.boolean_format = QTextCharFormat()
        self.boolean_format.setForeground(QColor("#994500"))
        
        self.null_format = QTextCharFormat()
        self.null_format.setForeground(QColor("#808080"))
    
    def highlightBlock(self, text: str) -> None:
        in_string = False
        escape = False
        start = 0
        
        for i, char in enumerate(text):
            if escape:
                escape = False
                continue
            if char == '\\':
                escape = True
                continue
            if char == '"':
                if in_string:
                    self.setFormat(start, i - start + 1, self.string_format)
                in_string = not in_string
                start = i


class ProtocolViewerWindow(QWidget):
    """
    协议交互查看器窗口
    
    显示所有API请求和响应的详细信息。
    """
    
    closed = pyqtSignal()
    _log_entry_signal = pyqtSignal(object)
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._is_subscribed = False
        self._last_log_count = 0
        self._log_entry_signal.connect(self._on_log_entry_ui)
        self._setup_ui()
        self._subscribe_logger()
    
    def _setup_ui(self) -> None:
        self.setWindowTitle("协议交互查看器")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        toolbar = QHBoxLayout()
        
        filter_label = QLabel("筛选:")
        toolbar.addWidget(filter_label)
        
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["全部", "请求", "响应", "工具调用", "工具结果", "错误"])
        self.filter_combo.currentTextChanged.connect(self._apply_filter)
        toolbar.addWidget(self.filter_combo)
        
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索...")
        self.search_edit.setMaximumWidth(200)
        self.search_edit.textChanged.connect(self._apply_filter)
        toolbar.addWidget(self.search_edit)
        
        toolbar.addStretch()
        
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(self._clear_logs)
        toolbar.addWidget(self.clear_btn)
        
        self.auto_scroll_cb = QPushButton("自动滚动")
        self.auto_scroll_cb.setCheckable(True)
        self.auto_scroll_cb.setChecked(True)
        toolbar.addWidget(self.auto_scroll_cb)
        
        layout.addLayout(toolbar)
        
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        left_panel = QWidget()
        left_panel.setMinimumWidth(200)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        list_label = QLabel("交互记录")
        list_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(list_label)
        
        self.log_list = QListWidget()
        self.log_list.setAlternatingRowColors(True)
        self.log_list.itemClicked.connect(self._on_item_selected)
        self.log_list.setStyleSheet("""
            QListWidget {
                font-family: Consolas, monospace;
                font-size: 11px;
            }
            QListWidget::item {
                padding: 4px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #000;
            }
        """)
        left_layout.addWidget(self.log_list)
        
        splitter.addWidget(left_panel)
        
        right_panel = QWidget()
        right_panel.setMinimumWidth(300)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.detail_header = QLabel("选择一条记录查看详情")
        self.detail_header.setStyleSheet("font-weight: bold; padding: 4px;")
        right_layout.addWidget(self.detail_header)
        
        self.detail_view = QTextEdit()
        self.detail_view.setReadOnly(True)
        self.detail_view.setFont(QFont("Consolas", 10))
        self.detail_view.setStyleSheet("""
            QTextEdit {
                background-color: #fafafa;
                border: 1px solid #ddd;
            }
        """)
        self.detail_view.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        right_layout.addWidget(self.detail_view)
        
        splitter.addWidget(right_panel)
        
        splitter.setSizes([300, 600])
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        
        layout.addWidget(splitter)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; padding: 4px;")
        layout.addWidget(self.status_label)
        
        self._refresh_timer = QTimer()
        self._refresh_timer.timeout.connect(self._do_refresh)
        self._refresh_timer.start(200)
    
    def _subscribe_logger(self) -> None:
        protocol_logger.subscribe(self._on_log_entry)
        self._is_subscribed = True
        self._load_existing_logs()
    
    def _unsubscribe_logger(self) -> None:
        if self._is_subscribed:
            protocol_logger.unsubscribe(self._on_log_entry)
            self._is_subscribed = False
    
    def _load_existing_logs(self) -> None:
        """加载已有日志"""
        logs = protocol_logger.get_logs(limit=500)
        for log in logs:
            self._add_log_item(log)
        self._update_status()
    
    def _on_log_entry(self, entry: ProtocolLogEntry) -> None:
        """日志条目回调 - 从工作线程调用，转发到主线程"""
        self._log_entry_signal.emit(entry)
    
    def _on_log_entry_ui(self, entry: ProtocolLogEntry) -> None:
        """在主线程中添加日志条目"""
        self._add_log_item(entry)
        self._update_status()
    
    def _do_refresh(self) -> None:
        """定时刷新（保留用于其他用途）"""
        pass
    
    def _refresh_list(self) -> None:
        """刷新列表"""
        self.log_list.clear()
        self._load_existing_logs()
    
    def _add_log_item(self, log: ProtocolLogEntry) -> None:
        """添加日志条目到列表"""
        direction_icon = {
            "request": "📤",
            "response": "📥",
            "stream": "📊",
            "tool_call": "🔧",
            "tool_result": "📋",
        }.get(log.direction, "❓")
        
        status_icon = {
            "pending": "⏳",
            "success": "✅",
            "error": "❌",
            "streaming": "🔄",
        }.get(log.status, "")
        
        time_str = log.timestamp.strftime("%H:%M:%S.%f")[:-3]
        
        if log.direction == "request":
            display = f"{direction_icon} [{time_str}] {log.method} {log.provider}"
            if log.request_data and "model" in log.request_data:
                display += f" ({log.request_data['model']})"
        elif log.direction == "response":
            display = f"{direction_icon} [{time_str}] {log.provider} {status_icon}"
            if log.duration_ms:
                display += f" ({log.duration_ms:.0f}ms)"
        elif log.direction == "tool_call":
            display = f"{direction_icon} [{time_str}] 调用 {log.method}"
            if log.request_data:
                params_str = ", ".join([f"{k}={v}" for k, v in list(log.request_data.items())[:3]])
                if len(log.request_data) > 3:
                    params_str += "..."
                display += f"({params_str})"
        elif log.direction == "tool_result":
            display = f"{direction_icon} [{time_str}] {log.method} 结果 {status_icon}"
            if log.duration_ms:
                display += f" ({log.duration_ms:.0f}ms)"
        else:
            display = f"{direction_icon} [{time_str}] {log.provider} {status_icon}"
        
        item = QListWidgetItem(display)
        item.setData(Qt.ItemDataRole.UserRole, log)
        
        if log.status == "error":
            item.setForeground(QColor("#d32f2f"))
        elif log.status == "success":
            item.setForeground(QColor("#388e3c"))
        elif log.direction == "tool_call":
            item.setForeground(QColor("#1565c0"))
        elif log.direction == "tool_result":
            item.setForeground(QColor("#00695c"))
        
        self.log_list.addItem(item)
        
        if self.auto_scroll_cb.isChecked():
            self.log_list.scrollToBottom()
    
    def _on_item_selected(self, item: QListWidgetItem) -> None:
        """选中日志条目"""
        log: ProtocolLogEntry = item.data(Qt.ItemDataRole.UserRole)
        self._show_detail(log)
    
    def _show_detail(self, log: ProtocolLogEntry) -> None:
        """显示日志详情"""
        header_parts = [
            f"时间: {log.timestamp.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}",
            f"提供商: {log.provider}",
            f"方向: {log.direction}",
            f"状态: {log.status}",
        ]
        
        if log.url:
            header_parts.append(f"URL: {log.url}")
        if log.method:
            header_parts.append(f"方法: {log.method}")
        if log.duration_ms:
            header_parts.append(f"耗时: {log.duration_ms:.2f}ms")
        if log.error:
            header_parts.append(f"错误: {log.error}")
        
        self.detail_header.setText(" | ".join(header_parts))
        
        detail_parts = []
        
        if log.request_data:
            detail_parts.append("=== 请求数据 ===")
            detail_parts.append(self._format_json(log.request_data))
        
        if log.response_data:
            detail_parts.append("\n=== 响应数据 ===")
            detail_parts.append(self._format_json(log.response_data))
        
        self.detail_view.setPlainText("\n".join(detail_parts))
    
    def _format_json(self, data: dict) -> str:
        """格式化JSON"""
        try:
            return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[ProtocolViewer] JSON格式化异常: {e}")
            return str(data)
    
    def _apply_filter(self) -> None:
        """应用筛选"""
        filter_type = self.filter_combo.currentText()
        search_text = self.search_edit.text().lower()
        
        for i in range(self.log_list.count()):
            item = self.log_list.item(i)
            log: ProtocolLogEntry = item.data(Qt.ItemDataRole.UserRole)
            
            visible = True
            
            if filter_type != "全部":
                if filter_type == "请求" and log.direction != "request":
                    visible = False
                elif filter_type == "响应" and log.direction != "response":
                    visible = False
                elif filter_type == "工具调用" and log.direction != "tool_call":
                    visible = False
                elif filter_type == "工具结果" and log.direction != "tool_result":
                    visible = False
                elif filter_type == "错误" and log.status != "error":
                    visible = False
            
            if visible and search_text:
                log_str = json.dumps(log.to_dict(), ensure_ascii=False).lower()
                visible = search_text in log_str
            
            item.setHidden(not visible)
    
    def _clear_logs(self) -> None:
        """清空日志"""
        protocol_logger.clear_logs()
        self.log_list.clear()
        self.detail_view.clear()
        self.detail_header.setText("选择一条记录查看详情")
        self._update_status()
    
    def _update_status(self) -> None:
        """更新状态栏"""
        count = self.log_list.count()
        self.status_label.setText(f"共 {count} 条记录")
    
    def closeEvent(self, event) -> None:
        """关闭事件"""
        self._unsubscribe_logger()
        self._refresh_timer.stop()
        self.closed.emit()
        super().closeEvent(event)


__all__ = ["ProtocolViewerWindow"]
