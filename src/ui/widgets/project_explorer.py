"""
工程资源管理器
显示当前工程文件夹的文件树结构
"""

from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSignal, QDir
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QTreeView,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QLabel,
    QHeaderView,
    QFileSystemModel,
)


class ProjectExplorer(QWidget):
    """
    工程资源管理器组件
    
    显示当前工程文件夹的文件树，支持：
    - 选择/切换工程目录
    - 显示文件夹和文件
    - 双击打开文件
    """
    
    file_selected = pyqtSignal(str)
    project_changed = pyqtSignal(str)
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._project_path: Optional[Path] = None
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 4)
        
        self.title_label = QLabel("工程资源管理器")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        self.open_btn = QPushButton("打开")
        self.open_btn.setFixedHeight(24)
        self.open_btn.clicked.connect(self._open_project_dialog)
        header_layout.addWidget(self.open_btn)
        
        layout.addLayout(header_layout)
        
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择工程目录...")
        self.path_edit.setReadOnly(True)
        self.path_edit.setStyleSheet("background-color: #f5f5f5; border: 1px solid #ddd; padding: 4px;")
        layout.addWidget(self.path_edit)
        
        self.file_model = QFileSystemModel()
        self.file_model.setFilter(
            QDir.Filter.AllDirs | QDir.Filter.Files | QDir.Filter.NoDotAndDotDot
        )
        # 禁用图标获取，避免SHGetFileInfo()超时
        self.file_model.setOption(QFileSystemModel.Option.DontUseCustomDirectoryIcons, True)
        self.file_model.setOption(QFileSystemModel.Option.DontWatchForChanges, True)
        
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.file_model)
        self.tree_view.setHeaderHidden(False)
        self.tree_view.setAnimated(True)
        self.tree_view.setIndentation(16)
        self.tree_view.setSortingEnabled(True)
        self.tree_view.sortByColumn(0, Qt.SortOrder.AscendingOrder)
        self.tree_view.doubleClicked.connect(self._on_double_click)
        
        header = self.tree_view.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionHidden(1, True)
        header.setSectionHidden(2, True)
        header.setSectionHidden(3, True)
        
        self.tree_view.setStyleSheet("""
            QTreeView {
                border: 1px solid #ddd;
                background-color: white;
            }
            QTreeView::item:selected {
                background-color: #e3f2fd;
                color: black;
            }
            QTreeView::item:hover {
                background-color: #f5f5f5;
            }
        """)
        
        layout.addWidget(self.tree_view)
        
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)
    
    def _open_project_dialog(self):
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "选择工程目录",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        if dir_path:
            self.set_project_path(dir_path)
    
    def set_project_path(self, path: str):
        self._project_path = Path(path)
        self.path_edit.setText(str(self._project_path))
        
        root_index = self.file_model.setRootPath(str(self._project_path))
        self.tree_view.setRootIndex(root_index)
        
        self.project_changed.emit(str(self._project_path))
    
    def get_project_path(self) -> Optional[Path]:
        return self._project_path
    
    def _on_double_click(self, index):
        file_path = self.file_model.filePath(index)
        file_info = self.file_model.fileInfo(index)
        
        if not file_info.isDir():
            self.file_selected.emit(file_path)
    
    def refresh(self):
        if self._project_path:
            self.file_model.setRootPath("")
            self.file_model.setRootPath(str(self._project_path))
