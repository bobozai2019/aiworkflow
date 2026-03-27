"""
测试：代码执行和反馈循环

测试WorkflowWithFeedback的完整流程。
"""

import asyncio
import sys
from pathlib import Path

import pytest

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.architect import ArchitectAgent
from src.agents.coder import CoderAgent
from src.agents.debugger import DebuggerAgent
from src.agents.tester import TesterAgent
from src.core.workflow_with_feedback import WorkflowWithFeedback
from src.protocols.deepseek import DeepSeekProtocol
from src.utils.config import Config


@pytest.fixture
def protocol():
    """创建测试用的协议"""
    config = Config.load("config")
    protocol_config = config.get_protocol("deepseek")

    return DeepSeekProtocol(
        api_key=protocol_config.get("api_key", ""),
        base_url=protocol_config.get("base_url", "https://api.deepseek.com"),
        default_model=protocol_config.get("default_model", "deepseek-chat")
    )


@pytest.fixture
def output_dir(tmp_path):
    """创建临时输出目录"""
    return tmp_path / "test_output"


@pytest.mark.asyncio
async def test_workflow_with_feedback_simple(protocol, output_dir):
    """
    测试带反馈循环的工作流 - 简单场景

    任务：实现一个简单的加法函数
    预期：代码能够正常执行，测试通过
    """
    workflow = WorkflowWithFeedback(
        base_output_dir=output_dir,
        max_retry_per_stage=2
    )

    # 添加Agent
    workflow.add_agent(ArchitectAgent(protocol=protocol, temperature=0.5))
    workflow.add_agent(CoderAgent(protocol=protocol, temperature=0.3))
    workflow.add_agent(TesterAgent(protocol=protocol, temperature=0.4))

    # 执行任务
    task = "实现一个add函数，接收两个数字参数，返回它们的和"

    result = await workflow.run(task)

    # 验证结果
    assert result.success, f"工作流执行失败: {result.error}"
    assert len(result.saved_files) > 0, "未生成任何文件"

    # 验证项目结构
    project_dir = Path(result.saved_files[0])
    assert (project_dir / "code").exists(), "代码目录不存在"
    assert (project_dir / "tests").exists(), "测试目录不存在"

    # 验证生成的文件
    code_files = list((project_dir / "code").glob("*.py"))
    test_files = list((project_dir / "tests").glob("test_*.py"))

    assert len(code_files) > 0, "未生成代码文件"
    assert len(test_files) > 0, "未生成测试文件"

    print(f"\n✅ 测试通过")
    print(f"项目目录: {project_dir}")
    print(f"代码文件: {[f.name for f in code_files]}")
    print(f"测试文件: {[f.name for f in test_files]}")


@pytest.mark.asyncio
async def test_workflow_with_feedback_with_error(protocol, output_dir):
    """
    测试带反馈循环的工作流 - 错误修复场景

    任务：实现一个可能有错误的函数
    预期：调试员能够发现并修复错误
    """
    workflow = WorkflowWithFeedback(
        base_output_dir=output_dir,
        max_retry_per_stage=3
    )

    # 添加Agent（包括调试员）
    workflow.add_agent(ArchitectAgent(protocol=protocol, temperature=0.5))
    workflow.add_agent(CoderAgent(protocol=protocol, temperature=0.3))
    workflow.add_agent(DebuggerAgent(protocol=protocol, temperature=0.3))
    workflow.add_agent(TesterAgent(protocol=protocol, temperature=0.4))

    # 执行任务
    task = "实现一个divide函数，接收两个数字参数，返回第一个数除以第二个数的结果。需要处理除零错误。"

    result = await workflow.run(task)

    # 验证结果
    assert result.success, f"工作流执行失败: {result.error}"

    # 验证执行统计
    stats = workflow._execution_stats
    print(f"\n执行统计:")
    print(f"  代码执行次数: {stats['code_executions']}")
    print(f"  测试运行次数: {stats['test_runs']}")
    print(f"  调试尝试次数: {stats['debug_attempts']}")
    print(f"  总重试次数: {stats['total_retries']}")

    # 如果有重试，说明调试员介入了
    if stats['debug_attempts'] > 0:
        print(f"\n✅ 调试员成功介入并修复了错误")


@pytest.mark.asyncio
async def test_code_executor_tool():
    """
    测试代码执行工具
    """
    from src.tools.executor import CodeExecutorTool, register_executor_tools
    from src.tools.base import ToolRegistry
    from src.core.permission import get_permission_manager

    # 注册工具
    register_executor_tools()

    # 创建测试项目
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        code_dir = project_dir / "code"
        code_dir.mkdir()

        # 创建测试代码文件
        test_code = """
def hello():
    print("Hello, World!")
    return "success"

if __name__ == "__main__":
    result = hello()
    print(f"Result: {result}")
"""
        test_file = code_dir / "hello.py"
        test_file.write_text(test_code)

        # 初始化权限管理器
        pm = get_permission_manager()
        pm.initialize(project_dir)

        # 执行代码
        ToolRegistry.set_current_agent("调试员")
        result = ToolRegistry.execute(
            "code_execute",
            file_path="code/hello.py",
            timeout=10
        )

        # 验证结果
        assert result.success, f"代码执行失败: {result.error}"
        assert "Hello, World!" in result.content, "输出不正确"
        assert "success" in result.content, "返回值不正确"

        print(f"\n✅ 代码执行工具测试通过")
        print(f"输出:\n{result.content}")


@pytest.mark.asyncio
async def test_test_runner_tool():
    """
    测试测试运行工具
    """
    from src.tools.executor import register_executor_tools
    from src.tools.base import ToolRegistry
    from src.core.permission import get_permission_manager

    # 注册工具
    register_executor_tools()

    # 创建测试项目
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        project_dir = Path(tmpdir)
        tests_dir = project_dir / "tests"
        tests_dir.mkdir()

        # 创建测试文件
        test_code = """
import pytest

def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 5 - 3 == 2
"""
        test_file = tests_dir / "test_math.py"
        test_file.write_text(test_code)

        # 初始化权限管理器
        pm = get_permission_manager()
        pm.initialize(project_dir)

        # 执行测试
        ToolRegistry.set_current_agent("测试员")
        result = ToolRegistry.execute(
            "test_run",
            test_path="tests",
            verbose=True,
            timeout=30
        )

        # 验证结果
        assert result.success, f"测试执行失败: {result.error}"
        assert result.metadata.get("passed", 0) == 2, "测试通过数量不正确"

        print(f"\n✅ 测试运行工具测试通过")
        print(f"测试统计: {result.metadata}")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
