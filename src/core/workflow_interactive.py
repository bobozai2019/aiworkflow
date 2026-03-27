"""
交互式工作流引擎

每个Agent执行前需要用户确认计划。
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, List, Optional

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.core.context import Context, TaskResult


class WorkflowStage(Enum):
    """工作流阶段"""
    IDLE = "idle"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentPlan:
    """Agent执行计划"""
    agent_name: str
    stage_name: str
    plan_content: str
    approved: bool = False
    executed: bool = False
    result: Optional[TaskResult] = None


class InteractiveWorkflow:
    """
    交互式工作流引擎

    流程：
    1. 需求分析师 → 生成计划 → 用户确认 → 执行
    2. 系统架构师 → 生成计划 → 用户确认 → 执行
    3. 代码开发者 → 生成计划 → 用户确认 → 执行
    4. 调试员（如需要）→ 生成计划 → 用户确认 → 执行
    5. 测试员 → 生成计划 → 用户确认 → 执行
    """

    def __init__(
        self,
        base_output_dir: Path = None,
        use_existing_project: bool = False,
        max_retry_per_stage: int = 3,
        on_plan_ready: Optional[Callable[[str, str, str], None]] = None,
        on_stage_complete: Optional[Callable[[str, TaskResult], None]] = None
    ) -> None:
        self.base_output_dir = base_output_dir or Path("./output")
        self.use_existing_project = use_existing_project
        self.max_retry_per_stage = max_retry_per_stage

        # 回调函数
        self.on_plan_ready = on_plan_ready  # (agent_name, stage_name, plan) -> None
        self.on_stage_complete = on_stage_complete  # (agent_name, result) -> None

        # 状态管理
        self._stage = WorkflowStage.IDLE
        self._agents: List[BaseAgent] = []
        self._plans: List[AgentPlan] = []
        self._current_plan_index = 0
        self._context: Optional[Context] = None
        self._project_dir: Optional[Path] = None
        self._task: str = ""

    def add_agent(self, agent: BaseAgent) -> "InteractiveWorkflow":
        """添加Agent"""
        self.agents.append(agent)
        return self

    @property
    def agents(self) -> List[BaseAgent]:
        """获取Agent列表"""
        return self._agents

    @property
    def current_stage(self) -> WorkflowStage:
        """获取当前阶段"""
        return self._stage

    @property
    def current_plan(self) -> Optional[AgentPlan]:
        """获取当前计划"""
        if 0 <= self._current_plan_index < len(self._plans):
            return self._plans[self._current_plan_index]
        return None

    def _generate_project_name(self, task: str, task_id: str) -> str:
        """生成项目名称"""
        import re
        chinese_chars = re.findall(r'[\u4e00-\u9fa5]+', task)
        if chinese_chars:
            project_name = ''.join(chinese_chars[:5])
        else:
            words = re.findall(r'[a-zA-Z]+', task)
            project_name = '_'.join(words[:3]).lower() if words else 'project'

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{project_name}_{timestamp}_{task_id}"

    def _create_project_dir(self, task: str, task_id: str) -> Path:
        """创建项目目录"""
        if self.use_existing_project and self.base_output_dir:
            project_dir = self.base_output_dir
        else:
            project_name = self._generate_project_name(task, task_id)
            project_dir = self.base_output_dir / project_name
            project_dir.mkdir(parents=True, exist_ok=True)

        requirements_dir = project_dir / "requirements"
        code_dir = project_dir / "code"
        tests_dir = project_dir / "tests"

        requirements_dir.mkdir(exist_ok=True)
        code_dir.mkdir(exist_ok=True)
        tests_dir.mkdir(exist_ok=True)

        return project_dir

    def _initialize_permission_manager(self, project_dir: Path) -> None:
        """初始化权限管理器"""
        from src.core.permission import get_permission_manager

        pm = get_permission_manager()
        pm.initialize(project_dir)

    async def start(self, task: str, task_id: str = None) -> None:
        """
        启动工作流

        Args:
            task: 任务描述
            task_id: 任务ID
        """
        task_id = task_id or str(uuid.uuid4())[:8]
        self._task = task
        self._context = Context(task_id=task_id)

        # 创建项目目录
        self._project_dir = self._create_project_dir(task, task_id)
        self._context.set("project_dir", str(self._project_dir))

        # 初始化权限管理器
        self._initialize_permission_manager(self._project_dir)

        # 注册执行工具
        from src.tools.executor import register_executor_tools
        register_executor_tools()

        # 设置Agent输出目录
        for agent in self._agents:
            agent.set_output_dir(self._project_dir)
            agent.update_prompt_output_dir(self._project_dir)

        logger.info(f"[InteractiveWorkflow] Started task {task_id}")
        logger.info(f"[InteractiveWorkflow] Project: {self._project_dir}")

        # 开始第一个Agent的计划生成
        await self._generate_next_plan()

    async def _generate_next_plan(self) -> None:
        """生成下一个Agent的计划"""
        if self._current_plan_index >= len(self._agents):
            # 所有Agent都已完成
            self._stage = WorkflowStage.COMPLETED
            logger.info("[InteractiveWorkflow] All agents completed")
            return

        agent = self._agents[self._current_plan_index]
        self._stage = WorkflowStage.PLANNING

        logger.info(f"[InteractiveWorkflow] Generating plan for: {agent.name}")

        # 生成计划
        plan_content = await self._generate_agent_plan(agent)

        # 创建计划对象
        stage_name = self._get_stage_name(self._current_plan_index)
        plan = AgentPlan(
            agent_name=agent.name,
            stage_name=stage_name,
            plan_content=plan_content
        )
        self._plans.append(plan)

        # 切换到等待批准状态
        self._stage = WorkflowStage.WAITING_APPROVAL

        # 通知用户计划已准备好
        if self.on_plan_ready:
            self.on_plan_ready(agent.name, stage_name, plan_content)

        logger.info(f"[InteractiveWorkflow] Plan ready for: {agent.name}")

    async def _generate_agent_plan(self, agent: BaseAgent) -> str:
        """
        生成Agent的执行计划

        Args:
            agent: Agent实例

        Returns:
            计划内容
        """
        # 构建计划生成提示
        plan_prompt = self._build_plan_prompt(agent)

        # 调用LLM生成计划
        from src.core.message import Message

        messages = [
            Message(role="system", content=agent.system_prompt),
            Message(role="user", content=plan_prompt)
        ]

        plan_content = ""
        async for chunk in agent.protocol.chat(
            messages,
            model=agent.model,
            temperature=0.3  # 使用较低温度生成计划
        ):
            if chunk.content:
                plan_content += chunk.content

        return plan_content

    def _build_plan_prompt(self, agent: BaseAgent) -> str:
        """
        构建计划生成提示

        Args:
            agent: Agent实例

        Returns:
            提示内容
        """
        # 获取之前Agent的输出
        previous_outputs = []
        for prev_plan in self._plans:
            if prev_plan.executed and prev_plan.result and prev_plan.result.success:
                previous_outputs.append(
                    f"=== {prev_plan.agent_name}的输出 ===\n{prev_plan.result.content[:500]}..."
                )

        context_info = "\n\n".join(previous_outputs) if previous_outputs else "这是第一个阶段，没有前置输出。"

        prompt = f"""
