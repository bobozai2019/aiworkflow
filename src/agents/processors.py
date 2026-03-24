"""
Agent输出处理器模块

为不同类型的Agent提供特定的输出处理和验证逻辑。
"""

from __future__ import annotations

import ast
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class ProcessedOutput:
    """
    处理后的输出结果
    
    Attributes:
        content: 原始内容
        files: 保存的文件路径列表
        validation_errors: 验证错误列表
        validation_warnings: 验证警告列表
        metadata: 额外元数据
    """
    content: str
    files: List[Path] = field(default_factory=list)
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """是否通过验证"""
        return len(self.validation_errors) == 0


class OutputProcessor(ABC):
    """
    输出处理器基类
    
    所有Agent输出处理器必须继承此类。
    """
    
    @abstractmethod
    def validate(self, content: str) -> tuple[List[str], List[str]]:
        """
        验证输出内容
        
        Args:
            content: Agent输出内容
            
        Returns:
            (错误列表, 警告列表)
        """
        pass
    
    @abstractmethod
    def process(self, content: str, output_dir: Path, agent_name: str = None) -> ProcessedOutput:
        """
        处理Agent输出
        
        Args:
            content: Agent输出内容
            output_dir: 输出目录
            agent_name: Agent名称（用于权限检查）
            
        Returns:
            处理后的输出结果
        """
        pass
    
    def _extract_code_blocks(self, content: str) -> List[tuple[str, str, str]]:
        """
        提取代码块
        
        Args:
            content: 内容字符串
            
        Returns:
            [(语言, 文件名, 代码内容), ...]
        """
        pattern = r'```(\w+)?(?:\s+file:\s*([^\n]+))?\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)
        return [(m[0] or "text", m[1].strip() if m[1] else "", m[2].strip()) for m in matches]
    
    def _check_write_permission(self, file_path: Path, agent_name: str) -> bool:
        """
        检查写入权限
        
        Args:
            file_path: 文件路径
            agent_name: Agent名称
            
        Returns:
            是否有写入权限
        """
        if not agent_name:
            return True
        
        from src.core.permission import get_permission_manager
        pm = get_permission_manager()
        
        if not pm._project_root:
            return True
        
        return pm.check_write_permission(agent_name, file_path)
    
    def _save_file_with_permission(
        self, 
        file_path: Path, 
        content: str, 
        agent_name: str = None
    ) -> tuple[bool, Optional[str]]:
        """
        带权限检查的文件保存
        
        Args:
            file_path: 文件路径
            content: 文件内容
            agent_name: Agent名称
            
        Returns:
            (是否成功, 错误信息)
        """
        if agent_name and not self._check_write_permission(file_path, agent_name):
            return False, f"权限拒绝: {agent_name} 没有写入 {file_path} 的权限"
        
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content, encoding="utf-8")
            logger.info(f"[OutputProcessor] Saved file: {file_path}")
            return True, None
        except Exception as e:
            logger.error(f"[OutputProcessor] Failed to save {file_path}: {e}")
            return False, str(e)


