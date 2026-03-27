"""
工具系统模块测试
"""

import pytest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.tools.base import (
    ToolResult,
    ToolParameter,
    BaseTool,
    ToolRegistry,
    FileReadTool,
    FileListTool,
    FileWriteTool,
    WebSearchTool,
    WebFetchTool,
    register_default_tools,
)


class TestToolResult:
    """工具执行结果测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = ToolResult(success=True, content="测试内容")
        
        assert result.success is True
        assert result.content == "测试内容"
        assert result.error is None
        assert result.metadata == {}
    
    def test_failure_result(self):
        """测试失败结果"""
        result = ToolResult(success=False, content="", error="发生错误")
        
        assert result.success is False
        assert result.error == "发生错误"
    
    def test_result_with_metadata(self):
        """测试带元数据的结果"""
        result = ToolResult(
            success=True,
            content="内容",
            metadata={"file_path": "/test.py", "size": 100}
        )
        
        assert result.metadata["file_path"] == "/test.py"
        assert result.metadata["size"] == 100


class TestToolParameter:
    """工具参数定义测试"""
    
    def test_required_parameter(self):
        """测试必需参数"""
        param = ToolParameter(
            name="file_path",
            type="string",
            description="文件路径"
        )
        
        assert param.name == "file_path"
        assert param.type == "string"
        assert param.description == "文件路径"
        assert param.required is True
        assert param.default is None
    
    def test_optional_parameter(self):
        """测试可选参数"""
        param = ToolParameter(
            name="pattern",
            type="string",
            description="匹配模式",
            required=False,
            default="*"
        )
        
        assert param.required is False
        assert param.default == "*"


class MockTool(BaseTool):
    """模拟工具用于测试"""
    
    name = "mock_tool"
    description = "模拟工具"
    parameters = [
        ToolParameter(name="input", type="string", description="输入")
    ]
    
    def execute(self, input: str) -> ToolResult:
        return ToolResult(success=True, content=f"处理: {input}")


class TestBaseTool:
    """工具基类测试"""
    
    def test_get_schema(self):
        """测试获取JSON Schema"""
        tool = MockTool()
        schema = tool.get_schema()
        
        assert schema["name"] == "mock_tool"
        assert schema["description"] == "模拟工具"
        assert "parameters" in schema
        assert "properties" in schema["parameters"]
        assert "input" in schema["parameters"]["properties"]
        assert "input" in schema["parameters"]["required"]


class TestToolRegistry:
    """工具注册中心测试"""
    
    @pytest.fixture(autouse=True)
    def reset_registry(self):
        """每个测试前重置注册中心"""
        ToolRegistry._tools = {}
        ToolRegistry._current_agent = None
        yield
    
    def test_register(self):
        """测试注册工具"""
        tool = MockTool()
        ToolRegistry.register(tool)
        
        assert "mock_tool" in ToolRegistry._tools
        assert ToolRegistry.get("mock_tool") == tool
    
    def test_get_not_found(self):
        """测试获取不存在的工具"""
        result = ToolRegistry.get("nonexistent")
        assert result is None
    
    def test_list_tools(self):
        """测试列出工具"""
        ToolRegistry.register(MockTool())
        
        tools = ToolRegistry.list_tools()
        assert "mock_tool" in tools
    
    def test_get_schemas(self):
        """测试获取所有工具Schema"""
        ToolRegistry.register(MockTool())
        
        schemas = ToolRegistry.get_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "mock_tool"
    
    def test_execute(self):
        """测试执行工具"""
        ToolRegistry.register(MockTool())
        
        result = ToolRegistry.execute("mock_tool", input="test")
        
        assert result.success is True
        assert result.content == "处理: test"
    
    def test_execute_not_found(self):
        """测试执行不存在的工具"""
        result = ToolRegistry.execute("nonexistent")
        
        assert result.success is False
        assert "工具不存在" in result.error
    
    def test_execute_with_error(self):
        """测试执行工具时出错"""
        class ErrorTool(BaseTool):
            name = "error_tool"
            description = "错误工具"
            parameters = []
            
            def execute(self):
                raise ValueError("测试错误")
        
        ToolRegistry.register(ErrorTool())
        result = ToolRegistry.execute("error_tool")
        
        assert result.success is False
        assert "测试错误" in result.error
    
    def test_set_current_agent(self):
        """测试设置当前Agent"""
        ToolRegistry.set_current_agent("TestAgent")
        
        assert ToolRegistry.get_current_agent() == "TestAgent"
    
    def test_execute_with_permission(self):
        """测试带权限执行"""
        ToolRegistry.register(MockTool())
        
        result = ToolRegistry.execute_with_permission(
            "mock_tool",
            "TestAgent",
            input="test"
        )
        
        assert result.success is True
        assert ToolRegistry.get_current_agent() == "TestAgent"


class TestFileReadTool:
    """文件读取工具测试"""
    
    @pytest.fixture(autouse=True)
    def reset_registry(self):
        ToolRegistry._tools = {}
        ToolRegistry._current_agent = None
    
    @pytest.fixture
    def temp_file(self):
        """创建临时文件"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
            f.write("test content line 1\n")
            f.write("test content line 2")
            temp_path = Path(f.name)
        yield temp_path
    
    def test_execute_success(self, temp_file):
        """测试成功读取文件"""
        ToolRegistry.set_current_agent("TestAgent")
        
        with patch('src.core.permission.get_permission_manager') as mock_pm:
            pm = MagicMock()
            pm._project_root = None
            pm.check_read_permission.return_value = True
            mock_pm.return_value = pm
            
            tool = FileReadTool()
            result = tool.execute(str(temp_file))
            
            assert result.success is True
            assert result.metadata["size"] > 0
    
    def test_execute_no_agent(self, temp_file):
        """测试未设置Agent"""
        tool = FileReadTool()
        result = tool.execute(str(temp_file))
        
        assert result.success is False
        assert "未设置当前Agent" in result.error
    
    def test_execute_permission_denied(self, temp_file):
        """测试权限拒绝"""
        ToolRegistry.set_current_agent("TestAgent")
        
        with patch('src.core.permission.get_permission_manager') as mock_pm:
            pm = MagicMock()
            pm._project_root = None
            pm.check_read_permission.return_value = False
            pm.get_allowed_directories.return_value = ["/allowed"]
            mock_pm.return_value = pm
            
            tool = FileReadTool()
            result = tool.execute(str(temp_file))
            
            assert result.success is False
            assert "权限拒绝" in result.error
    
    def test_execute_file_not_found(self):
        """测试文件不存在"""
        ToolRegistry.set_current_agent("TestAgent")
        
        with patch('src.core.permission.get_permission_manager') as mock_pm:
            pm = MagicMock()
            pm._project_root = None
            pm.check_read_permission.return_value = True
            mock_pm.return_value = pm
            
            tool = FileReadTool()
            result = tool.execute("/nonexistent/file.txt")
            
            assert result.success is False
            assert "文件不存在" in result.error


