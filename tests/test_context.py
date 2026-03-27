"""
上下文管理模块测试
"""

import pytest

from src.core.context import Context, TaskResult
from src.core.message import Message


class TestTaskResult:
    """任务执行结果测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = TaskResult(
            success=True,
            content="任务完成",
            agent_name="测试Agent"
        )
        
        assert result.success is True
        assert result.content == "任务完成"
        assert result.agent_name == "测试Agent"
        assert result.error is None
        assert result.saved_files == []
    
    def test_failure_result(self):
        """测试失败结果"""
        result = TaskResult(
            success=False,
            content="",
            agent_name="测试Agent",
            error="发生错误"
        )
        
        assert result.success is False
        assert result.error == "发生错误"
    
    def test_result_with_files(self):
        """测试带文件的结果"""
        result = TaskResult(
            success=True,
            content="代码已生成",
            agent_name="Coder",
            saved_files=["/path/to/main.py", "/path/to/test.py"]
        )
        
        assert len(result.saved_files) == 2
        assert "/path/to/main.py" in result.saved_files
    
    def test_result_with_reasoning(self):
        """测试带思考过程的结果"""
        result = TaskResult(
            success=True,
            content="结果",
            reasoning_content="这是思考过程"
        )
        
        assert result.reasoning_content == "这是思考过程"


class TestContext:
    """上下文管理测试"""
    
    @pytest.fixture
    def context(self):
        """创建上下文实例"""
        return Context()
    
    def test_init(self, context):
        """测试初始化"""
        assert context.data == {}
        assert context.results == {}
        assert context.messages == []
    
    def test_set_get(self, context):
        """测试设置和获取数据"""
        context.set("key1", "value1")
        assert context.get("key1") == "value1"
        
        context.set("key2", {"nested": "data"})
        assert context.get("key2") == {"nested": "data"}
    
    def test_get_default(self, context):
        """测试获取不存在的键返回默认值"""
        assert context.get("nonexistent") is None
        assert context.get("nonexistent", "default") == "default"
    
    def test_set_result(self, context):
        """测试设置结果"""
        result = TaskResult(
            success=True,
            content="完成",
            agent_name="Agent1"
        )
        
        context.set_result("Agent1", result)
        
        assert context.get_result("Agent1") == result
    
    def test_get_result_not_found(self, context):
        """测试获取不存在的结果"""
        assert context.get_result("Nonexistent") is None
    
    def test_get_previous_result(self, context):
        """测试获取上一个结果"""
        result1 = TaskResult(success=True, content="结果1", agent_name="Agent1")
        result2 = TaskResult(success=True, content="结果2", agent_name="Agent2")
        
        context.set_result("Agent1", result1)
        context.set_result("Agent2", result2)
        
        prev = context.get_previous_result()
        assert prev == result2
    
    def test_get_previous_result_empty(self, context):
        """测试空结果时获取上一个结果"""
        assert context.get_previous_result() is None
    
    def test_add_message(self, context):
        """测试添加消息"""
        msg = Message(role="user", content="Hello")
        
        context.add_message(msg)
        
        assert len(context.messages) == 1
        assert context.messages[0] == msg
    
    def test_add_multiple_messages(self, context):
        """测试添加多个消息"""
        msg1 = Message(role="user", content="Hello")
        msg2 = Message(role="assistant", content="Hi there")
        
        context.add_message(msg1)
        context.add_message(msg2)
        
        assert len(context.messages) == 2
        assert context.messages[0] == msg1
        assert context.messages[1] == msg2
    
    def test_get_all_content(self, context):
        """测试获取所有内容"""
        result1 = TaskResult(success=True, content="内容1", agent_name="Agent1")
        result2 = TaskResult(success=True, content="内容2", agent_name="Agent2")
        result3 = TaskResult(success=False, content="错误内容", agent_name="Agent3")
        
        context.set_result("Agent1", result1)
        context.set_result("Agent2", result2)
        context.set_result("Agent3", result3)
        
        all_content = context.get_all_content()
        
        assert "Agent1" in all_content
        assert "内容1" in all_content
        assert "Agent2" in all_content
        assert "内容2" in all_content
        assert "Agent3" not in all_content
    
    def test_get_all_content_empty(self, context):
        """测试空结果时获取所有内容"""
        all_content = context.get_all_content()
        assert all_content == ""


class TestContextIntegration:
    """上下文集成测试"""
    
    @pytest.fixture
    def context(self):
        return Context()
    
    def test_workflow_simulation(self, context):
        """测试模拟工作流"""
        context.set("task", "实现登录功能")
        context.set("project_path", "/project")
        
        analyst_result = TaskResult(
            success=True,
            content="# 需求分析\n用户登录功能...",
            agent_name="需求分析师"
        )
        context.set_result("需求分析师", analyst_result)
        
        prev = context.get_previous_result()
        assert prev == analyst_result
        
        coder_result = TaskResult(
            success=True,
            content="```python\nprint('hello')\n```",
            agent_name="代码开发者",
            saved_files=["/project/main.py"]
        )
        context.set_result("代码开发者", coder_result)
        
        all_content = context.get_all_content()
        assert "需求分析师" in all_content
        assert "代码开发者" in all_content
    
    def test_data_persistence(self, context):
        """测试数据持久化"""
        context.set("key1", "value1")
        context.set("key2", [1, 2, 3])
        context.set("key3", {"nested": True})
        
        assert context.get("key1") == "value1"
        assert context.get("key2") == [1, 2, 3]
        assert context.get("key3") == {"nested": True}
