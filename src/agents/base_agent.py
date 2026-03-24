"""
Agent基类模块

定义Agent的统一接口和基础功能。
"""

from __future__ import annotations

import re
import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from loguru import logger

from src.agents.processors import DefaultOutputProcessor, OutputProcessor
from src.core.context import Context, TaskResult
from src.core.message import ChatChunk, Message
from src.utils.file_tool import FileTool
from src.utils.protocol_logger import protocol_logger

if TYPE_CHECKING:
    from src.protocols.base import BaseProtocol


class AgentState(Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


class BaseAgent(ABC):
    """
    Agent基类
    
    所有Agent必须继承此类。
    
    Attributes:
        id: Agent唯一标识
        name: Agent名称
        state: 当前状态
        protocol: 使用的协议
        system_prompt: 系统提示词
        output_dir: 输出目录
        processor: 输出处理器
    """
    
    def __init__(
        self,
        name: str,
        protocol: "BaseProtocol",
        system_prompt: str = "",
        model: str = None,
        temperature: float = 0.7,
        output_dir: Path = None,
        processor: Optional[OutputProcessor] = None
    ) -> None:
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.state = AgentState.IDLE
        self.protocol = protocol
        self.system_prompt = system_prompt
        self.model = model
        self.temperature = temperature
        self.output_dir = output_dir or Path("./output")
        self._file_tool = FileTool(self.output_dir) if self.output_dir else None
        self._processor = processor or DefaultOutputProcessor()
        self._on_chunk: Optional[Callable[[str], None]] = None
        self._on_reasoning: Optional[Callable[[str], None]] = None
    
    def on_chunk(self, callback: Callable[[str], None]) -> None:
        """
        设置流式输出回调
        
        Args:
            callback: 回调函数
        """
        self._on_chunk = callback
    
    def on_reasoning(self, callback: Callable[[str], None]) -> None:
        """
        设置思考过程输出回调
        
        Args:
            callback: 回调函数
        """
        self._on_reasoning = callback
    
    def set_output_dir(self, output_dir: Path) -> None:
        """
        动态设置输出目录
        
        Args:
            output_dir: 新的输出目录
        """
        self.output_dir = Path(output_dir)
        self._file_tool = FileTool(self.output_dir)
        logger.debug(f"[{self.name}] Output directory set to: {self.output_dir}")
    
    def update_prompt_output_dir(self, output_dir: Path) -> None:
        """
        更新系统提示词中的输出目录占位符
        
        Args:
            output_dir: 实际输出目录
        """
        if "{OUTPUT_DIR}" in self.system_prompt:
            self.system_prompt = self.system_prompt.replace("{OUTPUT_DIR}", str(output_dir))
            logger.debug(f"[{self.name}] Updated prompt with output dir: {output_dir}")
    
    def parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """解析工具调用（公开方法）"""
        tool_calls = []
        pattern = r'<tool>\s*名称:\s*(\w+)\s*参数:\s*([^<]*?)\s*</tool>'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for name, params_str in matches:
            params = {}
            lines = params_str.split('\n')
            i = 0
            
            while i < len(lines):
                line = lines[i]
                stripped = line.strip()
                param_match = re.match(r'^(\w+):\s*(.*)$', stripped)
                
                if param_match:
                    key = param_match.group(1)
                    value_part = param_match.group(2)
                    
                    if value_part.strip() in ('|-', '|', '>', '>-'):
                        block_lines = []
                        i += 1
                        while i < len(lines):
                            next_line = lines[i]
                            if re.match(r'^\s*\w+: ', next_line):
                                break
                            block_lines.append(next_line)
                            i += 1
                        params[key] = '\n'.join(block_lines).strip()
                        continue
                    
                    elif value_part.strip():
                        params[key] = value_part.strip()
                        i += 1
                        continue
                    
                    else:
                        block_lines = []
                        i += 1
                        while i < len(lines):
                            next_line = lines[i]
                            if re.match(r'^\s*\w+: ', next_line):
                                break
                            if next_line.strip():
                                block_lines.append(next_line)
                            i += 1
                        params[key] = '\n'.join(block_lines).strip()
                        continue
                
                i += 1
            
            tool_calls.append({
                "name": name,
                "params": params
            })
        
        return tool_calls
    
    async def execute_tools(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """执行工具调用（带权限检查，公开方法）"""
        from src.tools.base import ToolRegistry, register_default_tools
        
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
    
    async def execute(
        self,
        task: str,
        context: Optional[Context] = None
    ) -> TaskResult:
        """
        执行任务
        
        Args:
            task: 任务描述
            context: 执行上下文
            
        Returns:
            执行结果
        """
        self.state = AgentState.RUNNING
        start_time = time.time()
        
        logger.info(f"[{self.name}] {'='*50}")
        logger.info(f"[{self.name}] 开始执行任务")
        logger.info(f"[{self.name}] 任务描述: {task[:100]}...")
        
        try:
            messages = self._build_messages(task, context)
            
            content_chunks = []
            reasoning_chunks = []
            in_thinking = False
            iteration = 0
            max_iterations = 10
            
            while iteration < max_iterations:
                iteration += 1
                logger.debug(f"[{self.name}] 开始第 {iteration} 次迭代")
                
                content_chunks = []
                reasoning_chunks = []
                in_thinking = False
                
                async for chunk in self.protocol.chat(
                    messages,
                    model=self.model,
                    temperature=self.temperature
                ):
                    if chunk.reasoning_content:
                        if not in_thinking:
                            in_thinking = True
                            if self._on_reasoning:
                                self._on_reasoning("\n<think/>\n")
                        reasoning_chunks.append(chunk.reasoning_content)
                        if self._on_reasoning:
                            self._on_reasoning(chunk.reasoning_content)
                    
                    if chunk.content:
                        if in_thinking:
                            in_thinking = False
                            if self._on_reasoning:
                                self._on_reasoning("\n</think/>\n")
                        content_chunks.append(chunk.content)
                        if self._on_chunk:
                            self._on_chunk(chunk.content)
                
                content = "".join(content_chunks)
                reasoning = "".join(reasoning_chunks)
                
                tool_calls = self.parse_tool_calls(content)
                logger.debug(f"[{self.name}] 解析到 {len(tool_calls)} 个工具调用")
                
                if not tool_calls:
                    break
                
                logger.info(f"[{self.name}] {'─'*40}")
                logger.info(f"[{self.name}] 发现 {len(tool_calls)} 个工具调用:")
                for idx, call in enumerate(tool_calls, 1):
                    params_str = ", ".join([f"{k}={v[:50]}..." if len(str(v)) > 50 else f"{k}={v}" for k, v in call["params"].items()])
                    logger.info(f"[{self.name}]   {idx}. {call['name']}({params_str})")
                
                tool_results = await self.execute_tools(tool_calls)
                
                logger.info(f"[{self.name}] 工具执行结果:")
                for r in tool_results:
                    status = "✅" if "成功" in r['result'] else "❌"
                    result_preview = r['result'][:100] + "..." if len(r['result']) > 100 else r['result']
                    logger.info(f"[{self.name}]   {status} {r['name']}: {result_preview}")
                
                messages.append(Message(role="assistant", content=content))
                tool_result_content = f"工具执行结果:\n" + "\n\n".join([f"**{r['name']}**:\n{r['result']}" for r in tool_results])
                messages.append(Message(role="user", content=tool_result_content))
            
            content = "".join(content_chunks)
            reasoning = "".join(reasoning_chunks)
            
            logger.info(f"[{self.name}] {'─'*40}")
            logger.info(f"[{self.name}] 开始处理输出内容...")
            
            processed = self._processor.process(content, self.output_dir, self.name)
            saved_files = [str(p) for p in processed.files]
            
            if processed.validation_errors:
                logger.warning(f"[{self.name}] 验证错误: {processed.validation_errors}")
            if processed.validation_warnings:
                logger.info(f"[{self.name}] 验证警告: {processed.validation_warnings}")
            
            if saved_files:
                logger.info(f"[{self.name}] 保存了 {len(saved_files)} 个文件:")
                for f in saved_files:
                    logger.info(f"[{self.name}]   📄 {f}")
            
            if context:
                context.set(f"{self.name}_validation_errors", processed.validation_errors)
                context.set(f"{self.name}_validation_warnings", processed.validation_warnings)
                context.set(f"{self.name}_metadata", processed.metadata)
            
            duration = time.time() - start_time
            self.state = AgentState.COMPLETED
            
            logger.info(f"[{self.name}] {'='*50}")
            logger.info(f"[{self.name}] ✅ 任务执行完成")
            logger.info(f"[{self.name}] 耗时: {duration:.2f}秒")
            logger.info(f"[{self.name}] 保存文件: {len(saved_files)}个")
            
            return TaskResult(
                success=True,
                content=content,
                reasoning_content=reasoning,
                agent_id=self.id,
                agent_name=self.name,
                duration=duration,
                saved_files=saved_files
            )
            
        except Exception as e:
            duration = time.time() - start_time
            self.state = AgentState.ERROR
            
            logger.error(f"[{self.name}] {'='*50}")
            logger.error(f"[{self.name}] ❌ 任务执行失败")
            logger.error(f"[{self.name}] 错误信息: {e}", exc_info=True)
            
            return TaskResult(
                success=False,
                content="",
                agent_id=self.id,
                agent_name=self.name,
                duration=duration,
                error=str(e)
            )
    
    def _build_messages(
        self,
        task: str,
        context: Optional[Context] = None
    ) -> List[Message]:
        """
        构建消息列表
        
        Args:
            task: 任务描述
            context: 执行上下文
            
        Returns:
            消息列表
        """
        messages = []
        
        if self.system_prompt:
            messages.append(Message(role="system", content=self.system_prompt))
        
        if context:
            all_results = context.results
            if all_results:
                context_parts = []
                for agent_name, result in all_results.items():
                    if result.success and result.content:
                        context_parts.append(f"=== {agent_name}的输出 ===\n{result.content}")
                
                if context_parts:
                    task_instruction = self._get_task_instruction()
                    context_content = f"""
以下是之前各Agent的工作成果：

{chr(10).join(context_parts)}

{task_instruction}
"""
                    messages.append(Message(role="user", content=context_content))
        
        messages.append(Message(role="user", content=task))
        
        return messages
    
    def _get_task_instruction(self) -> str:
        """根据Agent角色获取任务指令，子类可重写"""
        return "请基于以上内容继续你的工作。"
    
    @property
    def info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "model": self.model or self.protocol.default_model,
            "processor": self._processor.__class__.__name__
        }
