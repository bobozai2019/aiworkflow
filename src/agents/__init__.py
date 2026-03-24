"""
Agent实现模块
包含具体Agent角色的实现
"""

from src.agents.base_agent import BaseAgent, AgentState
from src.agents.analyst import AnalystAgent
from src.agents.architect import ArchitectAgent
from src.agents.coder import CoderAgent
from src.agents.tester import TesterAgent
from src.agents.processors import (
    OutputProcessor,
    ProcessedOutput,
    CodeOutputProcessor,
    TestOutputProcessor,
    ArchitectureOutputProcessor,
    RequirementOutputProcessor,
    DefaultOutputProcessor,
    get_processor_for_agent,
)

__all__ = [
    "BaseAgent",
    "AgentState",
    "AnalystAgent",
    "ArchitectAgent",
    "CoderAgent",
    "TesterAgent",
    "OutputProcessor",
    "ProcessedOutput",
    "CodeOutputProcessor",
    "TestOutputProcessor",
    "ArchitectureOutputProcessor",
    "RequirementOutputProcessor",
    "DefaultOutputProcessor",
    "get_processor_for_agent",
]
