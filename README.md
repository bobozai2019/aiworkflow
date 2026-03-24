# Multi-Agent System

基于Python的多平台智能Agent系统，支持国产大模型协议、多Agent协作编排。

## 功能特性

- 支持多种国产大模型（DeepSeek、通义千问、智谱GLM、MiniMax）
- 多Agent协作（需求分析师、系统架构师、Coder、测试员）
- 灵活的工作流编排
- PyQt图形界面
- 移动端API支持

## 快速开始

### 环境要求

- Python 3.10+
- Windows/Linux/macOS

### 安装

```bash
# 克隆项目
git clone <repository_url>
cd myagent

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 配置

1. 复制环境变量模板
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填入API密钥
```
DEEPSEEK_API_KEY=your_api_key
```

### 运行

```bash
# 命令行模式
python -m src.cli "实现一个用户登录功能"

# GUI模式
python -m src.main
```

## 项目结构

```
myagent/
├── src/                 # 源代码
│   ├── core/           # 核心模块
│   ├── agents/         # Agent实现
│   ├── protocols/      # 协议适配层
│   ├── communication/  # 通信层
│   ├── ui/             # PyQt界面
│   ├── api/            # 移动端API
│   └── utils/          # 工具模块
├── config/             # 配置文件
├── tests/              # 测试代码
├── plan.md             # 开发计划
└── requirements.txt    # 依赖清单
```

## 开发状态

当前处于 **MVP开发阶段**，详见 [plan.md](plan.md)

## 许可证

MIT License
