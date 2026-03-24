"""
异常定义模块

定义系统中的所有异常类型。
"""

from __future__ import annotations


class AgentError(Exception):
    """Agent系统基础异常"""
    
    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class ProtocolError(AgentError):
    """协议相关错误"""
    
    def __init__(self, message: str, provider: str = "", status_code: int = None) -> None:
        self.provider = provider
        self.status_code = status_code
        super().__init__(message)


class WorkflowError(AgentError):
    """工作流相关错误"""
    pass


class ConfigError(AgentError):
    """配置相关错误"""
    pass


__all__ = ["AgentError", "ProtocolError", "WorkflowError", "ConfigError"]
