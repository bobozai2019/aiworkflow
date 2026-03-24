# tests - 测试目录

本目录包含项目的测试代码。

## 目录结构

```
tests/
├── __init__.py
├── conftest.py           # pytest配置和fixtures
├── test_config.py        # 配置模块测试
├── test_logger.py        # 日志模块测试
├── test_http_client.py   # HTTP客户端测试
├── test_protocols.py     # 协议层测试
├── test_agents.py        # Agent测试
└── test_workflow.py      # 工作流测试
```

## 测试分类

| 测试文件 | 测试内容 | 类型 |
|----------|----------|------|
| `test_config.py` | 配置加载、环境变量替换 | 单元测试 |
| `test_logger.py` | 日志输出、格式化 | 单元测试 |
| `test_http_client.py` | HTTP请求、流式响应 | 单元测试 |
| `test_protocols.py` | 协议接口、API调用 | 集成测试 |
| `test_agents.py` | Agent执行、状态管理 | 集成测试 |
| `test_workflow.py` | 工作流编排、任务调度 | 端到端测试 |

## 运行测试

```bash
# 运行所有测试
pytest

# 运行指定测试文件
pytest tests/test_config.py

# 运行并显示详细输出
pytest -v

# 运行并生成覆盖率报告
pytest --cov=src --cov-report=html
```

## 测试约定

1. 测试文件以 `test_` 开头
2. 测试函数以 `test_` 开头
3. 使用 `pytest` 作为测试框架
4. 使用 `pytest-asyncio` 支持异步测试
5. Mock外部API调用，避免真实请求

## 示例测试

```python
import pytest
from src.utils.config import Config

def test_config_load():
    """测试配置加载"""
    config = Config.load('config/config.yaml')
    assert config is not None
    assert config.get('app.name') == 'Multi-Agent System'

@pytest.mark.asyncio
async def test_protocol_chat():
    """测试协议对话"""
    from src.protocols import create_protocol
    
    protocol = create_protocol('deepseek', api_key='test_key')
    # 使用mock测试
    # ...
```
