"""
文件工具模块

用于解析Agent输出中的代码块并保存到文件系统。
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from loguru import logger


@dataclass
class CodeBlock:
    """
    代码块数据结构
    
    Attributes:
        language: 编程语言
        filename: 文件名（可选）
        content: 代码内容
    """
    
    language: str
    filename: Optional[str]
    content: str


class FileTool:
    """
    文件工具类
    
    用于解析Agent输出中的代码块并保存文件。
    """
    
    CODE_BLOCK_PATTERN = re.compile(
        r'```(\w+)?(?:\s+file:\s*([^\n]+))?\n(.*?)```',
        re.DOTALL
    )
    
    FILENAME_PATTERNS = [
        re.compile(r'(?:文件名|filename|file):\s*[`]?([^\s`\n]+)[`]?'),
        re.compile(r'(?:保存到|save to):\s*[`]?([^\s`\n]+)[`]?'),
        re.compile(r'###\s*([a-zA-Z0-9_\-./]+\.\w+)'),
    ]
    
    def __init__(self, output_dir: Path):
        """
        初始化文件工具
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def parse_code_blocks(self, content: str) -> List[CodeBlock]:
        """
        从内容中解析代码块
        
        Args:
            content: Agent输出内容
            
        Returns:
            代码块列表
        """
        blocks = []
        
        matches = self.CODE_BLOCK_PATTERN.findall(content)
        
        for match in matches:
            language = match[0] or "text"
            explicit_filename = match[1].strip() if match[1] else None
            code_content = match[2].strip()
            
            filename = explicit_filename or self._guess_filename(content, language)
            
            blocks.append(CodeBlock(
                language=language,
                filename=filename,
                content=code_content
            ))
        
        return blocks
    
    def _guess_filename(self, content: str, language: str) -> Optional[str]:
        """
        尝试从内容中猜测文件名
        
        Args:
            content: 完整内容
            language: 编程语言
            
        Returns:
            猜测的文件名
        """
        for pattern in self.FILENAME_PATTERNS:
            match = pattern.search(content)
            if match:
                return match.group(1)
        
        lang_extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "go": "go",
            "rust": "rs",
            "c": "c",
            "cpp": "cpp",
            "csharp": "cs",
            "ruby": "rb",
            "php": "php",
            "swift": "swift",
            "kotlin": "kt",
            "sql": "sql",
            "html": "html",
            "css": "css",
            "json": "json",
            "yaml": "yaml",
            "yml": "yml",
            "markdown": "md",
            "shell": "sh",
            "bash": "sh",
        }
        
        ext = lang_extensions.get(language.lower(), language)
        return f"output.{ext}"
    
    def save_code_block(self, block: CodeBlock, sub_dir: str = None) -> Optional[Path]:
        """
        保存代码块到文件
        
        Args:
            block: 代码块
            sub_dir: 子目录（可选）
            
        Returns:
            保存的文件路径，失败返回None
        """
        if not block.filename:
            return None
        
        if sub_dir:
            target_dir = self.output_dir / sub_dir
        else:
            target_dir = self.output_dir
        
        target_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = target_dir / block.filename
        
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(block.content)
            
            logger.info(f"[FileTool] Saved: {file_path}")
            return file_path
            
        except Exception as e:
            logger.error(f"[FileTool] Failed to save {file_path}: {e}")
            return None
    
    def process_content(
        self,
        content: str,
        sub_dir: str = None
    ) -> tuple[str, List[Path]]:
        """
        处理内容，解析并保存所有代码块
        
        Args:
            content: Agent输出内容
            sub_dir: 子目录（可选）
            
        Returns:
            (原始内容, 保存的文件路径列表)
        """
        blocks = self.parse_code_blocks(content)
        saved_paths = []
        
        for block in blocks:
            path = self.save_code_block(block, sub_dir)
            if path:
                saved_paths.append(path)
        
        return content, saved_paths
