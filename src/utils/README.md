# utils - 工具模块

本目录包含通用工具函数和配置管理。

## 文件说明

| 文件 | 职责 |
|------|------|
| `config.py` | 配置管理，YAML加载，环境变量替换 |
| `logger.py` | 日志封装，控制台和文件输出 |
| `helpers.py` | 辅助函数 |

## 配置管理

```python
class Config:
    """配置管理器"""
    
    @classmethod
    def load(cls, path: str = 'config/config.yaml') -> 'Config':
        """加载配置文件"""
        pass
    
    def get(self, key: str, default=None):
        """获取配置项，支持点号分隔的路径"""
        pass
```

### 配置文件格式

```yaml
# config/config.yaml
app:
  name: "Multi-Agent System"
  version: "1.0.0"
  debug: true

logging:
  level: INFO
  file: "logs/app.log"

http:
  timeout: 60
  max_retries: 3
```

### 环境变量支持

```yaml
protocols:
  deepseek:
    api_key: "${DEEPSEEK_API_KEY}"  # 从环境变量读取
```

## 日志系统

```python
from src.utils.logger import logger

logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
logger.debug("调试日志")
```

### 日志格式

```
2024-01-15 10:30:45 | INFO | 消息内容
```

## 开发顺序（优先）

1. `config.py` - 配置管理
2. `logger.py` - 日志系统
3. `helpers.py` - 辅助函数
