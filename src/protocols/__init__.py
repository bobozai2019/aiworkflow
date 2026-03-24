"""
协议适配层
包含大模型API协议的实现
"""

from src.protocols.base import BaseProtocol


def create_protocol(name: str, **kwargs) -> BaseProtocol:
    """
    创建协议实例
    
    Args:
        name: 协议名称 (deepseek, qwen, glm, minimax)
        **kwargs: 协议参数
        
    Returns:
        协议实例
    """
    protocols = {
        "deepseek": _create_deepseek,
        "qwen": _create_qwen,
        "glm": _create_glm,
        "minimax": _create_minimax,
    }
    
    if name not in protocols:
        raise ValueError(f"Unknown protocol: {name}. Available: {list(protocols.keys())}")
    
    return protocols[name](**kwargs)


def _create_deepseek(**kwargs):
    from src.protocols.deepseek import DeepSeekProtocol
    return DeepSeekProtocol(**kwargs)


def _create_qwen(**kwargs):
    from src.protocols.qwen import QwenProtocol
    return QwenProtocol(**kwargs)


def _create_glm(**kwargs):
    from src.protocols.glm import GLMProtocol
    return GLMProtocol(**kwargs)


def _create_minimax(**kwargs):
    from src.protocols.minimax import MiniMaxProtocol
    return MiniMaxProtocol(**kwargs)


__all__ = ["BaseProtocol", "create_protocol"]
