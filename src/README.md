# src - 源代码目录

本目录包含项目的所有源代码。

## 目录结构

```
src/
├── core/           # 核心模块 - Agent基类、消息、上下文、工作流
├── agents/         # Agent实现 - 具体角色的Agent
├── protocols/      # 协议适配层 - 大模型API协议实现
├── communication/  # 通信层 - HTTP客户端、WebSocket、通知服务
├── ui/             # PyQt界面 - GUI组件
├── api/            # 移动端API - FastAPI服务
└── utils/          # 工具模块 - 配置、日志、辅助函数
```

## 模块说明

| 模块 | 职责 | 开发优先级 |
|------|------|------------|
| core | 核心业务逻辑，Agent基类和工作流引擎 | 高 |
| agents | 具体Agent角色实现 | 高 |
| protocols | 大模型API协议适配 | 高 |
| communication | 网络通信封装 | 高 |
| utils | 工具函数和配置管理 | 高 |
| ui | 图形界面 | 中 |
| api | 移动端API服务 | 低 |

## 入口文件

- `main.py` - 应用主入口（GUI模式）
- `cli.py` - 命令行入口（CLI模式）
