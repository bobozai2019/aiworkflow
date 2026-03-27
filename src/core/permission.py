"""
Agent权限管理模块

定义各Agent的文件访问权限控制。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional

from loguru import logger


class Permission(Enum):
    """权限类型枚举"""
    NONE = "none"
    READ = "read"
    WRITE = "write"
    READ_WRITE = "read_write"
    
    def can_read(self) -> bool:
        return self in (Permission.READ, Permission.READ_WRITE)
    
    def can_write(self) -> bool:
        return self in (Permission.WRITE, Permission.READ_WRITE)


@dataclass
class DirectoryPermission:
    """
    目录权限配置
    
    Attributes:
        directory: 目录路径（相对于项目根目录）
        permission: 权限类型
        description: 权限描述
    """
    directory: str
    permission: Permission
    description: str = ""
    
    def resolve_path(self, project_root: Path) -> Path:
        """解析为绝对路径（不使用 resolve，避免目录不存在时的问题）"""
        path = project_root / self.directory
        return path
    
    def matches(self, file_path: Path, project_root: Path) -> bool:
        """检查文件路径是否在此目录权限范围内"""
        try:
            resolved_dir = self.resolve_path(project_root)
            if not file_path.is_absolute():
                resolved_file = project_root / file_path
            else:
                resolved_file = file_path
            
            dir_str = resolved_dir.as_posix().rstrip('/')
            file_str = resolved_file.as_posix().rstrip('/')
            
            if file_str == dir_str:
                return True
            
            return file_str.startswith(dir_str + '/')
        except Exception:
            return False


@dataclass
class AgentPermission:
    """
    Agent权限配置
    
    Attributes:
        agent_name: Agent名称
        directories: 目录权限列表
        file_patterns: 文件模式权限（如 *.md, *.py）
        max_file_size: 最大文件大小限制（字节）
    """
    agent_name: str
    directories: List[DirectoryPermission] = field(default_factory=list)
    file_patterns: Dict[str, Permission] = field(default_factory=dict)
    max_file_size: int = 10 * 1024 * 1024
    
    def get_permission_for_path(self, file_path: Path, project_root: Path) -> Permission:
        """
        获取指定路径的权限
        
        使用最长路径匹配原则，返回最具体的权限配置。
        
        Args:
            file_path: 文件路径
            project_root: 项目根目录
            
        Returns:
            权限类型
        """
        file_path = Path(file_path)
        if not file_path.is_absolute():
            file_path = project_root / file_path
        
        best_match: DirectoryPermission | None = None
        best_match_len = -1
        
        for dir_perm in self.directories:
            if dir_perm.matches(file_path, project_root):
                resolved_dir = dir_perm.resolve_path(project_root)
                match_len = len(resolved_dir.as_posix())
                if match_len > best_match_len:
                    best_match = dir_perm
                    best_match_len = match_len
        
        if best_match:
            pattern_perm = self._get_pattern_permission(file_path)
            if pattern_perm != Permission.NONE:
                return self._intersect_permissions(best_match.permission, pattern_perm)
            return best_match.permission
        
        return Permission.NONE
    
    def _get_pattern_permission(self, file_path: Path) -> Permission:
        """获取文件模式权限"""
        for pattern, perm in self.file_patterns.items():
            if file_path.match(pattern):
                return perm
        return Permission.NONE
    
    def _intersect_permissions(self, p1: Permission, p2: Permission) -> Permission:
        """计算权限交集"""
        can_read = p1.can_read() and p2.can_read()
        can_write = p1.can_write() and p2.can_write()
        
        if can_read and can_write:
            return Permission.READ_WRITE
        elif can_read:
            return Permission.READ
        elif can_write:
            return Permission.WRITE
        else:
            return Permission.NONE


class PermissionManager:
    """
    权限管理器
    
    管理所有Agent的权限配置，提供权限检查接口。
    """
    
    _instance: Optional["PermissionManager"] = None
    _permissions: Dict[str, AgentPermission] = {}
    _project_root: Optional[Path] = None
    
    def __new__(cls) -> "PermissionManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._permissions = {}
            cls._instance._project_root = None
        return cls._instance
    
    def initialize(self, project_root: Path) -> None:
        """
        初始化权限管理器
        
        Args:
            project_root: 项目根目录
        """
        self._project_root = Path(project_root).resolve()
        self._setup_default_permissions()
        logger.info(f"[PermissionManager] Initialized with project root: {self._project_root}")
    
    def _setup_default_permissions(self) -> None:
        """设置默认权限配置"""
        self._permissions = {
            "需求分析师": AgentPermission(
                agent_name="需求分析师",
                directories=[
                    DirectoryPermission(
                        directory="requirements",
                        permission=Permission.READ_WRITE,
                        description="需求文档目录，可读写需求相关文档"
                    ),
                ],
                file_patterns={}
            ),
            "系统架构师": AgentPermission(
                agent_name="系统架构师",
                directories=[
                    DirectoryPermission(
                        directory="requirements",
                        permission=Permission.READ,
                        description="需求文档目录，只读"
                    ),
                    DirectoryPermission(
                        directory="code",
                        permission=Permission.READ_WRITE,
                        description="代码目录，架构文档放在代码根路径"
                    ),
                ],
                file_patterns={}
            ),
            "代码开发者": AgentPermission(
                agent_name="代码开发者",
                directories=[
                    DirectoryPermission(
                        directory="requirements",
                        permission=Permission.READ,
                        description="需求文档目录，只读"
                    ),
                    DirectoryPermission(
                        directory="code",
                        permission=Permission.READ_WRITE,
                        description="代码目录，可读写"
                    ),
                ],
                file_patterns={}
            ),
            "调试员": AgentPermission(
                agent_name="调试员",
                directories=[
                    DirectoryPermission(
                        directory="requirements",
                        permission=Permission.READ,
                        description="需求文档目录，只读"
                    ),
                    DirectoryPermission(
                        directory="code",
                        permission=Permission.READ_WRITE,
                        description="代码目录，可读写（修复代码）"
                    ),
                    DirectoryPermission(
                        directory="tests",
                        permission=Permission.READ,
                        description="测试目录，只读"
                    ),
                ],
                file_patterns={}
            ),
            "测试员": AgentPermission(
                agent_name="测试员",
                directories=[
                    DirectoryPermission(
                        directory=".",
                        permission=Permission.READ,
                        description="项目根目录，只读（查看目录结构）"
                    ),
                    DirectoryPermission(
                        directory="requirements",
                        permission=Permission.READ,
                        description="需求文档目录，只读"
                    ),
                    DirectoryPermission(
                        directory="code",
                        permission=Permission.READ,
                        description="代码目录，只读"
                    ),
                    DirectoryPermission(
                        directory="tests",
                        permission=Permission.READ_WRITE,
                        description="测试目录，可读写测试文件"
                    ),
                ],
                file_patterns={}
            ),
        }
    
    def register_permission(self, permission: AgentPermission) -> None:
        """
        注册Agent权限
        
        Args:
            permission: Agent权限配置
        """
        self._permissions[permission.agent_name] = permission
        logger.info(f"[PermissionManager] Registered permission for: {permission.agent_name}")
    
    def get_permission(self, agent_name: str) -> Optional[AgentPermission]:
        """
        获取Agent权限配置
        
        Args:
            agent_name: Agent名称
            
        Returns:
            权限配置，不存在返回None
        """
        return self._permissions.get(agent_name)
    
    def check_read_permission(self, agent_name: str, file_path: Path) -> bool:
        """
        检查读权限
        
        Args:
            agent_name: Agent名称
            file_path: 文件路径
            
        Returns:
            是否有读权限
        """
        if not self._project_root:
            logger.warning("[PermissionManager] Not initialized, denying access")
            return False
        
        permission = self.get_permission(agent_name)
        if not permission:
            logger.warning(f"[PermissionManager] No permission config for: {agent_name}")
            return False
        
        file_perm = permission.get_permission_for_path(file_path, self._project_root)
        result = file_perm.can_read()
        
        if not result:
            logger.warning(
                f"[PermissionManager] {agent_name} denied READ access to: {file_path}"
            )
        
        return result
    
    def check_write_permission(self, agent_name: str, file_path: Path) -> bool:
        """
        检查写权限
        
        Args:
            agent_name: Agent名称
            file_path: 文件路径
            
        Returns:
            是否有写权限
        """
        if not self._project_root:
            logger.warning("[PermissionManager] Not initialized, denying access")
            return False
        
        permission = self.get_permission(agent_name)
        if not permission:
            logger.warning(f"[PermissionManager] No permission config for: {agent_name}")
            return False
        
        file_perm = permission.get_permission_for_path(file_path, self._project_root)
        result = file_perm.can_write()
        
        if not result:
            logger.warning(
                f"[PermissionManager] {agent_name} denied WRITE access to: {file_path}"
            )
        
        return result
    
    def get_allowed_directories(self, agent_name: str, write_only: bool = False) -> List[Path]:
        """
        获取Agent允许访问的目录列表
        
        Args:
            agent_name: Agent名称
            write_only: 是否只返回可写入的目录
            
        Returns:
            允许访问的目录列表
        """
        permission = self.get_permission(agent_name)
        if not permission or not self._project_root:
            return []
        
        if write_only:
            return [
                dp.resolve_path(self._project_root) 
                for dp in permission.directories 
                if dp.permission.can_write()
            ]
        
        return [dp.resolve_path(self._project_root) for dp in permission.directories]
    
    def get_permission_info(self, agent_name: str) -> Dict:
        """
        获取Agent权限信息（用于提示词）
        
        Args:
            agent_name: Agent名称
            
        Returns:
            权限信息字典
        """
        permission = self.get_permission(agent_name)
        if not permission:
            return {"error": f"未找到 {agent_name} 的权限配置"}
        
        return {
            "agent_name": agent_name,
            "directories": [
                {
                    "path": dp.directory,
                    "permission": dp.permission.value,
                    "description": dp.description
                }
                for dp in permission.directories
            ],
            "file_patterns": {
                pattern: perm.value 
                for pattern, perm in permission.file_patterns.items()
            }
        }


def get_permission_manager() -> PermissionManager:
    """获取权限管理器单例"""
    return PermissionManager()


__all__ = [
    "Permission",
    "DirectoryPermission",
    "AgentPermission",
    "PermissionManager",
    "get_permission_manager",
]
