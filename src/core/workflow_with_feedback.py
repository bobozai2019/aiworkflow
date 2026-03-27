"""
带反馈循环的工作流引擎

支持代码执行验证和错误修复的迭代流程。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional

from loguru import logger

from src.agents.base_agent import BaseAgent
from src.core.context import Context, TaskResult


class WorkflowWithFeedback:
    """
    带反馈循环的工作流引擎

    支持：
    1. 代码执行验证
    2. 测试执行验证
    3. 失败自动重试
    4. 调试员介入修复
    """

    def __init__(
        self,
        base_output_dir: Path = None,
        use_existing_project: bool = False,
        max_retry_per_stage: int = 3
    ) -> None:
        self.agents: List[BaseAgent] = []
        self.on_progress: Optional[Callable[[str, str, float], None]] = None
        self.base_output_dir = base_output_dir or Path("./output")
        self.use_existing_project = use_existing_project
        self.max_retry_per_stage = max_retry_per_stage
        self._initial_results: dict = {}

        # 执行统计
        self._execution_stats = {
            "code_executions": 0,
            "test_runs": 0,
            "debug_attempts": 0,
            "total_retries": 0
        }

    def set_initial_context(self, results: dict) -> None:
        """设置初始上下文结果"""
        self._initial_results = results

    def add_agent(self, agent: BaseAgent) -> "WorkflowWithFeedback":
        """添加Agent"""
        self.agents.append(agent)
        return self

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
        """创建项目目录结构"""
        if self.use_existing_project and self.base_output_dir:
            logger.info(f"[WorkflowFeedback] Using existing project: {self.base_output_dir}")
            project_dir = self.base_output_dir
        else:
            project_name = self._generate_project_name(task, task_id)
            project_dir = self.base_output_dir / project_name
            project_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"[WorkflowFeedback] Created project: {project_dir}")

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
        logger.info(f"[WorkflowFeedback] Permission manager initialized")

    async def run(self, task: str, task_id: str = None) -> TaskResult:
        """
        执行工作流（带反馈循环）

        流程：
        1. 需求分析 → 架构设计 → 代码开发
        2. 执行代码验证
        3. 如果失败 → 调试修复 → 重新执行（最多3次）
        4. 测试用例开发
        5. 执行测试验证
        6. 如果失败 → 调试修复 → 重新测试（最多3次）
        """
        task_id = task_id or str(uuid.uuid4())[:8]
        context = Context(task_id=task_id)

        # 设置初始上下文
        for agent_name, result in self._initial_results.items():
            context.set_result(agent_name, result)

        project_dir = self._create_project_dir(task, task_id)
        context.set("project_dir", str(project_dir))

        self._initialize_permission_manager(project_dir)

        # 注册执行工具
        from src.tools.executor import register_executor_tools
        register_executor_tools()

        # 设置Agent输出目录
        for agent in self.agents:
            agent.set_output_dir(project_dir)
            agent.update_prompt_output_dir(project_dir)

        logger.info(f"[WorkflowFeedback] Starting task {task_id}")
        logger.info(f"[WorkflowFeedback] Project: {project_dir}")
        logger.info(f"[WorkflowFeedback] Max retry per stage: {self.max_retry_per_stage}")

        # 阶段1: 需求分析 + 架构设计 + 代码开发
        result = await self._run_development_phase(task, context)
        if not result.success:
            return result

        # 阶段2: 代码执行验证（带重试）
        result = await self._run_code_verification_phase(context, project_dir)
        if not result.success:
            return result

        # 阶段3: 测试开发 + 测试验证（带重试）
        result = await self._run_testing_phase(task, context, project_dir)
        if not result.success:
            return result

        # 生成最终报告
        final_content = self._generate_final_report(context)

        logger.info(f"[WorkflowFeedback] ✅ Task {task_id} completed successfully")
        logger.info(f"[WorkflowFeedback] Stats: {self._execution_stats}")

        return TaskResult(
            success=True,
            content=final_content,
            agent_id="workflow_feedback",
            agent_name="WorkflowWithFeedback",
            saved_files=[str(project_dir)]
        )

    async def _run_development_phase(
        self,
        task: str,
        context: Context
    ) -> TaskResult:
        """
        运行开发阶段（需求分析 + 架构设计 + 代码开发）
        """
        logger.info(f"[WorkflowFeedback] {'='*50}")
        logger.info(f"[WorkflowFeedback] 阶段1: 开发阶段")
        logger.info(f"[WorkflowFeedback] {'='*50}")

        # 找到需求分析师、架构师、程序员
        dev_agents = []
        for agent in self.agents:
            if agent.name in ["需求分析师", "系统架构师", "代码开发者"]:
                dev_agents.append(agent)

        if not dev_agents:
            return TaskResult(
                success=False,
                content="",
                error="未找到开发阶段所需的Agent"
            )

        # 顺序执行开发Agent
        for i, agent in enumerate(dev_agents):
            progress = (i + 1) / len(dev_agents) * 33  # 开发阶段占33%

            logger.info(f"[WorkflowFeedback] 执行: {agent.name}")

            if self.on_progress:
                self.on_progress(agent.name, "start", progress)

            result = await agent.execute(task, context)
            context.set_result(agent.name, result)

            if not result.success:
                logger.error(f"[WorkflowFeedback] {agent.name} 失败: {result.error}")
                if self.on_progress:
                    self.on_progress(agent.name, "failed", progress)
                return result

            logger.info(f"[WorkflowFeedback] ✅ {agent.name} 完成")
            if self.on_progress:
                self.on_progress(agent.name, "complete", progress)

        return TaskResult(success=True, content="开发阶段完成")

    async def _run_code_verification_phase(
        self,
        context: Context,
        project_dir: Path
    ) -> TaskResult:
        """
        运行代码验证阶段（执行代码 + 调试修复）
        """
        logger.info(f"[WorkflowFeedback] {'='*50}")
        logger.info(f"[WorkflowFeedback] 阶段2: 代码验证")
        logger.info(f"[WorkflowFeedback] {'='*50}")

        code_dir = project_dir / "code"
        python_files = list(code_dir.glob("*.py"))

        if not python_files:
            logger.warning("[WorkflowFeedback] 未找到Python文件，跳过代码验证")
            return TaskResult(success=True, content="无代码需要验证")

        logger.info(f"[WorkflowFeedback] 找到 {len(python_files)} 个Python文件")

        # 尝试执行每个Python文件
        for py_file in python_files:
            logger.info(f"[WorkflowFeedback] 验证文件: {py_file.name}")

            result = await self._verify_and_fix_code(
                py_file,
                context,
                project_dir
            )

            if not result.success:
                return result

        logger.info(f"[WorkflowFeedback] ✅ 代码验证完成")
        return TaskResult(success=True, content="代码验证通过")

    async def _verify_and_fix_code(
        self,
        code_file: Path,
        context: Context,
        project_dir: Path
    ) -> TaskResult:
        """
        验证并修复单个代码文件
        """
        from src.tools.base import ToolRegistry

        relative_path = code_file.relative_to(project_dir)

        for attempt in range(self.max_retry_per_stage):
            logger.info(f"[WorkflowFeedback] 执行代码 (尝试 {attempt + 1}/{self.max_retry_per_stage})")

            self._execution_stats["code_executions"] += 1

            # 执行代码
            exec_result = ToolRegistry.execute(
                "code_execute",
                file_path=str(relative_path),
                timeout=30
            )

            if exec_result.success:
                logger.info(f"[WorkflowFeedback] ✅ {code_file.name} 执行成功")
                return TaskResult(success=True, content=exec_result.content)

            # 执行失败，需要调试
            logger.warning(f"[WorkflowFeedback] ❌ {code_file.name} 执行失败")
            logger.warning(f"[WorkflowFeedback] 错误: {exec_result.error}")

            if attempt < self.max_retry_per_stage - 1:
                # 调用调试员修复
                fix_result = await self._call_debugger(
                    code_file,
                    exec_result,
                    context,
                    project_dir
                )

                if not fix_result.success:
                    logger.error(f"[WorkflowFeedback] 调试失败: {fix_result.error}")
                    continue

                logger.info(f"[WorkflowFeedback] 🔧 代码已修复，重新验证")
                self._execution_stats["total_retries"] += 1
            else:
                # 达到最大重试次数
                return TaskResult(
                    success=False,
                    content=exec_result.content,
                    error=f"代码验证失败（已重试{self.max_retry_per_stage}次）: {exec_result.error}"
                )

        return TaskResult(success=False, error="代码验证失败")

    async def _call_debugger(
        self,
        code_file: Path,
        exec_result: Any,
        context: Context,
        project_dir: Path
    ) -> TaskResult:
        """
        调用调试员修复代码
        """
        from src.agents.debugger import DebuggerAgent

        logger.info(f"[WorkflowFeedback] 🔍 调用调试员分析错误")

        self._execution_stats["debug_attempts"] += 1

        # 创建调试员Agent
        debugger = None
        for agent in self.agents:
            if agent.name == "调试员":
                debugger = agent
                break

        if not debugger:
            # 动态创建调试员
            from src.protocols.deepseek import DeepSeekProtocol
            from src.utils.config import Config

            config = Config.load("config")
            protocol_config = config.get_protocol("deepseek")

            protocol = DeepSeekProtocol(
                api_key=protocol_config.get("api_key", ""),
                base_url=protocol_config.get("base_url", ""),
                default_model=protocol_config.get("default_model", "deepseek-chat")
            )

            debugger = DebuggerAgent(
                protocol=protocol,
                temperature=0.3,
                output_dir=project_dir
            )
            debugger.set_work_dir(project_dir)

        # 构建调试任务
        error_info = f"""
