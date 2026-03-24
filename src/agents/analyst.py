"""
需求分析师Agent

负责分析用户需求，输出结构化需求文档。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.agents.processors import OutputProcessor, RequirementOutputProcessor
from src.protocols.base import BaseProtocol


SYSTEM_PROMPT = """你是一位专业的需求分析师。你的职责是与用户进行对话，帮助他们明确和完善需求。

## 角色定位
你是**需求分析师**，专注于业务需求分析，**只关注"做什么"，不关心"怎么做"**。

### 你要做的事情：
- 理解用户的业务需求和目标
- 澄清功能细节、边界条件和验收标准
- 整理结构化的需求文档
- 确认功能优先级和交付时间

### 你**绝对不要**做的事情：
- ❌ 写代码、改代码、看代码
- ❌ 讨论技术实现细节（如"调用哪个py文件"、"用什么框架"、"如何实现"）
- ❌ 关心技术实现方案
- ❌ 读取代码文件
- ❌ 在沟通过程中讨论代码相关内容
- ❌ 询问技术细节问题

## 工作区域限制
你的工作区域被严格限制在以下范围内：

**工作目录**: {WORK_DIR}/requirements/

你只能在这个目录下工作：
- 所有文件读取操作必须在 `requirements/` 目录下
- 所有文件写入操作必须在 `requirements/` 目录下
- 禁止访问其他任何目录（如 code/、tests/ 等）

## 文件访问权限
| 目录 | 权限 | 说明 |
|------|------|------|
| requirements/ | 读写 | 你的工作目录，可读写需求文档 |
| code/ | 禁止 | 程序员的工作区域 |
| tests/ | 禁止 | 测试员的工作区域 |

## 工作流程
1. 理解用户的初始需求描述
2. 如果需要了解项目背景，可以读取 requirements/ 目录下的文档
3. 通过提问澄清模糊的地方
4. 帮助用户确定功能优先级
5. 总结需求并请求用户确认

## 可用工具
你可以使用以下工具来获取信息：

1. **file_read** - 读取文件内容
   参数: file_path (文件路径，必须是 requirements/ 目录下的文件)
   用途: 读取需求文档
   **重要**: 文件路径必须以 `requirements/` 开头
   
2. **file_list** - 列出目录下的文件
   参数: directory (目录路径，必须是 requirements/ 或其子目录)
   用途: 了解 requirements/ 目录结构
   
3. **file_write** - 写入文件内容
   参数: file_path (文件路径), content (文件内容), mode (写入模式: write/append)
   用途: 保存需求文档到 requirements/ 目录
   **重要**: 文件路径必须以 `requirements/` 开头
   
4. **web_search** - 在网络上搜索信息
   参数: query (搜索关键词), num_results (结果数量)
   
5. **web_fetch** - 获取网页内容
   参数: url (网页地址)

## 工具调用格式
当需要使用工具时，使用以下格式：
```
<tool>
名称: 工具名称
参数:
  参数名: 参数值
</tool>
```

## 对话规则
- 每次回复只问1-2个关键问题，不要一次问太多
- 问题要具体，避免过于宽泛
- **只关注"做什么"，不关心"怎么做"**
- 不要问技术细节（如"调用哪个接口"、"用什么类"）
- 当用户说"确认"、"开始执行"、"就这样"等确认词时，**必须使用 file_write 工具保存需求文档**

## 最终需求文档格式
确认需求后，**必须使用 file_write 工具** 将需求文档保存到 requirements/requirements.md：

<tool>
名称: file_write
参数:
  file_path: requirements/requirements.md
  content: |-
    ## 需求确认文档

    ### 项目名称
    [项目名称]

    ### 功能列表
    1. [功能1] - 优先级: 高
    2. [功能2] - 优先级: 中

    ### 技术要求
    [技术栈、框架等要求]

    ### 输出文件
    [需要生成的文件列表]

    ### 确认状态
    需求已确认，等待执行。
  mode: write
</tool>

**重要**: 
1. 确认需求后，必须调用 file_write 工具保存文档，不要只输出文本！
2. 保存文档后，必须在回复末尾明确说：**需求已确认**

## 工作交接说明
需求确认后，你的工作就完成了。后续工作将由以下人员负责：
- **架构师**：设计技术方案
- **程序员**：编写代码实现
- **测试员**：编写测试用例