class TestFileListTool:
    """文件列表工具测试"""
    
    @pytest.fixture(autouse=True)
    def reset_registry(self):
        ToolRegistry._tools = {}
        ToolRegistry._current_agent = None
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as d:
            temp_path = Path(d)
            (temp_path / "file1.txt").write_text("content1", encoding='utf-8')
            (temp_path / "file2.py").write_text("print('hello')", encoding='utf-8')
            (temp_path / "subdir").mkdir()
            yield temp_path
    
    def test_execute_success(self, temp_dir):
        """测试成功列出目录"""
        ToolRegistry.set_current_agent("TestAgent")
        
        with patch('src.core.permission.get_permission_manager') as mock_pm:
            pm = MagicMock()
            pm._project_root = None
            pm.check_read_permission.return_value = True
            mock_pm.return_value = pm
            
            tool = FileListTool()
            result = tool.execute(str(temp_dir))
            
            assert result.success is True
            assert "file1.txt" in result.content
            assert "file2.py" in result.content
            assert "subdir" in result.content
    
    def test_execute_with_pattern(self, temp_dir):
        """测试带模式列出目录"""
        ToolRegistry.set_current_agent("TestAgent")
        
        with patch('src.core.permission.get_permission_manager') as mock_pm:
            pm = MagicMock()
            pm._project_root = None
            pm.check_read_permission.return_value = True
            mock_pm.return_value = pm
            
            tool = FileListTool()
            result = tool.execute(str(temp_dir), pattern="*.py")
            
            assert result.success is True
            assert "file2.py" in result.content
            assert "file1.txt" not in result.content


