# ui - PyQt界面

本目录包含PyQt图形界面组件。

## 目录结构

```
ui/
├── __init__.py              # 模块入口
├── main_window.py           # 主窗口
└── widgets/                 # UI组件
    ├── __init__.py
    ├── project_explorer.py  # 工程资源管理器
    ├── chat_panel.py        # 对话面板
    └── code_editor.py       # 代码编辑器
```

## 文件说明

| 文件 | 职责 |
|------|------|
| `main_window.py` | 主窗口，整合所有面板，菜单栏、工具栏、状态栏 |
| `widgets/project_explorer.py` | 工程资源管理器，文件树显示，目录选择 |
| `widgets/chat_panel.py` | 对话面板，多回合对话，模型切换，进度显示 |
| `widgets/code_editor.py` | 代码编辑器，语法高亮，文件保存 |

## 主窗口布局

```
┌─────────────────────────────────────────────────────────────────┐
│  菜单栏  [文件] [编辑] [设置] [帮助]                              │
├─────────────────────────────────────────────────────────────────┤
│  工具栏  [打开工程] | [停止] | [刷新]                             │
├───────────────┬─────────────────────┬───────────────────────────┤
│               │                     │                           │
│   工程资源    │     代码编辑器      │       对话面板            │
│   管理器      │                     │                           │
│               │                     │   [模型选择下拉框]        │
│  [打开]       │   代码内容...       │   ───────────────────     │
│  ───────────  │   代码内容...       │   消息气泡1               │
│  📁 src/      │   代码内容...       │   消息气泡2               │
│    📁 agents/ │   代码内容...       │   ...                     │
│    📁 ui/     │                     │                           │
│      ...      │                     │   ───────────────────     │
│               │                     │   [输入框] [发送] [清空]  │
│               │                     │                           │
├───────────────┴─────────────────────┴───────────────────────────┤
│  状态栏  [就绪] [工程: xxx] [模型: xxx]                           │
└─────────────────────────────────────────────────────────────────┘
```

## 组件详细说明

### 1. 工程资源管理器 (ProjectExplorer)

**功能：**
- 显示当前工程文件夹的文件树结构
- 支持选择/切换工程目录
- 双击文件可在编辑器中打开
- 自动刷新文件列表

**信号：**
- `file_selected(str)` - 文件被选中时发出，参数为文件路径
- `project_changed(str)` - 工程目录变更时发出，参数为目录路径

**使用示例：**
```python
explorer = ProjectExplorer()
explorer.set_project_path("/path/to/project")
explorer.file_selected.connect(self.on_file_selected)
```

### 2. 对话面板 (ChatPanel)

**功能：**
- 多回合对话历史显示（消息气泡形式）
- 模型切换（支持DeepSeek、通义千问、智谱GLM、MiniMax）
- 任务进度条显示
- 上下文维护

**支持的模型：**
| 提供商 | 模型ID | 显示名称 |
|--------|--------|----------|
| DeepSeek | deepseek-chat | DeepSeek Chat |
| DeepSeek | deepseek-reasoner | DeepSeek Reasoner |
| 通义千问 | qwen-plus | 通义千问 Plus |
| 通义千问 | qwen-turbo | 通义千问 Turbo |
| 智谱 | glm-4 | 智谱 GLM-4 |
| 智谱 | glm-4-flash | 智谱 GLM-4-Flash |
| MiniMax | abab6.5-chat | MiniMax abab6.5 |

**信号：**
- `message_sent(str)` - 用户发送消息时发出
- `model_changed(str)` - 模型切换时发出
- `task_started(str)` - 任务开始时发出
- `task_completed()` - 任务完成时发出

**使用示例：**
```python
chat = ChatPanel()
chat.add_message("user", "你好")
chat.add_assistant_message("你好！有什么可以帮助你的？", "assistant")
chat.message_sent.connect(self.on_message)
```

### 3. 代码编辑器 (CodeEditor)

**功能：**
- 打开/保存文件
- 基本语法高亮（Python、JavaScript）
- 文件修改状态跟踪
- 快捷键支持（Ctrl+S 保存）

**信号：**
- `file_saved(str)` - 文件保存时发出，参数为文件路径
- `content_changed()` - 内容变更时发出

**使用示例：**
```python
editor = CodeEditor()
editor.open_file("/path/to/file.py")
editor.set_content("print('Hello')", language="python")
content = editor.get_content()
```

## 启动方式

### 命令行启动
```bash
python -m src.cli --gui
# 或
python -m src.cli -g
```

### 代码启动
```python
from src.ui import run_gui
run_gui()
```

## 依赖

- Python 3.10+
- PyQt5

安装依赖：
```bash
pip install PyQt5
```

## 开发注意事项

1. **UI线程安全**：所有UI操作必须在主线程执行，Agent任务使用QThread在后台运行
2. **信号槽机制**：组件间通信使用Qt信号槽机制
3. **上下文维护**：对话历史通过Context对象维护，支持多回合对话
4. **异步处理**：Agent调用使用asyncio，在QThread中创建事件循环

## 后续计划

- [ ] 完善语法高亮（更多语言支持）
- [ ] 添加代码补全功能
- [ ] 支持多标签页编辑
- [ ] 添加主题切换
- [ ] 支持更多Agent角色显示
