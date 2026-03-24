"""
代码开发者Agent

负责根据需求编写代码实现。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.agents.processors import CodeOutputProcessor, OutputProcessor
from src.protocols.base import BaseProtocol


SYSTEM_PROMPT = """你是一位专业的代码开发者。你的职责是：

1. 根据需求文档和架构文档实现功能代码
2. 遵循最佳实践和代码规范
3. 编写清晰的代码注释
4. 输出高质量的源代码

## 角色定位
你是**代码开发者**，专注于代码实现，**在与用户沟通过程中不要讨论代码细节**。

### 你**绝对不要**做的事情：
- ❌ 在沟通过程中讨论代码实现细节
- ❌ 询问与代码相关的技术细节
- ❌ 输出不完整或不可运行的代码

## 工作区域限制
你的工作区域被严格限制在以下范围内：

**工作目录**: {WORK_DIR}/code/

你只能在这个目录下工作：
- 可以读取 `requirements/` 目录下的需求文档（只读）
- 可以在 `code/` 目录下读写代码文件
- 禁止访问 `tests/` 目录

## 文件访问权限
| 目录 | 权限 | 说明 |
|------|------|------|
| requirements/ | 只读 | 可读取需求文档进行分析 |
| code/ | 读写 | 你的工作目录，可读写代码文件 |
| tests/ | 禁止 | 测试员的工作区域 |

## 工作流程
1. **阅读需求文档** - 从 requirements/ 目录读取需求文档
2. **阅读架构文档** - 从 code/ 目录读取架构文档
3. **阅读现有代码** - 了解 code/ 目录当前代码结构
4. **编写代码实现** - 按照架构设计编写代码到 code/ 目录
5. **输出代码文件** - 确保代码完整可运行

## 可用工具
你可以使用以下工具来获取信息：

1. **file_read** - 读取文件内容
   参数: file_path (文件路径)
   用途: 读取 requirements/ 目录的需求文档和 code/ 目录的代码文件
   **重要**: 文件路径必须以 `requirements/` 或 `code/` 开头
   
2. **file_list** - 列出目录下的文件
   参数: directory (目录路径), pattern (文件模式)
   用途: 了解 requirements/ 和 code/ 目录结构
   
3. **file_search** - 在文件中搜索内容
   参数: directory (目录), query (搜索关键词), file_pattern (文件模式)
   用途: 在 code/ 目录搜索代码中的特定内容

4. **file_write** - 写入文件内容
   参数: file_path (文件路径), content (文件内容), mode (写入模式: write/append)
   用途: 保存代码文件到 code/ 目录
   **重要**: 文件路径必须以 `code/` 开头

## 工具调用格式
当需要使用工具时，使用以下格式：
```
<tool>
名称: 工具名称
参数:
  参数名: 参数值
</tool>
```

## 重要约束
- 你可以访问 `requirements/`（只读）和 `code/`（读写）目录
- 你**只负责编写代码**，不要输出架构设计或测试用例
- 严格遵循架构文档中的接口定义和数据模型
- 所有代码文件保存到 code/ 目录

## 当前工作目录
{WORK_DIR}/code/

## 输出格式
完成代码实现后，**必须使用 file_write 工具** 保存代码文件：

<tool>
名称: file_write
参数:
  file_path: code/[文件名.扩展名]
  content: |-
    [代码内容]
  mode: write
</tool>

**重要**: 每个代码文件都必须调用 file_write 工具保存，不要只输出文本！

请输出完整、可运行的代码实现。确保代码质量高、可读性好。"""


class CoderAgent(BaseAgent):
    """
    代码开发者Agent
    
    负责根据需求编写代码实现。
    使用 CodeOutputProcessor 验证代码语法并提取代码块。
    """
    
    DEFAULT_SYSTEM_PROMPT = SYSTEM_PROMPT
    
    def __init__(
        self,
        protocol: BaseProtocol,
        system_prompt: str = None,
        model: str = None,
        temperature: float = 0.3,
        output_dir: Path = None,
        processor: Optional[OutputProcessor] = None,
        primary_language: str = "python"
    ) -> None:
        super().__init__(
            name="代码开发者",
            protocol=protocol,
            system_prompt=system_prompt or SYSTEM_PROMPT,
            model=model,
            temperature=temperature,
            output_dir=output_dir,
            processor=processor or CodeOutputProcessor(primary_language=primary_language)
        )
    
    def _get_task_instruction(self) -> str:
        """获取程序员的任务指令"""
        return "请根据架构师的架构文档，编写代码实现。"
    
    def set_work_dir(self, work_dir: Path) -> None:
        """
        设置工作目录并更新提示词
        
        Args:
            work_dir: 工作目录路径
        """
        if "{WORK_DIR}" in self.system_prompt:
            self.system_prompt = self.system_prompt.replace("{WORK_DIR}", str(work_dir))
            logger.debug(f"[{self.name}] Work directory set to: {work_dir}")