代码文件: {code_file.name}
执行错误: {exec_result.error}

错误详情:
{exec_result.content}

请分析错误原因并修复代码。
"""

        # 执行调试
        debug_result = await debugger.execute(error_info, context)

        if debug_result.success:
            logger.info(f"[WorkflowFeedback] ✅ 调试完成")
        else:
            logger.error(f"[WorkflowFeedback] ❌ 调试失败: {debug_result.error}")

        return debug_result

    async def _run_testing_phase(
        self,
        task: str,
        context: Context,
        project_dir: Path
    ) -> TaskResult:
        """
        运行测试阶段（测试开发 + 测试验证）
        """
        logger.info(f"[WorkflowFeedback] {'='*50}")
        logger.info(f"[WorkflowFeedback] 阶段3: 测试阶段")
        logger.info(f"[WorkflowFeedback] {'='*50}")

        # 找到测试员
        tester = None
        for agent in self.agents:
            if agent.name == "测试员":
                tester = agent
                break

        if not tester:
            logger.warning("[WorkflowFeedback] 未找到测试员，跳过测试阶段")
            return TaskResult(success=True, content="无测试员")

        # 执行测试员生成测试用例
        logger.info(f"[WorkflowFeedback] 执行: {tester.name}")

        if self.on_progress:
            self.on_progress(tester.name, "start", 66)

        test_result = await tester.execute(task, context)
        context.set_result(tester.name, test_result)

        if not test_result.success:
            logger.error(f"[WorkflowFeedback] 测试员失败: {test_result.error}")
            if self.on_progress:
                self.on_progress(tester.name, "failed", 66)
            return test_result

        logger.info(f"[WorkflowFeedback] ✅ 测试用例生成完成")
        if self.on_progress:
            self.on_progress(tester.name, "complete", 66)

        # 执行测试验证
        tests_dir = project_dir / "tests"
        test_files = list(tests_dir.glob("test_*.py"))

        if not test_files:
            logger.warning("[WorkflowFeedback] 未找到测试文件")
            return TaskResult(success=True, content="无测试文件")

        logger.info(f"[WorkflowFeedback] 找到 {len(test_files)} 个测试文件")

        # 执行测试验证（带重试）
        result = await self._verify_and_fix_tests(
            tests_dir,
            context,
            project_dir
        )

        return result

    async def _verify_and_fix_tests(
        self,
        tests_dir: Path,
        context: Context,
        project_dir: Path
    ) -> TaskResult:
        """
        验证并修复测试
        """
        from src.tools.base import ToolRegistry

        relative_path = tests_dir.relative_to(project_dir)

        for attempt in range(self.max_retry_per_stage):
            logger.info(f"[WorkflowFeedback] 执行测试 (尝试 {attempt + 1}/{self.max_retry_per_stage})")

            self._execution_stats["test_runs"] += 1

            # 执行测试
            test_result = ToolRegistry.execute(
                "test_run",
                test_path=str(relative_path),
                verbose=True,
                timeout=60
            )

            if test_result.success:
                logger.info(f"[WorkflowFeedback] ✅ 测试通过")
                return TaskResult(success=True, content=test_result.content)

            # 测试失败
            logger.warning(f"[WorkflowFeedback] ❌ 测试失败")
            logger.warning(f"[WorkflowFeedback] 错误: {test_result.error}")

            if attempt < self.max_retry_per_stage - 1:
                # 调用调试员修复
                fix_result = await self._call_debugger_for_tests(
                    tests_dir,
                    test_result,
                    context,
                    project_dir
                )

                if not fix_result.success:
                    logger.error(f"[WorkflowFeedback] 调试失败: {fix_result.error}")
                    continue

                logger.info(f"[WorkflowFeedback] 🔧 代码已修复，重新测试")
                self._execution_stats["total_retries"] += 1
            else:
                # 达到最大重试次数
                return TaskResult(
                    success=False,
                    content=test_result.content,
                    error=f"测试失败（已重试{self.max_retry_per_stage}次）: {test_result.error}"
                )

        return TaskResult(success=False, error="测试验证失败")

    async def _call_debugger_for_tests(
        self,
        tests_dir: Path,
        test_result: Any,
        context: Context,
        project_dir: Path
    ) -> TaskResult:
        """
        调用调试员修复测试失败
        """
        logger.info(f"[WorkflowFeedback] 🔍 调用调试员分析测试失败")

        # 构建调试任务
        error_info = f"""
