"""
日志模块

基于loguru的日志封装，支持控制台和文件输出。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from loguru import logger


def setup_logger(
    level: str = "INFO",
    log_file: Optional[str] = None,
    log_format: str = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
) -> None:
    """
    配置日志系统
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
        log_format: 日志格式
    """
    logger.remove()
    
    logger.add(
        sys.stderr,
        format=log_format,
        level=level,
        colorize=True
    )
    
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            format=log_format,
            level=level,
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8"
        )


__all__ = ["logger", "setup_logger"]
