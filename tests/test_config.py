"""
配置管理模块测试
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import patch

from src.utils.config import Config


class TestConfig:
    """配置管理器测试"""
    
    @pytest.fixture(autouse=True)
    def reset_config(self):
        """每个测试前重置配置单例"""
        Config._instance = None
        Config._config = {}
        Config._agents = {}
        Config._protocols = {}
        yield
    
    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        with tempfile.TemporaryDirectory() as d:
            config_dir = Path(d) / "config"
            config_dir.mkdir()
            
            (config_dir / "config.yaml").write_text("""
app:
  name: TestApp
  debug: true
http:
  timeout: 30
  max_retries: 2
output:
  dir: ./output
""", encoding="utf-8")
            
            (config_dir / "agents.yaml").write_text("""
agents:
  analyst:
    name: Analyst
    model: test-model
    temperature: 0.7
""", encoding="utf-8")
            
            (config_dir / "protocols.yaml").write_text("""
protocols:
  deepseek:
    base_url: https://api.test.com
    default_model: test-model
""", encoding="utf-8")
            
            yield str(config_dir)
    
    def test_load(self, temp_config_dir):
        """测试加载配置"""
        config = Config.load(temp_config_dir)
        
        assert config._config is not None
        assert config._agents is not None
        assert config._protocols is not None
    
    def test_get_simple(self, temp_config_dir):
        """测试获取简单配置项"""
        config = Config.load(temp_config_dir)
        
        assert config.get("app.name") == "TestApp"
        assert config.get("app.debug") is True
        assert config.get("http.timeout") == 30
    
    def test_get_nested(self, temp_config_dir):
        """测试获取嵌套配置项"""
        config = Config.load(temp_config_dir)
        
        assert config.get("http") == {"timeout": 30, "max_retries": 2}
    
    def test_get_default(self, temp_config_dir):
        """测试获取不存在的配置项返回默认值"""
        config = Config.load(temp_config_dir)
        
        assert config.get("nonexistent") is None
        assert config.get("nonexistent", "default") == "default"
        assert config.get("app.nonexistent", 42) == 42
    
    def test_set(self, temp_config_dir):
        """测试设置配置项"""
        config = Config.load(temp_config_dir)
        
        config.set("app.new_key", "new_value")
        assert config.get("app.new_key") == "new_value"
    
    def test_set_nested(self, temp_config_dir):
        """测试设置嵌套配置项"""
        config = Config.load(temp_config_dir)
        
        config.set("new.nested.key", "value")
        assert config.get("new.nested.key") == "value"
    
    def test_get_agent(self, temp_config_dir):
        """测试获取Agent配置"""
        config = Config.load(temp_config_dir)
        
        agent_config = config.get_agent("analyst")
        assert agent_config is not None
        assert agent_config["name"] == "Analyst"
        assert agent_config["temperature"] == 0.7
    
    def test_get_agent_not_found(self, temp_config_dir):
        """测试获取不存在的Agent配置"""
        config = Config.load(temp_config_dir)
        
        agent_config = config.get_agent("nonexistent")
        assert agent_config is None
    
    def test_get_protocol(self, temp_config_dir):
        """测试获取协议配置"""
        config = Config.load(temp_config_dir)
        
        protocol_config = config.get_protocol("deepseek")
        assert protocol_config is not None
        assert protocol_config["base_url"] == "https://api.test.com"
    
    def test_get_protocol_not_found(self, temp_config_dir):
        """测试获取不存在的协议配置"""
        config = Config.load(temp_config_dir)
        
        protocol_config = config.get_protocol("nonexistent")
        assert protocol_config is None
    
    def test_properties(self, temp_config_dir):
        """测试属性访问"""
        config = Config.load(temp_config_dir)
        
        assert config.app_name == "TestApp"
        assert config.debug is True
        assert config.http_timeout == 30
        assert config.http_max_retries == 2
    
    def test_output_dir(self, temp_config_dir):
        """测试输出目录属性"""
        config = Config.load(temp_config_dir)
        
        output_dir = config.output_dir
        assert isinstance(output_dir, Path)


class TestConfigCache:
    """配置缓存测试"""
    
    @pytest.fixture(autouse=True)
    def reset_config(self):
        """每个测试前重置配置单例"""
        Config._instance = None
        Config._config = {}
        Config._agents = {}
        Config._protocols = {}
        yield
    
    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        with tempfile.TemporaryDirectory() as d:
            config_dir = Path(d) / "config"
            config_dir.mkdir()
            
            (config_dir / "config.yaml").write_text("app:\n  name: TestApp\n", encoding="utf-8")
            (config_dir / "agents.yaml").write_text("agents: {}\n", encoding="utf-8")
            (config_dir / "protocols.yaml").write_text("protocols: {}\n", encoding="utf-8")
            
            yield str(config_dir)
    
    def test_get_cache_empty(self, temp_config_dir):
        """测试获取空缓存"""
        config = Config.load(temp_config_dir)
        
        value = config.get_cache("nonexistent")
        assert value is None
        
        value = config.get_cache("nonexistent", "default")
        assert value == "default"
    
    def test_set_cache(self, temp_config_dir):
        """测试设置缓存"""
        config = Config.load(temp_config_dir)
        
        config.set_cache("test_key", "test_value")
        value = config.get_cache("test_key")
        assert value == "test_value"
    
    def test_cache_persistence(self, temp_config_dir):
        """测试缓存持久化"""
        config = Config.load(temp_config_dir)
        
        config.set_cache("key1", "value1")
        
        Config._instance = None
        config2 = Config.load(temp_config_dir)
        
        value = config2.get_cache("key1")
        assert value == "value1"
    
    def test_last_project(self, temp_config_dir):
        """测试上次项目路径"""
        config = Config.load(temp_config_dir)
        
        assert config.get_last_project() is None
        
        config.set_last_project("/path/to/project")
        assert config.get_last_project() == "/path/to/project"


class TestConfigEnvVars:
    """配置环境变量替换测试"""
    
    @pytest.fixture(autouse=True)
    def reset_config(self):
        """每个测试前重置配置单例"""
        Config._instance = None
        Config._config = {}
        Config._agents = {}
        Config._protocols = {}
        yield
    
    @pytest.fixture
    def temp_config_dir_with_env(self):
        """创建带环境变量的临时配置目录"""
        with tempfile.TemporaryDirectory() as d:
            config_dir = Path(d) / "config"
            config_dir.mkdir()
            
            (config_dir / "config.yaml").write_text("""
