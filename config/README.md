# config - 配置文件目录

本目录包含项目的配置文件。

## 文件说明

| 文件 | 说明 |
|------|------|
| `config.yaml` | 主配置文件，包含应用、日志、HTTP等配置 |
| `agents.yaml` | Agent配置，定义各角色的系统提示词和参数 |
| `protocols.yaml` | 协议配置，定义各模型的API地址和密钥 |

## 配置文件格式

### config.yaml - 主配置

```yaml
app:
  name: "Multi-Agent System"
  version: "1.0.0"
  debug: true

logging:
  level: INFO
  format: "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
  file: "logs/app.log"

http:
  timeout: 60
  max_retries: 3
  pool_size: 5
```

### agents.yaml - Agent配置

```yaml
agents:
  analyst:
    name: "需求分析师"
    model: "deepseek-chat"
    protocol: "deepseek"
    system_prompt: |
      你是一位专业的需求分析师...
    temperature: 0.7
```

### protocols.yaml - 协议配置

```yaml
protocols:
  deepseek:
    base_url: "https://api.deepseek.com"
    api_key: "${DEEPSEEK_API_KEY}"
    default_model: "deepseek-chat"
```

## 环境变量

敏感信息通过环境变量配置，在配置文件中使用 `${VAR_NAME}` 格式引用：

```bash
# .env 文件
DEEPSEEK_API_KEY=your_deepseek_key
QWEN_API_KEY=your_qwen_key
GLM_API_KEY=your_glm_key
MINIMAX_API_KEY=your_minimax_key
MINIMAX_GROUP_ID=your_group_id
```

## 配置加载

```python
from src.utils.config import Config

# 加载配置
config = Config.load('config/config.yaml')

# 获取配置项
app_name = config.get('app.name')
log_level = config.get('logging.level', 'INFO')
```