class TestFileWriteTool:
    """文件写入工具测试"""
    
    @pytest.fixture(autouse=True)
    def reset_registry(self):
        ToolRegistry._tools = {}
        ToolRegistry._current_agent = None
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)
    
    def test_execute_write(self, temp_dir):
        """测试写入文件"""
        ToolRegistry.set_current_agent("TestAgent")
        
        with patch('src.core.permission.get_permission_manager') as mock_pm:
            pm = MagicMock()
            pm._project_root = None
            pm.check_write_permission.return_value = True
            mock_pm.return_value = pm
            
            tool = FileWriteTool()
            file_path = temp_dir / "test.txt"
            result = tool.execute(str(file_path), "测试内容")
            
            assert result.success is True
            assert file_path.read_text(encoding='utf-8') == "测试内容"
    
    def test_execute_append(self, temp_dir):
        """测试追加写入"""
        ToolRegistry.set_current_agent("TestAgent")
        
        with patch('src.core.permission.get_permission_manager') as mock_pm:
            pm = MagicMock()
            pm._project_root = None
            pm.check_write_permission.return_value = True
            mock_pm.return_value = pm
            
            tool = FileWriteTool()
            file_path = temp_dir / "test.txt"
            file_path.write_text("初始内容\n", encoding='utf-8')
            
            result = tool.execute(str(file_path), "追加内容", mode="append")
            
            assert result.success is True
            assert "初始内容" in file_path.read_text(encoding='utf-8')
            assert "追加内容" in file_path.read_text(encoding='utf-8')


class TestWebSearchTool:
    """网络搜索工具测试"""
    
    def test_execute_success(self):
        """测试成功搜索"""
        tool = WebSearchTool()
        
        mock_response_data = {"AbstractText": "Test abstract", "AbstractURL": "http://test.com", "RelatedTopics": []}
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = json.dumps(mock_response_data).encode('utf-8')
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=None)
            mock_urlopen.return_value = mock_response
            
            result = tool.execute("test query")
            
            assert result.success is True
    
    def test_execute_error(self):
        """测试搜索出错"""
        tool = WebSearchTool()
        
        with patch('urllib.request.urlopen', side_effect=Exception("Network error")):
            result = tool.execute("test query")
            
            assert result.success is False
            assert "网络搜索失败" in result.error


class TestWebFetchTool:
    """网页抓取工具测试"""
    
    def test_execute_success(self):
        """测试成功抓取"""
        tool = WebFetchTool()
        
        with patch('urllib.request.urlopen') as mock_urlopen:
            mock_response = MagicMock()
            mock_response.read.return_value = b"<html><body><p>Test content</p></body></html>"
            mock_response.__enter__ = MagicMock(return_value=mock_response)
            mock_response.__exit__ = MagicMock(return_value=None)
            mock_urlopen.return_value = mock_response
            
            result = tool.execute("http://test.com")
            
            assert result.success is True
            assert "Test content" in result.content
    
    def test_execute_error(self):
        """测试抓取出错"""
        tool = WebFetchTool()
        
        with patch('urllib.request.urlopen', side_effect=Exception("Connection error")):
            result = tool.execute("http://test.com")
            
            assert result.success is False
            assert "获取网页失败" in result.error


class TestRegisterDefaultTools:
    """注册默认工具测试"""
    
    @pytest.fixture(autouse=True)
    def reset_registry(self):
        ToolRegistry._tools = {}
        yield
    
    def test_register_default_tools(self):
        """测试注册默认工具"""
        register_default_tools()
        
        tools = ToolRegistry.list_tools()
        assert "file_read" in tools
        assert "file_list" in tools
        assert "file_write" in tools
        assert "file_search" in tools
        assert "web_search" in tools
        assert "web_fetch" in tools