app:
  name: TestApp
api:
  key: ${TEST_API_KEY}
  url: ${TEST_API_URL:-https://default.api.com}
""", encoding="utf-8")
            (config_dir / "agents.yaml").write_text("agents: {}\n", encoding="utf-8")
            (config_dir / "protocols.yaml").write_text("protocols: {}\n", encoding="utf-8")
            
            yield str(config_dir)
    
    def test_replace_env_var(self, temp_config_dir_with_env):
        """测试替换环境变量"""
        with patch.dict(os.environ, {"TEST_API_KEY": "secret_key_123"}):
            config = Config.load(temp_config_dir_with_env)
            
            assert config.get("api.key") == "secret_key_123"
    
    def test_env_var_not_set(self, temp_config_dir_with_env):
        """测试环境变量未设置时保留占位符"""
        config = Config.load(temp_config_dir_with_env)
        
        assert config.get("api.key") == "${TEST_API_KEY}"


class TestConfigSingleton:
    """配置单例测试"""
    
    def test_singleton(self):
        """测试单例模式"""
        config1 = Config()
        config2 = Config()
        
        assert config1 is config2
    
    def test_singleton_after_load(self):
        """测试加载后单例"""
        with tempfile.TemporaryDirectory() as d:
            config_dir = Path(d) / "config"
            config_dir.mkdir()
            
            (config_dir / "config.yaml").write_text("app:\n  name: App1\n", encoding="utf-8")
            (config_dir / "agents.yaml").write_text("agents: {}\n", encoding="utf-8")
            (config_dir / "protocols.yaml").write_text("protocols: {}\n", encoding="utf-8")
            
            config1 = Config.load(str(config_dir))
            config2 = Config()
            
            assert config1 is config2
            assert config2.get("app.name") == "App1"
