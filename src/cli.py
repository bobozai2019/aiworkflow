"""
命令行入口

提供命令行交互界面。
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Optional

from loguru import logger

from src.agents.analyst import AnalystAgent
from src.agents.coder import CoderAgent
from src.core.workflow import Workflow
from src.protocols.deepseek import DeepSeekProtocol
from src.utils.config import Config
from src.utils.logger import setup_logger


def create_workflow(config: Config) -> Workflow:
    """
    创建工作流
    
    Args:
        config: 配置对象
        
    Returns:
        工作流实例
    """
    protocol_config = config.get_protocol("deepseek")
    if not protocol_config:
        raise ValueError("DeepSeek protocol not configured")
    
    protocol = DeepSeekProtocol(
        api_key=protocol_config.get("api_key", ""),
        base_url=protocol_config.get("base_url", "https://api.deepseek.com"),
        default_model=protocol_config.get("default_model", "deepseek-chat")
    )
    
    output_dir = config.output_dir
    
    analyst_config = config.get_agent_with_replaced_prompt("analyst") or {}
    coder_config = config.get_agent_with_replaced_prompt("coder") or {}
    
    analyst = AnalystAgent(
        protocol=protocol,
        system_prompt=analyst_config.get("system_prompt", ""),
        model=analyst_config.get("model"),
        temperature=analyst_config.get("temperature", 0.7)
    )
    
    coder = CoderAgent(
        protocol=protocol,
        system_prompt=coder_config.get("system_prompt", ""),
        model=coder_config.get("model"),
        temperature=coder_config.get("temperature", 0.3)
    )
    
    workflow = Workflow(base_output_dir=output_dir)
    workflow.add_agent(analyst)
    workflow.add_agent(coder)
    
    return workflow


def on_progress(agent_name: str, status: str, progress: float) -> None:
    """
    进度回调
    
    Args:
        agent_name: Agent名称
        status: 状态
        progress: 进度
    """
    if status == "start":
        print(f"\n{'='*50}")
        print(f"[{agent_name}] 开始工作...")
        print(f"{'='*50}\n")
    elif status == "complete":
        print(f"\n[{agent_name}] 完成! 进度: {progress:.0f}%")


def on_chunk(chunk: str) -> None:
    """
    流式输出回调
    
    Args:
        chunk: 内容块
    """
    print(chunk, end="", flush=True)


def on_reasoning(chunk: str) -> None:
    """
    思考过程输出回调
    
    Args:
        chunk: 思考内容块
    """
    print(f"\033[90m{chunk}\033[0m", end="", flush=True)


async def run_task(task: str, config_dir: str = "config") -> None:
    """
    执行任务
    
    Args:
        task: 任务描述
        config_dir: 配置目录
    """
    config = Config.load(config_dir)
    
    setup_logger(
        level=config.get("logging.level", "INFO"),
        log_file=config.get("logging.file"),
        log_format=config.get("logging.format", "{time} | {level} | {message}")
    )
    
    workflow = create_workflow(config)
    
    for agent in workflow.agents:
        agent.on_chunk(on_chunk)
        agent.on_reasoning(on_reasoning)
    
    workflow.on_progress = on_progress
    
    print(f"\n任务: {task}")
    print(f"Agent: {' -> '.join(workflow.get_agent_names())}")
    print(f"输出目录: {workflow.base_output_dir}")
    print()
    
    result = await workflow.run(task)
    
    print("\n\n" + "="*50)
    if result.success:
        print("任务完成!")
        if result.saved_files:
            print(f"项目目录: {result.saved_files[0]}")
    else:
        print(f"任务失败: {result.error}")
    print("="*50)


def main() -> None:
    """主入口"""
    parser = argparse.ArgumentParser(
        description="Multi-Agent System - 多Agent协作系统"
    )
    parser.add_argument(
        "task",
        nargs="?",
        help="任务描述"
    )
    parser.add_argument(
        "-c", "--config",
        default="config",
        help="配置目录路径"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="交互模式"
    )
    parser.add_argument(
        "-g", "--gui",
        action="store_true",
        help="启动图形界面"
    )
    
    args = parser.parse_args()
    
    if args.gui:
        from src.ui import run_gui
        run_gui()
        return
    
    args.interactive = True
    if args.interactive:
        print("Multi-Agent System 交互模式")
        print("输入任务描述，按Enter执行。输入 'quit' 退出。")
        print()
        
        while True:
            try:
                task = input("请输入任务: ").strip()
                if task.lower() == "quit":
                    break
                if task:
                    asyncio.run(run_task(task, args.config))
            except KeyboardInterrupt:
                print("\n再见!")
                break
    elif args.task:
        asyncio.run(run_task(args.task, args.config))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
