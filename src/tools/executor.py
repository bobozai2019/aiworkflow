"""
代码执行工具模块

提供代码执行和测试运行能力。
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger

from src.tools.base import BaseTool, ToolParameter, ToolResult


class CodeExecutorTool(BaseTool):
    """
    代码执行工具

    在隔离环境中执行Python代码，捕获输出和错误。
    """

    name = "code_execute"
    description = "在隔离环境中执行Python代码并返回结果（stdout/stderr/exit_code）"
    requires_permission = True
    parameters = [
        ToolParameter(
            name="file_path",
            type="string",
            description="要执行的Python文件路径（相对于项目根目录）",
            required=True
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="执行超时时间（秒），默认30秒",
            required=False,
            default=30
        ),
        ToolParameter(
            name="args",
            type="string",
            description="命令行参数（可选）",
            required=False,
            default=""
        )
    ]

    def execute(
        self,
        file_path: str,
        timeout: int = 30,
        args: str = ""
    ) -> ToolResult:
        """
        执行Python代码

        Args:
            file_path: Python文件路径
            timeout: 超时时间（秒）
            args: 命令行参数

        Returns:
            执行结果
        """
        from src.core.permission import get_permission_manager
        from src.tools.base import ToolRegistry

        agent_name = ToolRegistry.get_current_agent()
        if not agent_name:
            return ToolResult(
                success=False,
                content="",
                error="权限错误: 未设置当前Agent"
            )

        pm = get_permission_manager()
        path = Path(file_path)

        if not path.is_absolute() and pm._project_root:
            path = pm._project_root / file_path

        if not pm.check_read_permission(agent_name, path):
            return ToolResult(
                success=False,
                content="",
                error=f"权限拒绝: {agent_name} 没有读取 {file_path} 的权限"
            )

        if not path.exists():
            return ToolResult(
                success=False,
                content="",
                error=f"文件不存在: {file_path}"
            )

        if not path.suffix == ".py":
            return ToolResult(
                success=False,
                content="",
                error=f"只支持Python文件，当前文件: {path.suffix}"
            )

        try:
            start_time = time.time()

            cmd = [sys.executable, str(path)]
            if args:
                cmd.extend(args.split())

            logger.info(f"[CodeExecutor] 执行命令: {' '.join(cmd)}")
            logger.info(f"[CodeExecutor] 工作目录: {path.parent}")

            result = subprocess.run(
                cmd,
                cwd=str(path.parent),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy()
            )

            duration = time.time() - start_time

            output_parts = []
            if result.stdout:
                output_parts.append(f"=== 标准输出 ===\n{result.stdout}")
            if result.stderr:
                output_parts.append(f"=== 标准错误 ===\n{result.stderr}")

            output = "\n\n".join(output_parts) if output_parts else "(无输出)"

            success = result.returncode == 0

            metadata = {
                "exit_code": result.returncode,
                "duration": duration,
                "file_path": str(path),
                "has_stdout": bool(result.stdout),
                "has_stderr": bool(result.stderr)
            }

            if success:
                logger.info(f"[CodeExecutor] ✅ 执行成功 (耗时: {duration:.2f}s)")
                return ToolResult(
                    success=True,
                    content=f"执行成功 (退出码: 0)\n\n{output}",
                    metadata=metadata
                )
            else:
                logger.warning(f"[CodeExecutor] ❌ 执行失败 (退出码: {result.returncode})")
                return ToolResult(
                    success=False,
                    content=output,
                    error=f"执行失败 (退出码: {result.returncode})",
                    metadata=metadata
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                content="",
                error=f"执行超时 (超过 {timeout} 秒)",
                metadata={"timeout": timeout}
            )
        except Exception as e:
            logger.error(f"[CodeExecutor] 执行异常: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"执行异常: {str(e)}"
            )


class TestRunnerTool(BaseTool):
    """
    测试运行工具

    执行pytest测试并返回测试报告。
    """

    name = "test_run"
    description = "执行pytest测试用例并返回测试报告（通过/失败/错误详情）"
    requires_permission = True
    parameters = [
        ToolParameter(
            name="test_path",
            type="string",
            description="测试文件或目录路径（相对于项目根目录）",
            required=True
        ),
        ToolParameter(
            name="verbose",
            type="boolean",
            description="是否显示详细输出",
            required=False,
            default=True
        ),
        ToolParameter(
            name="timeout",
            type="integer",
            description="执行超时时间（秒），默认60秒",
            required=False,
            default=60
        )
    ]

    def execute(
        self,
        test_path: str,
        verbose: bool = True,
        timeout: int = 60
    ) -> ToolResult:
        """
        执行测试

        Args:
            test_path: 测试路径
            verbose: 是否详细输出
            timeout: 超时时间

        Returns:
            测试结果
        """
        from src.core.permission import get_permission_manager
        from src.tools.base import ToolRegistry

        agent_name = ToolRegistry.get_current_agent()
        if not agent_name:
            return ToolResult(
                success=False,
                content="",
                error="权限错误: 未设置当前Agent"
            )

        pm = get_permission_manager()
        path = Path(test_path)

        if not path.is_absolute() and pm._project_root:
            path = pm._project_root / test_path

        if not pm.check_read_permission(agent_name, path):
            return ToolResult(
                success=False,
                content="",
                error=f"权限拒绝: {agent_name} 没有读取 {test_path} 的权限"
            )

        if not path.exists():
            return ToolResult(
                success=False,
                content="",
                error=f"测试路径不存在: {test_path}"
            )

        try:
            start_time = time.time()

            cmd = [
                sys.executable, "-m", "pytest",
                str(path),
                "-v" if verbose else "",
                "--tb=short",
                "--color=no"
            ]
            cmd = [c for c in cmd if c]

            logger.info(f"[TestRunner] 执行命令: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                cwd=str(pm._project_root) if pm._project_root else str(path.parent),
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy()
            )

            duration = time.time() - start_time

            output = result.stdout + "\n" + result.stderr

            passed = result.returncode == 0

            test_summary = self._parse_test_summary(output)

            metadata = {
                "exit_code": result.returncode,
                "duration": duration,
                "test_path": str(path),
                **test_summary
            }

            if passed:
                logger.info(f"[TestRunner] ✅ 测试通过 (耗时: {duration:.2f}s)")
                return ToolResult(
                    success=True,
                    content=f"测试通过\n\n{output}",
                    metadata=metadata
                )
            else:
                logger.warning(f"[TestRunner] ❌ 测试失败")
                return ToolResult(
                    success=False,
                    content=output,
                    error="测试失败，存在失败或错误的用例",
                    metadata=metadata
                )

        except subprocess.TimeoutExpired:
            return ToolResult(
                success=False,
                content="",
                error=f"测试超时 (超过 {timeout} 秒)",
                metadata={"timeout": timeout}
            )
        except FileNotFoundError:
            return ToolResult(
                success=False,
                content="",
                error="pytest未安装，请先安装: pip install pytest"
            )
        except Exception as e:
            logger.error(f"[TestRunner] 执行异常: {e}")
            return ToolResult(
                success=False,
                content="",
                error=f"执行异常: {str(e)}"
            )

    def _parse_test_summary(self, output: str) -> Dict[str, int]:
        """
        解析测试摘要

        Args:
            output: pytest输出

        Returns:
            测试统计信息
        """
        import re

        summary = {
            "passed": 0,
            "failed": 0,
            "errors": 0,
            "skipped": 0,
            "total": 0
        }

        pattern = r"(\d+) passed|(\d+) failed|(\d+) error|(\d+) skipped"
        matches = re.findall(pattern, output)

        for match in matches:
            if match[0]:
                summary["passed"] = int(match[0])
            if match[1]:
                summary["failed"] = int(match[1])
            if match[2]:
                summary["errors"] = int(match[2])
            if match[3]:
                summary["skipped"] = int(match[3])

        summary["total"] = sum([
            summary["passed"],
            summary["failed"],
            summary["errors"],
            summary["skipped"]
        ])

        return summary


def register_executor_tools() -> None:
    """注册执行器工具"""
    from src.tools.base import ToolRegistry

    ToolRegistry.register(CodeExecutorTool())
    ToolRegistry.register(TestRunnerTool())
    logger.info("[ExecutorTools] Registered code execution tools")


__all__ = [
    "CodeExecutorTool",
    "TestRunnerTool",
    "register_executor_tools",
]
