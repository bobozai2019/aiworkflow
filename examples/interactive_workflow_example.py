"""
交互式工作流示例

演示如何使用InteractiveWorkflow，每个Agent执行前需要用户确认。
"""

import asyncio
from pathlib import Path

from src.agents.analyst import AnalystAgent
from src.agents.architect import ArchitectAgent
from src.agents.coder import CoderAgent
from src.agents.debugger import DebuggerAgent
from src.agents.tester import TesterAgent
from src.core.workflow_interactive import InteractiveWorkflow, WorkflowStage
from src.protocols.deepseek import DeepSeekProtocol
from src.utils.config import Config
from src.utils.logger import setup_logger


class InteractiveWorkflowDemo:
    """交互式工作流演示"""

    def __init__(self):
        self.workflow: InteractiveWorkflow = None
        self.waiting_for_approval = False

    def on_plan_ready(self, agent_name: str, stage_name: str, plan: str) -> None:
        """
        当计划准备好时的回调

        Args:
            agent_name: Agent名称
            stage_name: 阶段名称
            plan: 计划内容
        """
        print("\n" + "="*70)
        print(f"[计划] {stage_name}: {agent_name}")
        print("="*70)
        print("\n计划内容:")
        print(plan)
        print("\n" + "-"*70)
        print("请确认是否执行此计划:")
        print("  1. 输入 'y' 或 'yes' - 批准并执行")
        print("  2. 输入 'n' 或 'no' - 拒绝并重新生成")
        print("  3. 输入 'm:修改内容' - 修改计划后执行")
        print("-"*70)

        self.waiting_for_approval = True

    def on_stage_complete(self, agent_name: str, result) -> None:
        """
        当阶段完成时的回调

        Args:
            agent_name: Agent名称
            result: 执行结果
        """
        print("\n" + "="*70)
        if result.success:
            print(f"[成功] {agent_name} 执行完成")
            if result.saved_files:
                print(f"生成文件: {len(result.saved_files)}个")
        else:
            print(f"[失败] {agent_name} 执行失败")
            print(f"错误: {result.error}")
        print("="*70 + "\n")

        self.waiting_for_approval = False

    async def run(self, task: str):
        """
        运行交互式工作流

        Args:
            task: 任务描述
        """
        # 设置日志
        setup_logger(level="INFO")

        # 加载配置
        config = Config.load("config")
        protocol_config = config.get_protocol("deepseek")

        # 创建协议
        protocol = DeepSeekProtocol(
            api_key=protocol_config.get("api_key", ""),
            base_url=protocol_config.get("base_url", "https://api.deepseek.com"),
            default_model=protocol_config.get("default_model", "deepseek-chat")
        )

        # 创建工作流
        output_dir = Path("./output")
        self.workflow = InteractiveWorkflow(
            base_output_dir=output_dir,
            max_retry_per_stage=3,
            on_plan_ready=self.on_plan_ready,
            on_stage_complete=self.on_stage_complete
        )

        # 添加Agent
        self.workflow.add_agent(AnalystAgent(protocol=protocol, temperature=0.7))
        self.workflow.add_agent(ArchitectAgent(protocol=protocol, temperature=0.5))
        self.workflow.add_agent(CoderAgent(protocol=protocol, temperature=0.3))
        self.workflow.add_agent(TesterAgent(protocol=protocol, temperature=0.4))

        print("\n" + "="*70)
        print("[启动] 交互式工作流启动")
        print("="*70)
        print(f"\n任务: {task}")
        print(f"Agent流程: {' → '.join([a.name for a in self.workflow.agents])}")
        print(f"输出目录: {self.workflow.base_output_dir}")
        print("\n每个Agent执行前都会展示计划，等待您的确认。\n")

        # 启动工作流
        await self.workflow.start(task)

        # 进入交互循环
        await self.interactive_loop()

    async def interactive_loop(self):
        """交互循环"""
        while self.workflow.current_stage != WorkflowStage.COMPLETED:
            if self.workflow.current_stage == WorkflowStage.ERROR:
                print("\n[错误] 工作流执行出错，已停止。")
                break

            if self.waiting_for_approval:
                # 等待用户输入
                user_input = input("\n请输入您的决定: ").strip().lower()

                if user_input in ['y', 'yes', '是', '确认']:
                    # 批准计划
                    print("\n[批准] 计划已批准，开始执行...\n")
                    await self.workflow.approve_plan()

                elif user_input in ['n', 'no', '否', '拒绝']:
                    # 拒绝计划
                    reason = input("请输入拒绝原因（可选）: ").strip()
                    print("\n[拒绝] 计划已拒绝，重新生成...\n")
                    await self.workflow.reject_plan(reason if reason else None)

                elif user_input.startswith('m:') or user_input.startswith('修改:'):
                    # 修改计划
                    modification = user_input.split(':', 1)[1].strip()
                    print(f"\n[修改] 计划已修改: {modification}")
                    print("开始执行...\n")
                    await self.workflow.approve_plan(modifications=modification)

                else:
                    print("[错误] 无效输入，请重新输入。")

            else:
                # 等待计划生成或执行完成
                await asyncio.sleep(0.5)

        # 工作流完成
        if self.workflow.current_stage == WorkflowStage.COMPLETED:
            print("\n" + "="*70)
            print("[完成] 所有阶段已完成！")
            print("="*70)

            # 显示进度
            progress = self.workflow.get_progress()
            print(f"\n完成进度: {progress['completed_stages']}/{progress['total_stages']}")

            # 显示项目目录
            project_dir = self.workflow.get_project_dir()
            if project_dir:
                print(f"项目目录: {project_dir}")

            # 显示所有计划和结果
            print("\n执行摘要:")
            for plan in self.workflow.get_all_plans():
                status = "[成功]" if plan.result and plan.result.success else "[失败]"
                print(f"  {status} {plan.stage_name}: {plan.agent_name}")


async def main():
    """主函数"""
    demo = InteractiveWorkflowDemo()

    # 定义任务
    task = """
实现一个简单的待办事项管理系统，包含以下功能：
1. 添加待办事项
2. 标记完成
3. 删除待办事项
4. 列出所有待办事项

要求：
- 使用Python实现
- 数据存储在内存中（使用列表）
- 提供命令行交互界面
"""

    await demo.run(task)


if __name__ == "__main__":
    asyncio.run(main())