测试目录: {tests_dir.name}
测试失败: {test_result.error}

测试输出:
{test_result.content}

请分析测试失败原因并修复代码（注意：通常是业务代码有问题，而非测试用例有问题）。
"""

        # 调用调试员
        return await self._call_debugger(
            tests_dir,
            test_result,
            context,
            project_dir
        )

    def _generate_final_report(self, context: Context) -> str:
        """生成最终报告"""
        report_parts = []

        report_parts.append("# 项目开发完成报告\n")

        # 执行统计
        report_parts.append("## 执行统计")
        report_parts.append(f"- 代码执行次数: {self._execution_stats['code_executions']}")
        report_parts.append(f"- 测试运行次数: {self._execution_stats['test_runs']}")
        report_parts.append(f"- 调试尝试次数: {self._execution_stats['debug_attempts']}")
        report_parts.append(f"- 总重试次数: {self._execution_stats['total_retries']}\n")

        # Agent输出摘要
        report_parts.append("## Agent工作摘要")
        for agent_name, result in context.results.items():
            status = "✅ 成功" if result.success else "❌ 失败"
            report_parts.append(f"- {agent_name}: {status}")
            if result.saved_files:
                report_parts.append(f"  文件: {len(result.saved_files)}个")

        return "\n".join(report_parts)

    def get_agent_names(self) -> List[str]:
        """获取所有Agent名称"""
        return [agent.name for agent in self.agents]


__all__ = ["WorkflowWithFeedback"]
