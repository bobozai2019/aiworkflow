"""
工作流测试模块
"""

import pytest
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path
import tempfile

from src.core.workflow import Workflow
from src.core.context import Context, TaskResult
from src.core.message import Message


class MockProtocol:
    """模拟协议"""
    
    def __init__(self):
        self.base_url = "https://mock.api"
        self.api_key = "mock_key"
        self.default_model = "mock-model"
    
    async def chat(self, messages, model=None, stream=True, **kwargs):
        from src.core.message import ChatChunk
        yield ChatChunk(content="测试响应")


class MockSuccessAgent:
    """模拟成功的Agent"""
    
    def __init__(self, name: str = "成功Agent"):
        self.name = name
        self.id = "test_id"
    
    def set_output_dir(self, path):
        pass
    
    def update_prompt_output_dir(self, path):
        pass
    
    async def execute(self, task, context):
        return TaskResult(
            success=True,
            content="执行成功",
            agent_id=self.id,
            agent_name=self.name,
            duration=0.1
        )


class MockFailingAgent:
    """模拟失败的Agent"""
    
    def __init__(self, name: str = "失败Agent"):
        self.name = name
        self.id = "fail_id"
    
    def set_output_dir(self, path):
        pass
    
    def update_prompt_output_dir(self, path):
        pass
    
    async def execute(self, task, context):
        return TaskResult(
            success=False,
            content="",
            agent_id=self.id,
            agent_name=self.name,
            duration=0.1,
            error="模拟失败"
        )


class TestWorkflow:
    """工作流测试"""
    
    def test_init(self):
        """测试初始化"""
        workflow = Workflow()
        assert len(workflow.agents) == 0
    
    def test_add_agent(self):
        """测试添加Agent"""
        workflow = Workflow()
        protocol = MockProtocol()
        
        from src.agents.analyst import AnalystAgent
        agent = AnalystAgent(protocol=protocol)
        
        workflow.add_agent(agent)
        
        assert len(workflow.agents) == 1
        assert workflow.agents[0] == agent
    
    def test_add_agent_chaining(self):
        """测试添加Agent链式调用"""
        workflow = Workflow()
        protocol = MockProtocol()
        
        from src.agents.analyst import AnalystAgent
        from src.agents.coder import CoderAgent
        
        result = workflow.add_agent(AnalystAgent(protocol=protocol)).add_agent(CoderAgent(protocol=protocol))
        
        assert result == workflow
        assert len(workflow.agents) == 2
    
    def test_get_agent_names(self):
        """测试获取Agent名称列表"""
        workflow = Workflow()
        protocol = MockProtocol()
        
        from src.agents.analyst import AnalystAgent
        from src.agents.coder import CoderAgent
        
        workflow.add_agent(AnalystAgent(protocol=protocol))
        workflow.add_agent(CoderAgent(protocol=protocol))
        
        names = workflow.get_agent_names()
        
        assert len(names) == 2
        assert "需求分析师" in names
        assert "代码开发者" in names
    
    def test_set_initial_context(self):
        """测试设置初始上下文"""
        workflow = Workflow()
        
        initial_results = {
            "需求分析师": TaskResult(
                success=True,
                content="测试需求",
                agent_name="需求分析师"
            )
        }
        
        workflow.set_initial_context(initial_results)
        
        assert workflow._initial_results == initial_results


class TestProgressCallback:
    """测试进度回调"""
    
    @pytest.mark.asyncio
    async def test_progress_callback_on_success(self):
        """测试成功时的进度回调"""
        workflow = Workflow()
        workflow.add_agent(MockSuccessAgent("测试Agent"))
        
        callbacks = []
        workflow.on_progress = lambda name, status, progress: callbacks.append({
            "agent": name,
            "status": status,
            "progress": progress
        })
        
        result = await workflow.run("测试任务")
        
        assert result.success == True
        
        assert len(callbacks) == 2
        
        assert callbacks[0]["agent"] == "测试Agent"
        assert callbacks[0]["status"] == "start"
        
        assert callbacks[1]["agent"] == "测试Agent"
        assert callbacks[1]["status"] == "complete"
    
    @pytest.mark.asyncio
    async def test_progress_callback_on_failure(self):
        """测试失败时的进度回调"""
        workflow = Workflow()
        workflow.add_agent(MockFailingAgent("失败Agent"))
        
        callbacks = []
        workflow.on_progress = lambda name, status, progress: callbacks.append({
            "agent": name,
            "status": status,
            "progress": progress
        })
        
        result = await workflow.run("测试任务")
        
        assert result.success == False
        
        assert len(callbacks) == 2
        
        assert callbacks[0]["agent"] == "失败Agent"
        assert callbacks[0]["status"] == "start"
        
        assert callbacks[1]["agent"] == "失败Agent"
        assert callbacks[1]["status"] == "failed"
    
    @pytest.mark.asyncio
    async def test_progress_callback_multiple_agents(self):
        """测试多个Agent的进度回调"""
        workflow = Workflow()
        workflow.add_agent(MockSuccessAgent("Agent1"))
        workflow.add_agent(MockSuccessAgent("Agent2"))
        
        callbacks = []
        workflow.on_progress = lambda name, status, progress: callbacks.append({
            "agent": name,
            "status": status,
            "progress": progress
        })
        
        result = await workflow.run("测试任务")
        
        assert result.success == True
        assert len(callbacks) == 4
        
        assert callbacks[0]["agent"] == "Agent1"
        assert callbacks[0]["status"] == "start"
        assert callbacks[1]["agent"] == "Agent1"
        assert callbacks[1]["status"] == "complete"
        
        assert callbacks[2]["agent"] == "Agent2"
        assert callbacks[2]["status"] == "start"
        assert callbacks[3]["agent"] == "Agent2"
        assert callbacks[3]["status"] == "complete"
    
    @pytest.mark.asyncio
    async def test_progress_callback_stops_on_failure(self):
        """测试失败时停止后续Agent执行"""
        workflow = Workflow()
        workflow.add_agent(MockFailingAgent("失败Agent"))
        workflow.add_agent(MockSuccessAgent("后续Agent"))
        
        callbacks = []
        workflow.on_progress = lambda name, status, progress: callbacks.append({
            "agent": name,
            "status": status
        })
        
        result = await workflow.run("测试任务")
        
        assert result.success == False
        
        assert len(callbacks) == 2
        assert all(cb["agent"] == "失败Agent" for cb in callbacks)
    
    @pytest.mark.asyncio
    async def test_progress_callback_without_callback(self):
        """测试没有回调时正常执行"""
        workflow = Workflow()
        workflow.add_agent(MockSuccessAgent("测试Agent"))
        
        workflow.on_progress = None
        
        result = await workflow.run("测试任务")
        
        assert result.success == True
    
    @pytest.mark.asyncio
    async def test_progress_values(self):
        """测试进度值计算"""
        workflow = Workflow()
        workflow.add_agent(MockSuccessAgent("Agent1"))
        workflow.add_agent(MockSuccessAgent("Agent2"))
        
        progress_values = []
        workflow.on_progress = lambda name, status, progress: progress_values.append(progress)
        
        await workflow.run("测试任务")
        
        assert progress_values[0] == 50.0
        assert progress_values[1] == 50.0
        assert progress_values[2] == 100.0
        assert progress_values[3] == 100.0


