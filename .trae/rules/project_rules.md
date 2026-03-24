# Project Rules

## Pip 白名单

在沙箱环境中安装Python包时，如果遇到沙箱限制错误，以下包默认允许安装：

### GUI 相关
- PyQt5
- PyQt5-sip
- PyQt5-Qt5
- PyQt6
- PySide6

### 系统工具
- pip
- setuptools
- wheel

### 规则说明
当执行 `pip install` 时遇到 `TRAE Sandbox Error: hit restricted` 错误，这些包应自动添加到白名单中允许安装。

## 开发规范

### 代码风格
- 使用中文注释
- 遵循 PEP 8 规范
- 类型注解使用 Python 3.10+ 语法

### 提交规范
- feat: 新功能
- fix: 修复bug
- docs: 文档更新
- refactor: 重构
- test: 测试相关

## 备份规范

每完成一个系统/模块的开发后，将整个工作目录压缩保存到本地作为备份。

### 备份规则
- **触发时机**: 完成一个完整系统或模块开发后
- **备份位置**: 项目目录内的 `backups/` 子目录（沙箱兼容）
- **命名格式**: `{项目名}_{日期}_{版本或阶段标识}.zip`
  - 示例: `myagent_20260322_v1.0.0.zip`
  - 示例: `myagent_20260322_gui_complete.zip`
- **排除内容**: 
  - `__pycache__/`
  - `*.pyc`
  - `.env` (敏感信息)
  - `logs/`
  - `.git/`
  - `backups/` (避免递归)

### 执行命令示例
```bash
# Windows PowerShell - 在项目目录内创建备份
New-Item -ItemType Directory -Path "D:\AIprogram\myagent\backups" -Force
Compress-Archive -Path "D:\AIprogram\myagent\src", "D:\AIprogram\myagent\config" -DestinationPath "D:\AIprogram\myagent\backups\myagent_20260322_gui_complete.zip" -Force
```

## 沙箱规则

### 沙箱限制处理
- 当操作遇到 `TRAE Sandbox Error` 时，自动在沙箱允许的路径内执行
- 不要触发询问，直接调整方案在沙箱内运行
- 备份、文件操作等都在项目目录内进行
