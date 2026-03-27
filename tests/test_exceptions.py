"""
异常模块测试
"""

import pytest

from src.exceptions import AgentError, ProtocolError, WorkflowError, ConfigError


class TestAgentError:
    """Agent基础异常测试"""
    
    def test_init(self):
        """测试初始化"""
        error = AgentError("测试错误")
        assert error.message == "测试错误"
        assert str(error) == "测试错误"
    
    def test_raise(self):
        """测试抛出异常"""
        with pytest.raises(AgentError) as exc_info:
            raise AgentError("发生错误")
        assert str(exc_info.value) == "发生错误"


class TestProtocolError:
    """协议异常测试"""
    
    def test_init_basic(self):
        """测试基本初始化"""
        error = ProtocolError("API调用失败")
        assert error.message == "API调用失败"
        assert error.provider == ""
        assert error.status_code is None
    
    def test_init_with_provider(self):
        """测试带provider初始化"""
        error = ProtocolError("API调用失败", provider="deepseek")
        assert error.provider == "deepseek"
        assert error.status_code is None
    
    def test_init_with_status_code(self):
        """测试带状态码初始化"""
        error = ProtocolError("API调用失败", provider="deepseek", status_code=429)
        assert error.provider == "deepseek"
        assert error.status_code == 429
    
    def test_inheritance(self):
        """测试继承关系"""
        error = ProtocolError("测试")
        assert isinstance(error, AgentError)
        assert isinstance(error, Exception)


class TestWorkflowError:
    """工作流异常测试"""
    
    def test_init(self):
        """测试初始化"""
        error = WorkflowError("工作流执行失败")
        assert error.message == "工作流执行失败"
    
    def test_inheritance(self):
        """测试继承关系"""
        error = WorkflowError("测试")
        assert isinstance(error, AgentError)


class TestConfigError:
    """配置异常测试"""
    
    def test_init(self):
        """测试初始化"""
        error = ConfigError("配置文件不存在")
        assert error.message == "配置文件不存在"
    
    def test_inheritance(self):
        """测试继承关系"""
        error = ConfigError("测试")
        assert isinstance(error, AgentError)


class TestExceptionHierarchy:
    """异常层次结构测试"""
    
    def test_all_exceptions_inherit_from_agent_error(self):
        """测试所有异常都继承自AgentError"""
        exceptions = [
            ProtocolError("test"),
            WorkflowError("test"),
            ConfigError("test"),
        ]
        
        for exc in exceptions:
            assert isinstance(exc, AgentError)
            assert isinstance(exc, Exception)
    
    def test_catch_with_base_class(self):
        """测试可以用基类捕获派生异常"""
        with pytest.raises(AgentError):
            raise ProtocolError("API错误")
        
        with pytest.raises(AgentError):
            raise WorkflowError("工作流错误")
        
        with pytest.raises(AgentError):
            raise ConfigError("配置错误")
