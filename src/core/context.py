"""
上下文管理模块

用于Agent间共享数据和状态。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.message import Message


@dataclass
class TaskResult:
    """
    任务执行结果
    
    Attributes:
        success: 是否成功
        content: 输出内容
        reasoning_content: 思考过程内容
        agent_id: 执行的Agent ID
        agent_name: Agent名称
        duration: 耗时（秒）
        error: 错误信息
        saved_files: 保存的文件路径列表
    """
    
    success: bool
    content: str
    reasoning_content: str = ""
    agent_id: str = ""
    agent_name: str = ""
    duration: float = 0.0
    error: Optional[str] = None
    saved_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "content": self.content,
            "reasoning_content": self.reasoning_content,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "duration": self.duration,
            "error": self.error,
            "saved_files": self.saved_files
        }


@dataclass
class Context:
    """
    执行上下文
    
    用于Agent间共享数据和传递状态。
    
    Attributes:
        task_id: 任务ID
        messages: 消息历史
        results: 各Agent的执行结果
        data: 共享数据
    """
    
    task_id: str = ""
    messages: List[Message] = field(default_factory=list)
    results: Dict[str, TaskResult] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    
    def set(self, key: str, value: Any) -> None:
        """
        存储数据
        
        Args:
            key: 数据键
            value: 数据值
        """
        self.data[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取数据
        
        Args:
            key: 数据键
            default: 默认值
            
        Returns:
            数据值
        """
        return self.data.get(key, default)
    
    def add_message(self, message: Message) -> None:
        """
        添加消息到历史
        
        Args:
            message: 消息对象
        """
        self.messages.append(message)
    
    def set_result(self, agent_name: str, result: TaskResult) -> None:
        """
        设置Agent执行结果
        
        Args:
            agent_name: Agent名称
            result: 执行结果
        """
        self.results[agent_name] = result
    
    def get_result(self, agent_name: str) -> Optional[TaskResult]:
        """
        获取Agent执行结果
        
        Args:
            agent_name: Agent名称
            
        Returns:
            执行结果
        """
        return self.results.get(agent_name)
    
    def get_previous_result(self) -> Optional[TaskResult]:
        """
        获取上一个Agent的执行结果
        
        Returns:
            上一个执行结果
        """
        if not self.results:
            return None
        return list(self.results.values())[-1]
    
    def get_all_content(self) -> str:
        """
        获取所有Agent输出的拼接内容
        
        Returns:
            拼接后的内容
        """
        contents = []
        for name, result in self.results.items():
            if result.success:
                contents.append(f"=== {name} ===\n{result.content}")
        return "\n\n".join(contents)