class CodeOutputProcessor(OutputProcessor):
    """
    代码输出处理器
    
    用于CoderAgent，验证代码语法并提取代码块。
    """
    
    LANGUAGE_PARSERS = {
        "python": "_parse_python",
        "py": "_parse_python",
        "javascript": "_parse_javascript",
        "js": "_parse_javascript",
        "typescript": "_parse_typescript",
        "ts": "_parse_typescript",
    }
    
    def __init__(self, primary_language: str = "python"):
        self.primary_language = primary_language
    
    def validate(self, content: str) -> tuple[List[str], List[str]]:
        errors = []
        warnings = []
        
        code_blocks = self._extract_code_blocks(content)
        
        if not code_blocks:
            warnings.append("未检测到代码块，请确保使用 ``` 代码块格式输出代码")
            return errors, warnings
        
        for i, (lang, filename, code) in enumerate(code_blocks):
            block_name = filename or f"代码块{i+1}"
            
            if lang.lower() in ("python", "py"):
                syntax_errors = self._validate_python(code)
                for err in syntax_errors:
                    errors.append(f"{block_name}: {err}")
            
            if not filename:
                warnings.append(f"代码块{i+1}未指定文件名，将使用默认命名")
        
        return errors, warnings
    
    def _validate_python(self, code: str) -> List[str]:
        """验证Python代码语法"""
        errors = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"语法错误 (行{e.lineno}): {e.msg}")
        except Exception as e:
            errors.append(f"解析错误: {str(e)}")
        return errors
    
    def _validate_javascript(self, code: str) -> List[str]:
        """验证JavaScript代码（基础检查）"""
        errors = []
        open_braces = code.count('{')
        close_braces = code.count('}')
        open_parens = code.count('(')
        close_parens = code.count(')')
        open_brackets = code.count('[')
        close_brackets = code.count(']')
        
        if open_braces != close_braces:
            errors.append(f"花括号不匹配: {{ {open_braces} vs }} {close_braces}")
        if open_parens != close_parens:
            errors.append(f"圆括号不匹配: ( {open_parens} vs ) {close_parens}")
        if open_brackets != close_brackets:
            errors.append(f"方括号不匹配: [ {open_brackets} vs ] {close_brackets}")
        
        return errors
    
    def _validate_typescript(self, code: str) -> List[str]:
        """验证TypeScript代码（复用JavaScript检查）"""
        return self._validate_javascript(code)
    
    def process(self, content: str, output_dir: Path, agent_name: str = None) -> ProcessedOutput:
        from src.utils.file_tool import FileTool
        
        errors, warnings = self.validate(content)
        
        saved_files = []
        permission_errors = []
        
        code_blocks = self._extract_code_blocks(content)
        
        for lang, filename, code in code_blocks:
            if not filename:
                continue
            
            file_path = output_dir / filename
            success, error = self._save_file_with_permission(file_path, code, agent_name)
            if success:
                saved_files.append(file_path)
            else:
                permission_errors.append(error)
        
        errors.extend(permission_errors)
        
        language_stats: Dict[str, int] = {}
        for lang, _, _ in code_blocks:
            language_stats[lang] = language_stats.get(lang, 0) + 1
        
        return ProcessedOutput(
            content=content,
            files=saved_files,
            validation_errors=errors,
            validation_warnings=warnings,
            metadata={
                "block_count": len(code_blocks),
                "languages": language_stats,
                "primary_language": self.primary_language
            }
        )


class TestOutputProcessor(OutputProcessor):
    """
    测试输出处理器
    
    用于TesterAgent，验证测试文件格式并统计测试用例。
    """
    
    TEST_PATTERNS = {
        "python": [
            r'def\s+test_\w+\s*\(',
            r'async\s+def\s+test_\w+\s*\(',
            r'class\s+Test\w+\s*[:\(]',
        ],
        "javascript": [
            r'(it|test|describe)\s*\(["\']',
            r'expect\s*\(',
        ],
    }
    
    def __init__(self, framework: str = "pytest"):
        self.framework = framework
    
    def validate(self, content: str) -> tuple[List[str], List[str]]:
        errors = []
        warnings = []
        
        code_blocks = self._extract_code_blocks(content)
        
        if not code_blocks:
            warnings.append("未检测到测试代码块")
            return errors, warnings
        
        has_tests = False
        for lang, filename, code in code_blocks:
            patterns = self.TEST_PATTERNS.get(lang.lower(), [])
            for pattern in patterns:
                if re.search(pattern, code):
                    has_tests = True
                    break
            
            if lang.lower() in ("python", "py"):
                if "import pytest" not in code and "import unittest" not in code:
                    warnings.append(f"{filename or '测试文件'}: 建议添加测试框架导入")
                
                syntax_errors = self._validate_python_syntax(code)
                errors.extend(syntax_errors)
        
        if not has_tests:
            warnings.append("未检测到标准测试函数定义")
        
        return errors, warnings
    
    def _validate_python_syntax(self, code: str) -> List[str]:
        """验证Python语法"""
        errors = []
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"测试代码语法错误 (行{e.lineno}): {e.msg}")
        return errors
    
    def process(self, content: str, output_dir: Path, agent_name: str = None) -> ProcessedOutput:
        from src.utils.file_tool import FileTool
        
        errors, warnings = self.validate(content)
        
        saved_files = []
        permission_errors = []
        
        code_blocks = self._extract_code_blocks(content)
        
        for lang, filename, code in code_blocks:
            if not filename:
                continue
            
            file_path = output_dir / filename
            success, error = self._save_file_with_permission(file_path, code, agent_name)
            if success:
                saved_files.append(file_path)
            else:
                permission_errors.append(error)
        
        errors.extend(permission_errors)
        
        test_count = 0
        test_functions = []
        
        for pattern in self.TEST_PATTERNS.get("python", []):
            matches = re.findall(pattern, content)
            test_count += len(matches)
            test_functions.extend(matches)
        
        return ProcessedOutput(
            content=content,
            files=saved_files,
            validation_errors=errors,
            validation_warnings=warnings,
            metadata={
                "test_count": test_count,
                "framework": self.framework,
                "test_functions": test_functions[:10]
            }
        )