class TestWorkflowRun:
    """测试工作流执行"""
    
    @pytest.mark.asyncio
    async def test_run_with_no_agents(self):
        """测试没有Agent时执行"""
        workflow = Workflow()
        
        result = await workflow.run("测试任务")
        
        assert result.success == True
        assert result.agent_name == "Workflow"
    
    @pytest.mark.asyncio
    async def test_run_creates_project_dir(self):
        """测试执行时创建项目目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workflow = Workflow(base_output_dir=Path(tmpdir))
            workflow.add_agent(MockSuccessAgent())
            
            result = await workflow.run("测试任务")
            
            assert result.success == True
            assert result.saved_files is not None
            assert len(result.saved_files) > 0
    
    @pytest.mark.asyncio
    async def test_run_with_existing_project(self):
        """测试使用现有项目目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_dir = Path(tmpdir) / "existing_project"
            project_dir.mkdir()
            
            workflow = Workflow(
                base_output_dir=project_dir,
                use_existing_project=True
            )
            workflow.add_agent(MockSuccessAgent())
            
            result = await workflow.run("测试任务")
            
            assert result.success == True
    
    @pytest.mark.asyncio
    async def test_run_returns_failure_result(self):
        """测试返回失败结果"""
        workflow = Workflow()
        workflow.add_agent(MockFailingAgent())
        
        result = await workflow.run("测试任务")
        
        assert result.success == False
        assert result.error == "模拟失败"


class TestContext:
    """上下文测试"""
    
    def test_init(self):
        """测试初始化"""
        context = Context(task_id="test_001")
        assert context.task_id == "test_001"
        assert len(context.messages) == 0
    
    def test_add_message(self):
        """测试添加消息"""
        context = Context(task_id="test_001")
        message = Message(role="user", content="测试消息")
        
        context.add_message(message)
        
        assert len(context.messages) == 1
        assert context.messages[0].content == "测试消息"
    
    def test_set_get(self):
        """测试设置和获取数据"""
        context = Context(task_id="test_001")
        
        context.set("key1", "value1")
        context.set("key2", {"nested": "value"})
        
        assert context.get("key1") == "value1"
        assert context.get("key2")["nested"] == "value"
        assert context.get("nonexistent", "default") == "default"
    
    def test_set_result(self):
        """测试设置结果"""
        context = Context(task_id="test_001")
        
        result = TaskResult(
            success=True,
            content="测试内容",
            agent_id="test_id",
            agent_name="测试Agent"
        )
        
        context.set_result("测试Agent", result)
        
        assert context.get_result("测试Agent") == result
    
    def test_get_all_content(self):
        """测试获取所有内容"""
        context = Context(task_id="test_001")
        
        context.set_result("Agent1", TaskResult(
            success=True,
            content="内容1",
            agent_id="id1",
            agent_name="Agent1"
        ))
        context.set_result("Agent2", TaskResult(
            success=True,
            content="内容2",
            agent_id="id2",
            agent_name="Agent2"
        ))
        
        all_content = context.get_all_content()
        
        assert "内容1" in all_content
        assert "内容2" in all_content


class TestTaskResult:
    """任务结果测试"""
    
    def test_success_result(self):
        """测试成功结果"""
        result = TaskResult(
            success=True,
            content="测试内容",
            agent_id="test_id",
            agent_name="测试Agent",
            duration=1.5
        )
        
        assert result.success
        assert result.content == "测试内容"
        assert result.error is None
    
    def test_failure_result(self):
        """测试失败结果"""
        result = TaskResult(
            success=False,
            content="",
            agent_id="test_id",
            agent_name="测试Agent",
            duration=0.5,
            error="测试错误"
        )
        
        assert not result.success
        assert result.error == "测试错误"
    
    def test_result_with_saved_files(self):
        """测试带保存文件的结果"""
        result = TaskResult(
            success=True,
            content="测试内容",
            agent_id="test_id",
            agent_name="测试Agent",
            saved_files=["/path/to/file1.py", "/path/to/file2.py"]
        )
        
        assert len(result.saved_files) == 2
        assert "/path/to/file1.py" in result.saved_files


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
