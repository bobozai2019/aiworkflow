"""
配置管理模块

负责加载和管理YAML配置文件，支持环境变量替换。
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from dotenv import load_dotenv


class Config:
    """
    配置管理器
    
    负责加载YAML配置文件，支持环境变量替换和嵌套访问。
    
    Attributes:
        _instance: 单例实例
        _config: 配置数据
        _agents: Agent配置
        _protocols: 协议配置
        _config_dir: 配置目录路径
    """
    
    _instance: Optional[Config] = None
    _config: Dict[str, Any] = {}
    _agents: Dict[str, Any] = {}
    _protocols: Dict[str, Any] = {}
    _config_dir: str = "config"
    _cache_file: str = "cache.json"
    
    def __new__(cls) -> Config:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def load(cls, config_dir: str = "config") -> Config:
        """
        加载所有配置文件
        
        Args:
            config_dir: 配置文件目录
            
        Returns:
            Config实例
        """
        load_dotenv()
        
        instance = cls()
        instance._config_dir = config_dir
        config_path = Path(config_dir)
        
        instance._config = instance._load_yaml(config_path / "config.yaml")
        instance._agents = instance._load_yaml(config_path / "agents.yaml").get("agents", {})
        instance._protocols = instance._load_yaml(config_path / "protocols.yaml").get("protocols", {})
        
        return instance
    
    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """
        加载YAML文件并替换环境变量
        
        Args:
            path: 文件路径
            
        Returns:
            配置字典
        """
        if not path.exists():
            return {}
        
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        
        content = self._replace_env_vars(content)
        
        return yaml.safe_load(content) or {}
    
    def _replace_env_vars(self, content: str) -> str:
        """
        替换环境变量占位符
        
        Args:
            content: 文件内容
            
        Returns:
            替换后的内容
        """
        pattern = r"\$\{([^}]+)\}"
        
        def replacer(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return os.getenv(var_name, match.group(0))
        
        return re.sub(pattern, replacer, content)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项，支持点号分隔的路径
        
        Args:
            key: 配置键，如 "app.name"
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key.split(".")
        value: Any = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置项，支持点号分隔的路径
        
        Args:
            key: 配置键，如 "app.name"
            value: 配置值
        """
        keys = key.split(".")
        config: Dict[str, Any] = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            if isinstance(config, dict):
                config = config[k]
        
        if isinstance(config, dict):
            config[keys[-1]] = value
    
    def save(self) -> None:
        """保存配置到文件"""
        config_path = Path(self._config_dir)
        
        self._save_yaml(config_path / "config.yaml", self._config)
        
        agents_data = {"agents": self._agents}
        self._save_yaml(config_path / "agents.yaml", agents_data)
        
        protocols_data = {"protocols": self._protocols}
        self._save_yaml(config_path / "protocols.yaml", protocols_data)
    
    def _save_yaml(self, path: Path, data: Dict[str, Any]) -> None:
        """
        保存数据到YAML文件
        
        Args:
            path: 文件路径
            data: 要保存的数据
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    
    def _get_cache_path(self) -> Path:
        """获取缓存文件路径"""
        return Path(self._config_dir) / self._cache_file
    
    def get_cache(self, key: str, default: Any = None) -> Any:
        """
        获取缓存项
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            缓存值
        """
        cache_path = self._get_cache_path()
        if not cache_path.exists():
            return default
        
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                return cache_data.get(key, default)
        except (json.JSONDecodeError, IOError):
            return default
    
    def set_cache(self, key: str, value: Any) -> None:
        """
        设置缓存项
        
        Args:
            key: 缓存键
            value: 缓存值
        """
        cache_path = self._get_cache_path()
        cache_data: Dict[str, Any] = {}
        
        if cache_path.exists():
            try:
                with open(cache_path, "r", encoding="utf-8") as f:
                    cache_data = json.load(f)
            except (json.JSONDecodeError, IOError):
                cache_data = {}
        
        cache_data[key] = value
        
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(cache_data, f, ensure_ascii=False, indent=2)
    
    def get_last_project(self) -> Optional[str]:
        """
        获取上次打开的项目路径
        
        Returns:
            项目路径字符串，如果没有则返回 None
        """
        return self.get_cache("last_project")
    
    def set_last_project(self, project_path: str) -> None:
        """
        保存项目路径到缓存
        
        Args:
            project_path: 项目路径
        """
        self.set_cache("last_project", project_path)
    
    def get_agent(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent配置
        
        Args:
            name: Agent名称
            
        Returns:
            Agent配置字典
        """
        return self._agents.get(name)
    
    def get_protocol(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取协议配置
        
        Args:
            name: 协议名称
            
        Returns:
            协议配置字典
        """
        return self._protocols.get(name)
    
    @property
    def app_name(self) -> str:
        return self.get("app.name", "Multi-Agent System")
    
    @property
    def debug(self) -> bool:
        return self.get("app.debug", False)
    
    @property
    def http_timeout(self) -> int:
        return self.get("http.timeout", 60)
    
    @property
    def http_max_retries(self) -> int:
        return self.get("http.max_retries", 3)
    
    @property
    def output_dir(self) -> Path:
        """
        获取输出目录路径
        
        Returns:
            输出目录的Path对象
        """
        dir_str = self.get("output.dir", "./output")
        return Path(dir_str).resolve()
    
    def get_agent_with_replaced_prompt(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent配置
        
        注意: {OUTPUT_DIR} 占位符会在运行时由 Workflow 动态替换，
        因为项目目录是根据任务动态创建的。
        
        Args:
            name: Agent名称
            
        Returns:
            Agent配置字典
        """
        agent_config = self._agents.get(name)
        if agent_config is None:
            return None
        
        return agent_config.copy()


config: Config = Config()