class ArchitectureOutputProcessor(OutputProcessor):
    """
    架构文档处理器
    
    用于ArchitectAgent，验证架构文档完整性。
    """
    
    REQUIRED_SECTIONS = [
        "## 模块设计",
        "## 接口定义",
    ]
    
    RECOMMENDED_SECTIONS = [
        "## 数据模型",
        "## 技术选型",
        "## 部署架构",
    ]
    
    def validate(self, content: str) -> tuple[List[str], List[str]]:
        errors = []
        warnings = []
        
        for section in self.REQUIRED_SECTIONS:
            if section not in content:
                errors.append(f"缺少必要章节: {section}")
        
        for section in self.RECOMMENDED_SECTIONS:
            if section not in content:
                warnings.append(f"建议添加章节: {section}")
        
        has_diagram = any([
            "```mermaid" in content,
            "```plantuml" in content,
            "```graph" in content,
            "graph " in content,
            "sequenceDiagram" in content,
            "classDiagram" in content,
        ])
        
        if not has_diagram:
            warnings.append("建议添加架构图（支持Mermaid、PlantUML等格式）")
        
        return errors, warnings
    
    def process(self, content: str, output_dir: Path, agent_name: str = None) -> ProcessedOutput:
        from src.utils.file_tool import FileTool
        
        errors, warnings = self.validate(content)
        
        saved_files = []
        permission_errors = []
        
        code_blocks = self._extract_code_blocks(content)
        
        for lang, filename, code in code_blocks:
            if not filename:
                continue
            
            file_path = output_dir / filename
            success, error = self._save_file_with_permission(file_path, code, agent_name)
            if success:
                saved_files.append(file_path)
            else:
                permission_errors.append(error)
        
        architecture_file = output_dir / "architecture.md"
        success, error = self._save_file_with_permission(architecture_file, content, agent_name)
        if success:
            saved_files.append(architecture_file)
        else:
            permission_errors.append(error)
        
        errors.extend(permission_errors)
        
        sections_found = []
        for section in self.REQUIRED_SECTIONS + self.RECOMMENDED_SECTIONS:
            if section in content:
                sections_found.append(section)
        
        return ProcessedOutput(
            content=content,
            files=saved_files,
            validation_errors=errors,
            validation_warnings=warnings,
            metadata={
                "sections_found": sections_found,
                "has_diagram": any([
                    "```mermaid" in content,
                    "```plantuml" in content,
                ])
            }
        )


