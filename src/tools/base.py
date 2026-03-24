"""
工具系统模块

为Agent提供可调用的工具能力，支持权限控制。
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    content: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolParameter:
    """工具参数定义"""
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


class BaseTool(ABC):
    """工具基类"""
    
    name: str = ""
    description: str = ""
    parameters: List[ToolParameter] = []
    requires_permission: bool = False
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具的JSON Schema"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type,
                        "description": p.description
                    } for p in self.parameters
                },
                "required": [p.name for p in self.parameters if p.required]
            }
        }


class ToolRegistry:
    """工具注册中心"""
    
    _tools: Dict[str, BaseTool] = {}
    _current_agent: Optional[str] = None
    
    @classmethod
    def register(cls, tool: BaseTool) -> None:
        cls._tools[tool.name] = tool
        logger.info(f"[ToolRegistry] Registered tool: {tool.name}")
    
    @classmethod
    def get(cls, name: str) -> Optional[BaseTool]:
        return cls._tools.get(name)
    
    @classmethod
    def list_tools(cls) -> List[str]:
        return list(cls._tools.keys())
    
    @classmethod
    def get_schemas(cls) -> List[Dict[str, Any]]:
        return [tool.get_schema() for tool in cls._tools.values()]
    
    @classmethod
    def set_current_agent(cls, agent_name: str) -> None:
        """设置当前执行的Agent名称"""
        cls._current_agent = agent_name
    
    @classmethod
    def get_current_agent(cls) -> Optional[str]:
        """获取当前执行的Agent名称"""
        return cls._current_agent
    
    @classmethod
    def execute(cls, name: str, **kwargs) -> ToolResult:
        tool = cls.get(name)
        if not tool:
            return ToolResult(
                success=False,
                content="",
                error=f"工具不存在: {name}"
            )
        
        try:
            return tool.execute(**kwargs)
        except Exception as e:
            logger.error(f"[ToolRegistry] Tool execution error: {e}")
            return ToolResult(
                success=False,
                content="",
                error=str(e)
            )
    
    @classmethod
    def execute_with_permission(
        cls, 
        name: str, 
        agent_name: str,
        **kwargs
    ) -> ToolResult:
        """
        带权限检查的工具执行
        
        Args:
            name: 工具名称
            agent_name: Agent名称
            **kwargs: 工具参数
            
        Returns:
            工具执行结果
        """
        cls.set_current_agent(agent_name)
        return cls.execute(name, **kwargs)


class FileReadTool(BaseTool):
    """文件读取工具（带权限检查）"""
    
    name = "file_read"
    description = "读取本地文件内容"
    requires_permission = True
    parameters = [
        ToolParameter(
            name="file_path",
            type="string",
            description="要读取的文件路径",
            required=True
        )
    ]
    
    def execute(self, file_path: str) -> ToolResult:
        from src.core.permission import get_permission_manager
        
        agent_name = ToolRegistry.get_current_agent()
        if not agent_name:
            return ToolResult(
                success=False,
                content="",
                error="权限错误: 未设置当前Agent"
            )
        
        path = Path(file_path)
        if not path.is_absolute():
            pm = get_permission_manager()
            if pm._project_root:
                path = pm._project_root / file_path
        
        pm = get_permission_manager()
        if not pm.check_read_permission(agent_name, path):
            allowed_dirs = pm.get_allowed_directories(agent_name)
            allowed_info = "\n".join([f"  - {d}" for d in allowed_dirs])
            return ToolResult(
                success=False,
                content="",
                error=f"权限拒绝: {agent_name} 没有读取 {file_path} 的权限\n允许访问的目录:\n{allowed_info}"
            )
        
        try:
            if not path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"文件不存在: {file_path}"
                )
            
            if not path.is_file():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"路径不是文件: {file_path}"
                )
            
            content = path.read_text(encoding="utf-8")
            
            return ToolResult(
                success=True,
                content=content,
                metadata={
                    "file_path": str(path),
                    "size": len(content),
                    "lines": content.count("\n") + 1
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"读取文件失败: {str(e)}"
            )


class FileListTool(BaseTool):
    """文件列表工具（带权限检查）"""
    
    name = "file_list"
    description = "列出目录下的文件和子目录"
    requires_permission = True
    parameters = [
        ToolParameter(
            name="directory",
            type="string",
            description="要列出的目录路径，默认为当前项目目录",
            required=False,
            default="."
        ),
        ToolParameter(
            name="pattern",
            type="string",
            description="文件匹配模式，如 *.py",
            required=False,
            default="*"
        )
    ]
    
    def execute(self, directory: str = ".", pattern: str = "*") -> ToolResult:
        from src.core.permission import get_permission_manager
        
        agent_name = ToolRegistry.get_current_agent()
        if not agent_name:
            return ToolResult(
                success=False,
                content="",
                error="权限错误: 未设置当前Agent"
            )
        
        path = Path(directory)
        if not path.is_absolute():
            pm = get_permission_manager()
            if pm._project_root:
                path = pm._project_root / directory
        
        pm = get_permission_manager()
        if not pm.check_read_permission(agent_name, path):
            allowed_dirs = pm.get_allowed_directories(agent_name)
            allowed_info = "\n".join([f"  - {d}" for d in allowed_dirs])
            return ToolResult(
                success=False,
                content="",
                error=f"权限拒绝: {agent_name} 没有访问 {directory} 的权限\n允许访问的目录:\n{allowed_info}"
            )
        
        try:
            if not path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"目录不存在: {directory}"
                )
            
            if not path.is_dir():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"路径不是目录: {directory}"
                )
            
            items = list(path.glob(pattern))
            
            result_lines = []
            for item in sorted(items):
                if item.is_dir():
                    result_lines.append(f"📁 {item.name}/")
                else:
                    size = item.stat().st_size
                    result_lines.append(f"📄 {item.name} ({size} bytes)")
            
            content = "\n".join(result_lines) if result_lines else "目录为空"
            
            return ToolResult(
                success=True,
                content=content,
                metadata={
                    "directory": str(path),
                    "count": len(items)
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"列出目录失败: {str(e)}"
            )


class FileSearchTool(BaseTool):
    """文件搜索工具（带权限检查）"""
    
    name = "file_search"
    description = "在文件中搜索指定内容"
    requires_permission = True
    parameters = [
        ToolParameter(
            name="directory",
            type="string",
            description="搜索的目录路径",
            required=True
        ),
        ToolParameter(
            name="query",
            type="string",
            description="搜索的关键词或正则表达式",
            required=True
        ),
        ToolParameter(
            name="file_pattern",
            type="string",
            description="文件匹配模式，如 *.py",
            required=False,
            default="*"
        )
    ]
    
    def execute(self, directory: str, query: str, file_pattern: str = "*") -> ToolResult:
        from src.core.permission import get_permission_manager
        
        agent_name = ToolRegistry.get_current_agent()
        if not agent_name:
            return ToolResult(
                success=False,
                content="",
                error="权限错误: 未设置当前Agent"
            )
        
        path = Path(directory)
        if not path.is_absolute():
            pm = get_permission_manager()
            if pm._project_root:
                path = pm._project_root / directory
        
        pm = get_permission_manager()
        if not pm.check_read_permission(agent_name, path):
            allowed_dirs = pm.get_allowed_directories(agent_name)
            allowed_info = "\n".join([f"  - {d}" for d in allowed_dirs])
            return ToolResult(
                success=False,
                content="",
                error=f"权限拒绝: {agent_name} 没有搜索 {directory} 的权限\n允许访问的目录:\n{allowed_info}"
            )
        
        try:
            if not path.exists():
                return ToolResult(
                    success=False,
                    content="",
                    error=f"目录不存在: {directory}"
                )
            
            results = []
            pattern = re.compile(query, re.IGNORECASE)
            
            for file_path in path.rglob(file_pattern):
                if not file_path.is_file():
                    continue
                
                if not pm.check_read_permission(agent_name, file_path):
                    continue
                
                try:
                    content = file_path.read_text(encoding="utf-8")
                    for i, line in enumerate(content.split("\n"), 1):
                        if pattern.search(line):
                            results.append(f"{file_path}:{i}: {line.strip()[:100]}")
                except Exception as e:
                    logger.debug(f"[FileSearchTool] 跳过文件 {file_path}: {e}")
                    continue
            
            if not results:
                return ToolResult(
                    success=True,
                    content="未找到匹配内容",
                    metadata={"matches": 0}
                )
            
            return ToolResult(
                success=True,
                content="\n".join(results[:50]),
                metadata={"matches": len(results)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"搜索失败: {str(e)}"
            )


class FileWriteTool(BaseTool):
    """文件写入工具（带权限检查）"""
    
    name = "file_write"
    description = "写入内容到文件，如果文件不存在则创建"
    requires_permission = True
    parameters = [
        ToolParameter(
            name="file_path",
            type="string",
            description="要写入的文件路径",
            required=True
        ),
        ToolParameter(
            name="content",
            type="string",
            description="要写入的文件内容",
            required=True
        ),
        ToolParameter(
            name="mode",
            type="string",
            description="写入模式: 'write' 覆盖写入, 'append' 追加写入",
            required=False,
            default="write"
        )
    ]
    
    def execute(self, file_path: str, content: str, mode: str = "write") -> ToolResult:
        from src.core.permission import get_permission_manager
        
        agent_name = ToolRegistry.get_current_agent()
        if not agent_name:
            return ToolResult(
                success=False,
                content="",
                error="权限错误: 未设置当前Agent"
            )
        
        path = Path(file_path)
        if not path.is_absolute():
            pm = get_permission_manager()
            if pm._project_root:
                path = pm._project_root / file_path
        
        pm = get_permission_manager()
        if not pm.check_write_permission(agent_name, path):
            allowed_dirs = pm.get_allowed_directories(agent_name, write_only=True)
            allowed_info = "\n".join([f"  - {d}" for d in allowed_dirs])
            return ToolResult(
                success=False,
                content="",
                error=f"权限拒绝: {agent_name} 没有写入 {file_path} 的权限\n允许写入的目录:\n{allowed_info}"
            )
        
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            
            write_mode = "a" if mode == "append" else "w"
            with open(path, write_mode, encoding="utf-8") as f:
                f.write(content)
            
            action = "追加" if mode == "append" else "写入"
            return ToolResult(
                success=True,
                content=f"成功{action}文件: {file_path}",
                metadata={
                    "file_path": str(path),
                    "size": len(content),
                    "mode": mode
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"写入文件失败: {str(e)}"
            )


class WebSearchTool(BaseTool):
    """网络搜索工具"""
    
    name = "web_search"
    description = "在网络上搜索信息（使用DuckDuckGo）"
    parameters = [
        ToolParameter(
            name="query",
            type="string",
            description="搜索关键词",
            required=True
        ),
        ToolParameter(
            name="num_results",
            type="integer",
            description="返回结果数量",
            required=False,
            default=5
        )
    ]
    
    def execute(self, query: str, num_results: int = 5) -> ToolResult:
        try:
            search_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
            
            req = urllib.request.Request(
                search_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))
            
            results = []
            
            if data.get("AbstractText"):
                results.append(f"📖 摘要: {data['AbstractText']}")
                if data.get("AbstractURL"):
                    results.append(f"🔗 来源: {data['AbstractURL']}")
            
            related = data.get("RelatedTopics", [])[:num_results]
            for topic in related:
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append(f"• {topic['Text']}")
                    if topic.get("FirstURL"):
                        results.append(f"  链接: {topic['FirstURL']}")
            
            if not results:
                return ToolResult(
                    success=True,
                    content="未找到相关结果",
                    metadata={"query": query}
                )
            
            return ToolResult(
                success=True,
                content="\n".join(results),
                metadata={"query": query, "results": len(results)}
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"网络搜索失败: {str(e)}"
            )


class WebFetchTool(BaseTool):
    """网页抓取工具"""
    
    name = "web_fetch"
    description = "获取网页内容"
    parameters = [
        ToolParameter(
            name="url",
            type="string",
            description="要获取的网页URL",
            required=True
        )
    ]
    
    def execute(self, url: str) -> ToolResult:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                }
            )
            
            with urllib.request.urlopen(req, timeout=15) as response:
                content = response.read().decode("utf-8", errors="ignore")
            
            text_content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            text_content = re.sub(r'<style[^>]*>.*?</style>', '', text_content, flags=re.DOTALL)
            text_content = re.sub(r'<[^>]+>', ' ', text_content)
            text_content = re.sub(r'\s+', ' ', text_content).strip()
            
            if len(text_content) > 5000:
                text_content = text_content[:5000] + "...(内容已截断)"
            
            return ToolResult(
                success=True,
                content=text_content,
                metadata={
                    "url": url,
                    "length": len(text_content)
                }
            )
        except Exception as e:
            return ToolResult(
                success=False,
                content="",
                error=f"获取网页失败: {str(e)}"
            )


def register_default_tools() -> None:
    """注册默认工具"""
    ToolRegistry.register(FileReadTool())
    ToolRegistry.register(FileListTool())
    ToolRegistry.register(FileSearchTool())
    ToolRegistry.register(FileWriteTool())
    ToolRegistry.register(WebSearchTool())
    ToolRegistry.register(WebFetchTool())


__all__ = [
    "ToolResult",
    "ToolParameter",
    "BaseTool",
    "ToolRegistry",
    "FileReadTool",
    "FileListTool",
    "FileSearchTool",
    "FileWriteTool",
    "WebSearchTool",
    "WebFetchTool",
    "register_default_tools",
]
