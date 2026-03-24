# protocols - 协议适配层

本目录包含大模型API协议的实现。

## 文件说明

| 文件 | 说明 |
|------|------|
| `base.py` | 协议抽象基类，定义统一接口 |
| `deepseek.py` | DeepSeek API协议实现 |
| `qwen.py` | 通义千问 API协议实现 |
| `glm.py` | 智谱GLM API协议实现 |
| `minimax.py` | MiniMax API协议实现 |

## 协议基类接口

```python
class BaseProtocol(ABC):
    """协议基类"""
    
    @abstractmethod
    async def chat(
        self, 
        messages: List[Message], 
        stream: bool = True
    ) -> AsyncIterator[str]:
        """对话接口，支持流式输出"""
        pass
    
    @abstractmethod
    def format_messages(self, messages: List[Message]) -> List[Dict]:
        """格式化消息为协议特定格式"""
        pass
```

## 支持的模型

| 模型 | API格式 | Base URL | 特点 |
|------|---------|----------|------|
| DeepSeek | OpenAI兼容 | https://api.deepseek.com | 128K上下文 |
| Qwen | OpenAI兼容 | https://dashscope.aliyuncs.com/compatible-mode/v1 | 长文本支持 |
| GLM | OpenAI兼容 | https://open.bigmodel.cn/api/paas/v4 | 函数调用 |
| MiniMax | OpenAI兼容 | https://api.minimax.chat/v1 | 需要group_id |

## 使用示例

```python
from src.protocols import create_protocol

# 创建协议实例
protocol = create_protocol('deepseek', api_key='your_api_key')

# 流式对话
async for chunk in protocol.chat(messages, stream=True):
    print(chunk, end='')
```

## 开发顺序（MVP）

1. `base.py` - 协议基类
2. `deepseek.py` - DeepSeek协议（优先）
3. `qwen.py` - Qwen协议（后续）
4. `glm.py` - GLM协议（后续）
5. `minimax.py` - MiniMax协议（后续）