class RequirementOutputProcessor(OutputProcessor):
    """
    需求文档处理器
    
    用于AnalystAgent，验证需求文档格式和完整性。
    """
    
    REQUIRED_SECTIONS = [
        "## 功能列表",
    ]
    
    RECOMMENDED_SECTIONS = [
        "## 需求概述",
        "## 详细需求",
        "## 技术建议",
    ]
    
    def validate(self, content: str) -> tuple[List[str], List[str]]:
        errors = []
        warnings = []
        
        for section in self.REQUIRED_SECTIONS:
            if section not in content:
                errors.append(f"缺少必要章节: {section}")
        
        for section in self.RECOMMENDED_SECTIONS:
            if section not in content:
                warnings.append(f"建议添加章节: {section}")
        
        feature_pattern = r'\d+\.\s*(.+?)(?:\s*-\s*优先级\s*[:：]?\s*(高|中|低))?'
        features = re.findall(feature_pattern, content)
        
        if not features:
            warnings.append("未检测到功能列表项，建议使用数字列表格式")
        
        has_acceptance = "验收标准" in content or "验收条件" in content
        if not has_acceptance:
            warnings.append("建议添加验收标准")
        
        return errors, warnings
    
    def process(self, content: str, output_dir: Path, agent_name: str = None) -> ProcessedOutput:
        from src.utils.file_tool import FileTool
        
        errors, warnings = self.validate(content)
        
        saved_files = []
        permission_errors = []
        
        code_blocks = self._extract_code_blocks(content)
        
        for lang, filename, code in code_blocks:
            if not filename:
                continue
            
            file_path = output_dir / filename
            success, error = self._save_file_with_permission(file_path, code, agent_name)
            if success:
                saved_files.append(file_path)
            else:
                permission_errors.append(error)
        
        requirements_file = output_dir / "requirements.md"
        success, error = self._save_file_with_permission(requirements_file, content, agent_name)
        if success:
            saved_files.append(requirements_file)
        else:
            permission_errors.append(error)
        
        errors.extend(permission_errors)
        
        feature_pattern = r'\d+\.\s*(.+?)(?:\s*-\s*优先级\s*[:：]?\s*(高|中|低))?'
        features = re.findall(feature_pattern, content)
        
        priority_stats = {"高": 0, "中": 0, "低": 0, "未指定": 0}
        for feature, priority in features:
            if priority in priority_stats:
                priority_stats[priority] += 1
            else:
                priority_stats["未指定"] += 1
        
        sections_found = []
        for section in self.REQUIRED_SECTIONS + self.RECOMMENDED_SECTIONS:
            if section in content:
                sections_found.append(section)
        
        return ProcessedOutput(
            content=content,
            files=saved_files,
            validation_errors=errors,
            validation_warnings=warnings,
            metadata={
                "feature_count": len(features),
                "priority_distribution": priority_stats,
                "sections_found": sections_found
            }
        )


class DefaultOutputProcessor(OutputProcessor):
    """
    默认输出处理器
    
    仅做基础的文件提取，不做特定验证。
    """
    
    def validate(self, content: str) -> tuple[List[str], List[str]]:
        return [], []
    
    def process(self, content: str, output_dir: Path, agent_name: str = None) -> ProcessedOutput:
        from src.utils.file_tool import FileTool
        
        saved_files = []
        permission_errors = []
        
        code_blocks = self._extract_code_blocks(content)
        
        for lang, filename, code in code_blocks:
            if not filename:
                continue
            
            file_path = output_dir / filename
            success, error = self._save_file_with_permission(file_path, code, agent_name)
            if success:
                saved_files.append(file_path)
            else:
                permission_errors.append(error)
        
        return ProcessedOutput(
            content=content,
            files=saved_files,
            validation_errors=permission_errors,
            metadata={"processor": "default"}
        )


def get_processor_for_agent(agent_type: str) -> OutputProcessor:
    """
    根据Agent类型获取对应的处理器
    
    Args:
        agent_type: Agent类型名称
        
    Returns:
        输出处理器实例
    """
    processors = {
        "analyst": RequirementOutputProcessor,
        "architect": ArchitectureOutputProcessor,
        "coder": CodeOutputProcessor,
        "tester": TestOutputProcessor,
    }
    
    processor_class = processors.get(agent_type.lower(), DefaultOutputProcessor)
    return processor_class()


__all__ = [
    "ProcessedOutput",
    "OutputProcessor",
    "CodeOutputProcessor",
    "TestOutputProcessor",
    "ArchitectureOutputProcessor",
    "RequirementOutputProcessor",
    "DefaultOutputProcessor",
    "get_processor_for_agent",
]