任务描述: {self._task}

之前的工作成果:
{context_info}

请根据以上信息，制定你的工作计划。

**重要**: 请按照以下格式输出你的计划：

## 工作计划

### 1. 分析阶段
- [ ] 分析任务需求
- [ ] 确定工作范围
- [ ] 识别关键要点

### 2. 执行阶段
- [ ] 具体步骤1
- [ ] 具体步骤2
- [ ] 具体步骤3

### 3. 输出阶段
- [ ] 生成文档/代码
- [ ] 验证输出质量
- [ ] 保存到指定目录

### 4. 预期产出
- 文件1: [文件名] - [说明]
- 文件2: [文件名] - [说明]

### 5. 预计耗时
约 [X] 分钟

请详细列出你的工作计划，让用户了解你将要做什么。
"""
        return prompt

    def _get_stage_name(self, index: int) -> str:
        """获取阶段名称"""
        stage_names = [
            "阶段1: 需求分析",
            "阶段2: 系统架构设计",
            "阶段3: 代码开发",
            "阶段4: 代码调试",
            "阶段5: 测试验证"
        ]
        if index < len(stage_names):
            return stage_names[index]
        return f"阶段{index + 1}"

    async def approve_plan(self, modifications: str = None) -> None:
        """
        批准当前计划并执行

        Args:
            modifications: 用户对计划的修改建议（可选）
        """
        if self._stage != WorkflowStage.WAITING_APPROVAL:
            logger.warning(f"[InteractiveWorkflow] Cannot approve in stage: {self._stage}")
            return

        plan = self.current_plan
        if not plan:
            logger.error("[InteractiveWorkflow] No current plan to approve")
            return

        # 如果用户提供了修改建议，更新计划
        if modifications:
            plan.plan_content += f"\n\n## 用户修改建议\n{modifications}"
            logger.info(f"[InteractiveWorkflow] Plan modified by user")

        plan.approved = True
        self._stage = WorkflowStage.EXECUTING

        logger.info(f"[InteractiveWorkflow] Executing: {plan.agent_name}")

        # 执行Agent
        agent = self._agents[self._current_plan_index]
        result = await agent.execute(self._task, self._context)

        # 保存结果
        plan.executed = True
        plan.result = result
        self._context.set_result(agent.name, result)

        # 通知阶段完成
        if self.on_stage_complete:
            self.on_stage_complete(agent.name, result)

        if result.success:
            logger.info(f"[InteractiveWorkflow] ✅ {agent.name} completed")

            # 移动到下一个Agent
            self._current_plan_index += 1
            await self._generate_next_plan()
        else:
            logger.error(f"[InteractiveWorkflow] ❌ {agent.name} failed: {result.error}")
            self._stage = WorkflowStage.ERROR

    async def reject_plan(self, reason: str = None) -> None:
        """
        拒绝当前计划

        Args:
            reason: 拒绝原因
        """
        if self._stage != WorkflowStage.WAITING_APPROVAL:
            logger.warning(f"[InteractiveWorkflow] Cannot reject in stage: {self._stage}")
            return

        plan = self.current_plan
        if not plan:
            logger.error("[InteractiveWorkflow] No current plan to reject")
            return

        logger.info(f"[InteractiveWorkflow] Plan rejected: {plan.agent_name}")
        if reason:
            logger.info(f"[InteractiveWorkflow] Reason: {reason}")

        # 重新生成计划
        self._plans.pop()  # 移除被拒绝的计划
        await self._generate_next_plan()

    async def modify_and_approve(self, new_plan: str) -> None:
        """
        修改计划并批准

        Args:
            new_plan: 新的计划内容
        """
        if self._stage != WorkflowStage.WAITING_APPROVAL:
            logger.warning(f"[InteractiveWorkflow] Cannot modify in stage: {self._stage}")
            return

        plan = self.current_plan
        if not plan:
            logger.error("[InteractiveWorkflow] No current plan to modify")
            return

        # 更新计划内容
        plan.plan_content = new_plan
        logger.info(f"[InteractiveWorkflow] Plan modified and approved: {plan.agent_name}")

        # 批准并执行
        await self.approve_plan()

    def get_progress(self) -> dict:
        """
        获取工作流进度

        Returns:
            进度信息
        """
        total = len(self._agents)
        completed = sum(1 for p in self._plans if p.executed)

        return {
            "total_stages": total,
            "completed_stages": completed,
            "current_stage": self._current_plan_index + 1,
            "current_agent": self._agents[self._current_plan_index].name if self._current_plan_index < total else None,
            "stage": self._stage.value,
            "progress_percent": (completed / total * 100) if total > 0 else 0
        }

    def get_all_plans(self) -> List[AgentPlan]:
        """获取所有计划"""
        return self._plans

    def get_project_dir(self) -> Optional[Path]:
        """获取项目目录"""
        return self._project_dir


__all__ = ["InteractiveWorkflow", "WorkflowStage", "AgentPlan"]
