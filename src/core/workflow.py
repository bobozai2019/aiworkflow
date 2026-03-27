"""
工作流引擎模块

负责Agent编排和任务调度。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.core.context import Context, TaskResult


class Workflow:
    """
    工作流引擎
    
    负责Agent编排和任务调度。
    
    Attributes:
        agents: Agent列表
        on_progress: 进度回调
        base_output_dir: 基础输出目录
    """
    
    def __init__(self, base_output_dir: Path = None, use_existing_project: bool = False) -> None:
        self.agents: List[BaseAgent] = []
        self.on_progress: Optional[Callable[[str, str, float], None]] = None
        self.base_output_dir = base_output_dir or Path("./output")
        self.use_existing_project = use_existing_project
        self._initial_results: dict = {}
    
    def set_initial_context(self, results: dict) -> None:
        """
        设置初始上下文结果
        
        Args:
            results: 初始结果字典，key为agent名称，value为TaskResult
        """
        self._initial_results = results
    
    def add_agent(self, agent: BaseAgent) -> Workflow:
        """
        添加Agent
        
        Args:
            agent: Agent实例
            
        Returns:
            self，支持链式调用
        """
        self.agents.append(agent)
        return self
    
    def _generate_project_name(self, task: str, task_id: str) -> str:
        """
        根据任务描述生成项目名称
        
        Args:
            task: 任务描述
            task_id: 任务ID
            
        Returns:
            项目名称
        """
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]+', task)
        if chinese_chars:
            project_name = ''.join(chinese_chars[:5])
        else:
            words = re.findall(r'[a-zA-Z]+', task)
            project_name = '_'.join(words[:3]).lower() if words else 'project'
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{project_name}_{timestamp}_{task_id}"
    
    def _create_project_dir(self, task: str, task_id: str) -> Path:
        """
        创建项目目录结构
        
        Args:
            task: 任务描述
            task_id: 任务ID
            
        Returns:
            项目目录路径
        """
        if self.use_existing_project and self.base_output_dir:
            logger.info(f"[Workflow] Using existing project directory: {self.base_output_dir}")
            project_dir = self.base_output_dir
        else:
            project_name = self._generate_project_name(task, task_id)
            project_dir = self.base_output_dir / project_name
            project_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[Workflow] Created project directory: {project_dir}")
        
        requirements_dir = project_dir / "requirements"
        code_dir = project_dir / "code"
        tests_dir = project_dir / "tests"
        
        requirements_dir.mkdir(exist_ok=True)
        code_dir.mkdir(exist_ok=True)
        tests_dir.mkdir(exist_ok=True)
        
        logger.info(f"[Workflow] Created directory structure:")
        logger.info(f"  - requirements/: 需求文档目录")
        logger.info(f"  - code/: 代码目录")
        logger.info(f"  - tests/: 测试目录")
        
        return project_dir
    
    def _initialize_permission_manager(self, project_dir: Path) -> None:
        """
        初始化权限管理器
        
        Args:
            project_dir: 项目目录
        """
        from src.core.permission import get_permission_manager
        
        pm = get_permission_manager()
        pm.initialize(project_dir)
        logger.info(f"[Workflow] Permission manager initialized for: {project_dir}")
    
    async def run(
        self,
        task: str,
        task_id: str = None
    ) -> TaskResult:
        """
        执行工作流
        
        Args:
            task: 任务描述
            task_id: 任务ID
            
        Returns:
            最终执行结果
        """
        task_id = task_id or str(uuid.uuid4())[:8]
        context = Context(task_id=task_id)
        
        for agent_name, result in self._initial_results.items():
            context.set_result(agent_name, result)
        
        project_dir = self._create_project_dir(task, task_id)
        context.set("project_dir", str(project_dir))
        
        self._initialize_permission_manager(project_dir)
        
        for agent in self.agents:
            agent.set_output_dir(project_dir)
            agent.update_prompt_output_dir(project_dir)
        
        total_agents = len(self.agents)
        logger.info(f"[Workflow] Starting task {task_id} with {total_agents} agents")
        logger.info(f"[Workflow] Project directory: {project_dir}")
        
        for i, agent in enumerate(self.agents):
            progress = (i + 1) / total_agents * 100
            
            logger.info(f"[Workflow] {'='*50}")
            logger.info(f"[Workflow] 开始执行: {agent.name} ({i+1}/{total_agents})")
            logger.info(f"[Workflow] 进度: {progress:.0f}%")
            
            if self.on_progress:
                self.on_progress(agent.name, "start", progress)
            
            result = await agent.execute(task, context)
            context.set_result(agent.name, result)
            
            if result.success:
                logger.info(f"[Workflow] ✅ {agent.name} 执行成功")
                if result.saved_files:
                    logger.info(f"[Workflow] 保存的文件: {result.saved_files}")
                
                if self.on_progress:
                    self.on_progress(agent.name, "complete", progress)
            else:
                logger.error(f"[Workflow] ❌ {agent.name} 执行失败: {result.error}")
                
                if self.on_progress:
                    self.on_progress(agent.name, "failed", progress)
                
                logger.error(f"[Workflow] Agent {agent.name} failed, stopping workflow")
                return result
        
        final_content = context.get_all_content()
        
        logger.info(f"[Workflow] Task {task_id} completed successfully")
        
        return TaskResult(
            success=True,
            content=final_content,
            agent_id="workflow",
            agent_name="Workflow",
            saved_files=[str(project_dir)]
        )
    
    def get_agent_names(self) -> List[str]:
        """
        获取所有Agent名称
        
        Returns:
            Agent名称列表
        """
        return [agent.name for agent in self.agents]