你不需要关心技术实现，只需要把需求描述清楚即可。

## 当前工作目录
{WORK_DIR}/requirements/"""


class AnalystAgent(BaseAgent):
    """
    需求分析师Agent
    
    负责分析用户需求，输出结构化需求文档。
    使用 RequirementOutputProcessor 验证需求文档格式和完整性。
    """
    
    DEFAULT_SYSTEM_PROMPT = SYSTEM_PROMPT
    CODE_EXTENSIONS = {'.py', '.js', '.ts', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala'}
    
    def __init__(
        self,
        protocol: BaseProtocol,
        system_prompt: str = None,
        model: str = None,
        temperature: float = 0.7,
        output_dir: Path = None,
        processor: Optional[OutputProcessor] = None
    ) -> None:
        super().__init__(
            name="需求分析师",
            protocol=protocol,
            system_prompt=system_prompt or SYSTEM_PROMPT,
            model=model,
            temperature=temperature,
            output_dir=output_dir,
            processor=processor or RequirementOutputProcessor()
        )
    
    async def execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行工具调用 - 需求分析师不能读取代码文件"""
        from src.tools.base import ToolRegistry, register_default_tools
        from src.utils.protocol_logger import protocol_logger
        import time
        
        register_default_tools()
        
        results = []
        for call in tool_calls:
            name = call["name"]
            params = call["params"]
            
            tool = ToolRegistry.get(name)
            if tool:
                valid_params = {}
                param_names = {p.name for p in tool.parameters}
                for key, value in params.items():
                    if key in param_names:
                        valid_params[key] = value
                    else:
                        logger.warning(f"[{self.name}] 忽略未知参数: {key}={value}")
                params = valid_params
            
            # 详细日志：工具调用参数
            logger.info(f"[{self.name}] 🔧 调用工具: {name}")
            for k, v in params.items():
                if isinstance(v, str) and len(v) > 100:
                    preview = v[:100] + "..."
                else:
                    preview = v
                logger.info(f"[{self.name}]   参数 {k}: {preview}")
            
            if name == "file_read" and "file_path" in params:
                file_path = Path(params["file_path"])
                ext = file_path.suffix.lower()
                
                if ext in self.CODE_EXTENSIONS:
                    logger.warning(f"[{self.name}] ⛔ 拒绝读取代码文件: {ext}")
                    results.append({
                        "name": name,
                        "result": f"作为需求分析师，不应该读取代码文件（{ext}）。请专注于文档文件（如 .md, .txt, .json）。"
                    })
                    protocol_logger.log_tool_call(name, params)
                    protocol_logger.log_tool_result(
                        tool_name=name,
                        result=f"拒绝读取代码文件: {ext}",
                        success=False,
                        error="需求分析师不能读取代码文件"
                    )
                    continue
            
            protocol_logger.log_tool_call(name, params)
            
            start_time = time.time()
            result = ToolRegistry.execute_with_permission(name, self.name, **params)
            duration_ms = (time.time() - start_time) * 1000
            
            # 详细日志：工具返回值
            if result.success:
                if isinstance(result.content, str) and len(result.content) > 200:
                    result_preview = result.content[:200] + "..."
                else:
                    result_preview = result.content
                logger.info(f"[{self.name}] ✅ 工具返回 ({duration_ms:.0f}ms): {result_preview}")
                
                results.append({
                    "name": name,
                    "result": result.content
                })
                protocol_logger.log_tool_result(
                    tool_name=name,
                    result=result.content,
                    success=True,
                    duration_ms=duration_ms
                )
            else:
                error_msg = f"执行失败: {result.error}"
                logger.error(f"[{self.name}] ❌ 工具失败 ({duration_ms:.0f}ms): {result.error}")
                
                results.append({
                    "name": name,
                    "result": error_msg
                })
                protocol_logger.log_tool_result(
                    tool_name=name,
                    result=result.error or "",
                    success=False,
                    error=result.error,
                    duration_ms=duration_ms
                )
        
        return results
    
    def set_work_dir(self, work_dir: Path) -> None:
        """
        设置工作目录并更新提示词
        
        Args:
            work_dir: 工作目录路径
        """
        if "{WORK_DIR}" in self.system_prompt:
            self.system_prompt = self.system_prompt.replace("{WORK_DIR}", str(work_dir))
            logger.debug(f"[{self.name}] Work directory set to: {work_dir}")
