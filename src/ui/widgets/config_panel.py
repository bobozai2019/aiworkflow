"""
配置面板组件

显示和编辑系统配置。
"""

from __future__ import annotations

from typing import Dict, Optional

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QComboBox,
    QGroupBox,
    QFormLayout,
    QSpinBox,
    QDoubleSpinBox,
    QMessageBox,
    QTabWidget,
    QTextEdit,
)

from src.utils.config import Config


class ConfigPanel(QWidget):
    """
    配置面板
    
    显示和编辑系统配置。
    """
    
    config_saved = pyqtSignal()
    
    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self._config: Optional[Config] = None
        self._setup_ui()
        self._load_config()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(4, 4, 4, 4)
        
        title_label = QLabel("配置面板")
        title_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        self.save_btn = QPushButton("保存")
        self.save_btn.setFixedHeight(24)
        self.save_btn.clicked.connect(self._save_config)
        header_layout.addWidget(self.save_btn)
        
        layout.addLayout(header_layout)
        
        self.tabs = QTabWidget()
        
        general_tab = QWidget()
        general_layout = QFormLayout(general_tab)
        
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setPlaceholderText("输出目录路径")
        general_layout.addRow("输出目录:", self.output_dir_edit)
        
        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        general_layout.addRow("日志级别:", self.log_level_combo)
        
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(10, 600)
        self.timeout_spin.setValue(60)
        self.timeout_spin.setSuffix(" 秒")
        general_layout.addRow("超时时间:", self.timeout_spin)
        
        self.tabs.addTab(general_tab, "通用")
        
        model_tab = QWidget()
        model_layout = QFormLayout(model_tab)
        
        self.default_model_combo = QComboBox()
        self.default_model_combo.addItems([
            "deepseek-chat",
            "deepseek-reasoner",
            "qwen-plus",
            "qwen-turbo",
            "glm-4",
            "glm-4-flash",
            "abab6.5-chat",
        ])
        model_layout.addRow("默认模型:", self.default_model_combo)
        
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setValue(0.7)
        self.temperature_spin.setSingleStep(0.1)
        model_layout.addRow("温度:", self.temperature_spin)
        
        self.tabs.addTab(model_tab, "模型")
        
        api_tab = QWidget()
        api_layout = QFormLayout(api_tab)
        
        self.deepseek_key_edit = QLineEdit()
        self.deepseek_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.deepseek_key_edit.setPlaceholderText("DeepSeek API Key")
        api_layout.addRow("DeepSeek Key:", self.deepseek_key_edit)
        
        self.qwen_key_edit = QLineEdit()
        self.qwen_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.qwen_key_edit.setPlaceholderText("Qwen API Key")
        api_layout.addRow("Qwen Key:", self.qwen_key_edit)
        
        self.glm_key_edit = QLineEdit()
        self.glm_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.glm_key_edit.setPlaceholderText("GLM API Key")
        api_layout.addRow("GLM Key:", self.glm_key_edit)
        
        self.minimax_key_edit = QLineEdit()
        self.minimax_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.minimax_key_edit.setPlaceholderText("MiniMax API Key")
        api_layout.addRow("MiniMax Key:", self.minimax_key_edit)
        
        self.tabs.addTab(api_tab, "API密钥")
        
        layout.addWidget(self.tabs, 1)
        
        self.setMinimumWidth(300)
    
    def _load_config(self):
        """加载配置"""
        try:
            self._config = Config.load()
            
            output_dir = self._config.get("output_dir", "./output")
            self.output_dir_edit.setText(str(output_dir))
            
            log_level = self._config.get("logging.level", "INFO")
            index = self.log_level_combo.findText(log_level)
            if index >= 0:
                self.log_level_combo.setCurrentIndex(index)
            
            timeout = self._config.get("http.timeout", 60)
            self.timeout_spin.setValue(timeout)
            
            default_model = self._config.get("default_model", "deepseek-chat")
            index = self.default_model_combo.findText(default_model)
            if index >= 0:
                self.default_model_combo.setCurrentIndex(index)
            
            temperature = self._config.get("default_temperature", 0.7)
            self.temperature_spin.setValue(temperature)
            
            deepseek_config = self._config.get_protocol("deepseek")
            if deepseek_config:
                self.deepseek_key_edit.setText(deepseek_config.get("api_key", ""))
            
        except Exception as e:
            print(f"加载配置失败: {e}")
    
    def _save_config(self):
        """保存配置"""
        try:
            if self._config:
                self._config.set("output_dir", self.output_dir_edit.text())
                self._config.set("logging.level", self.log_level_combo.currentText())
                self._config.set("http.timeout", self.timeout_spin.value())
                self._config.set("default_model", self.default_model_combo.currentText())
                self._config.set("default_temperature", self.temperature_spin.value())
                
                self._config.save()
                
                QMessageBox.information(self, "成功", "配置已保存")
                self.config_saved.emit()
        except Exception as e:
            QMessageBox.warning(self, "错误", f"保存配置失败: {e}")
    
    def get_current_config(self) -> Dict:
        """获取当前配置"""
        return {
            "output_dir": self.output_dir_edit.text(),
            "log_level": self.log_level_combo.currentText(),
            "timeout": self.timeout_spin.value(),
            "default_model": self.default_model_combo.currentText(),
            "temperature": self.temperature_spin.value(),
        }
