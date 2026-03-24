"""
代码编辑器
简单的代码查看和编辑组件
"""

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QSyntaxHighlighter, QTextCharFormat, QColor, QKeySequence
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLabel,
    QPushButton,
    QFileDialog,
    QMessageBox,
)


class SimpleHighlighter(QSyntaxHighlighter):
    """简单的语法高亮器"""
    
    def __init__(self, document, language: str = "python"):
        super().__init__(document)
        self._language = language
        self._setup_formats()
    
    def _setup_formats(self):
        self._formats = {}
        
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000ff"))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#008000"))
        
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#ff6600"))
        
        self._formats["keyword"] = keyword_format
        self._formats["string"] = string_format
        self._formats["comment"] = comment_format
        self._formats["number"] = number_format
        
        self._keywords = {
            "python": [
                "def", "class", "if", "else", "elif", "for", "while", "try", "except",
                "finally", "with", "as", "import", "from", "return", "yield", "raise",
                "pass", "break", "continue", "and", "or", "not", "in", "is", "None",
                "True", "False", "lambda", "async", "await", "global", "nonlocal",
            ],
            "javascript": [
                "function", "class", "if", "else", "for", "while", "try", "catch",
                "finally", "return", "yield", "const", "let", "var", "async", "await",
                "import", "export", "from", "new", "this", "super", "extends",
            ],
        }
    
    def highlightBlock(self, text: str):
        language_keywords = self._keywords.get(self._language, [])
        
        for keyword in language_keywords:
            index = text.find(keyword)
            while index >= 0:
                length = len(keyword)
                if (index == 0 or not text[index - 1].isalnum()) and \
                   (index + length >= len(text) or not text[index + length].isalnum()):
                    self.setFormat(index, length, self._formats["keyword"])
                index = text.find(keyword, index + 1)
        
        in_string = False
        string_char = None
        for i, char in enumerate(text):
            if char in '"\'':
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
                self.setFormat(i, 1, self._formats["string"])
            elif in_string:
                self.setFormat(i, 1, self._formats["string"])
        
        comment_start = text.find("#") if self._language == "python" else text.find("//")
        if comment_start >= 0:
            self.setFormat(comment_start, len(text) - comment_start, self._formats["comment"])


class CodeEditor(QWidget):
    """
    简单代码编辑器组件
    
    支持：
    - 打开/保存文件
    - 基本语法高亮
    - 行号显示
    """
    
    file_saved = pyqtSignal(str)
    content_changed = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._current_file: Optional[Path] = None
        self._is_modified: bool = False
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 4)
        
        self.title_label = QLabel("代码编辑器")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.title_label)
        
        self.file_label = QLabel("未打开文件")
        self.file_label.setStyleSheet("color: #666; font-size: 11px;")
        header_layout.addWidget(self.file_label)
        
        header_layout.addStretch()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setFixedHeight(24)
        self.save_btn.clicked.connect(self._save_file)
        self.save_btn.setShortcut(QKeySequence("Ctrl+S"))
        header_layout.addWidget(self.save_btn)
        
        self.save_as_btn = QPushButton("另存为")
        self.save_as_btn.setFixedHeight(24)
        self.save_as_btn.clicked.connect(self._save_file_as)
        header_layout.addWidget(self.save_as_btn)
        
        layout.addLayout(header_layout)
        
        self.editor = QTextEdit()
        self.editor.setFont(QFont("Consolas", 11))
        self.editor.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.editor.setStyleSheet("""
            QTextEdit {
                border: 1px solid #ddd;
                background-color: #fafafa;
            }
        """)
        self.editor.textChanged.connect(self._on_text_changed)
        
        self._highlighter = SimpleHighlighter(self.editor.document(), "python")
        
        layout.addWidget(self.editor)
        
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; padding: 4px; font-size: 11px;")
        layout.addWidget(self.status_label)
    
    def _on_text_changed(self):
        if not self._is_modified:
            self._is_modified = True
            self._update_title()
        self.content_changed.emit()
    
    def _update_title(self):
        if self._current_file:
            title = self._current_file.name
            if self._is_modified:
                title += " *"
            self.file_label.setText(title)
        else:
            self.file_label.setText("未保存文件" if self._is_modified else "未打开文件")
    
    def open_file(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            self.set_status(f"文件不存在: {file_path}")
            return
        
        try:
            content = path.read_text(encoding="utf-8")
            self.editor.setPlainText(content)
            self._current_file = path
            self._is_modified = False
            self._update_title()
            self._update_highlighter(path.suffix)
            self.set_status(f"已打开: {path.name}")
        except Exception as e:
            self.set_status(f"打开失败: {e}")
    
    def _update_highlighter(self, suffix: str):
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "javascript",
        }
        language = language_map.get(suffix.lower(), "python")
        self._highlighter = SimpleHighlighter(self.editor.document(), language)
    
    def _save_file(self):
        if self._current_file:
            try:
                self._current_file.write_text(self.editor.toPlainText(), encoding="utf-8")
                self._is_modified = False
                self._update_title()
                self.set_status(f"已保存: {self._current_file.name}")
                self.file_saved.emit(str(self._current_file))
            except Exception as e:
                self.set_status(f"保存失败: {e}")
        else:
            self._save_file_as()
    
    def _save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存文件",
            str(self._current_file or Path.home()),
            "Python文件 (*.py);;JavaScript文件 (*.js);;所有文件 (*)"
        )
        if file_path:
            path = Path(file_path)
            try:
                path.write_text(self.editor.toPlainText(), encoding="utf-8")
                self._current_file = path
                self._is_modified = False
                self._update_title()
                self._update_highlighter(path.suffix)
                self.set_status(f"已保存: {path.name}")
                self.file_saved.emit(str(path))
            except Exception as e:
                self.set_status(f"保存失败: {e}")
    
    def set_content(self, content: str, language: str = "python"):
        self.editor.setPlainText(content)
        self._current_file = None
        self._is_modified = False
        self._update_title()
        self._highlighter = SimpleHighlighter(self.editor.document(), language)
    
    def get_content(self) -> str:
        return self.editor.toPlainText()
    
    def set_status(self, status: str):
        self.status_label.setText(status)
    
    def get_current_file(self) -> Optional[Path]:
        return self._current_file
    
    def is_modified(self) -> bool:
        return self._is_modified
