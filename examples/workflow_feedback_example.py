"""
示例：使用带反馈循环的工作流

演示如何使用WorkflowWithFeedback实现完整的开发流程。
"""

import asyncio
from pathlib import Path

from src.agents.architect import ArchitectAgent
from src.agents.coder import CoderAgent
from src.agents.debugger import DebuggerAgent
from src.agents.tester import TesterAgent
from src.core.workflow_with_feedback import WorkflowWithFeedback
from src.protocols.deepseek import DeepSeekProtocol
from src.utils.config import Config
from src.utils.logger import setup_logger


def on_progress(agent_name: str, status: str, progress: float) -> None:
    """进度回调"""
    if status == "start":
        print(f"\n{'='*50}")
        print(f"[{agent_name}] 开始工作...")
        print(f"{'='*50}\n")
    elif status == "complete":
        print(f"\n[{agent_name}] 完成! 进度: {progress:.0f}%")
    elif status == "failed":
        print(f"\n[{agent_name}] 失败!")


async def main():
    """主函数"""
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
    workflow = WorkflowWithFeedback(
        base_output_dir=output_dir,
        max_retry_per_stage=3
    )

    # 添加Agent
    workflow.add_agent(ArchitectAgent(protocol=protocol, temperature=0.5))
    workflow.add_agent(CoderAgent(protocol=protocol, temperature=0.3))
    workflow.add_agent(DebuggerAgent(protocol=protocol, temperature=0.3))
    workflow.add_agent(TesterAgent(protocol=protocol, temperature=0.4))

    # 设置进度回调
    workflow.on_progress = on_progress

    # 定义任务
    task = """
实现一个简单的计算器模块，包含以下功能：
1. 加法 add(a, b)
2. 减法 subtract(a, b)
3. 乘法 multiply(a, b)
4. 除法 divide(a, b) - 需要处理除零错误

要求：
- 所有函数都要有类型注解
- 除法函数要抛出合适的异常
- 代码要有注释
"""

    print(f"\n任务: {task}")
    print(f"Agent: {' -> '.join(workflow.get_agent_names())}")
    print(f"输出目录: {workflow.base_output_dir}")
    print(f"最大重试次数: {workflow.max_retry_per_stage}")
    print()

    # 执行工作流
    result = await workflow.run(task)

    # 输出结果
    print("\n\n" + "="*50)
    if result.success:
        print("✅ 任务完成!")
        print(f"\n{result.content}")
        if result.saved_files:
            print(f"\n项目目录: {result.saved_files[0]}")
    else:
        print(f"❌ 任务失败: {result.error}")
    print("="*50)


if __name__ == "__main__":
    asyncio.run(main())
