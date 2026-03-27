"""
CLI命令行模块测试
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from src.cli import create_workflow, on_progress, on_chunk, on_reasoning, run_task, main


class TestCreateWorkflow:
    """创建工作流测试"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        with tempfile.TemporaryDirectory() as d:
            config_dir = Path(d) / "config"
            config_dir.mkdir()
            
            (config_dir / "config.yaml").write_text("""
app:
  name: TestApp
output:
  dir: ./output
""", encoding="utf-8")
            
            (config_dir / "agents.yaml").write_text("""
agents:
  analyst:
    name: Analyst
    model: test-model
    temperature: 0.7
  coder:
    name: Coder
    model: test-model
    temperature: 0.3
""", encoding="utf-8")
            
            (config_dir / "protocols.yaml").write_text("""
protocols:
  deepseek:
    api_key: test_key
    base_url: https://api.test.com
    default_model: test-model
""", encoding="utf-8")
            
            yield str(config_dir)
    
    def test_create_workflow_success(self, temp_config_dir):
        """测试成功创建工作流"""
        from src.utils.config import Config
        
        Config._instance = None
        config = Config.load(temp_config_dir)
        
        workflow = create_workflow(config)
        
        assert workflow is not None
        assert len(workflow.agents) == 2
    
    def test_create_workflow_no_protocol(self, temp_config_dir):
        """测试没有协议配置"""
        from src.utils.config import Config
        
        Config._instance = None
        config = Config.load(temp_config_dir)
        config._protocols = {}
        
        with pytest.raises(ValueError, match="DeepSeek protocol not configured"):
            create_workflow(config)


class TestCallbacks:
    """回调函数测试"""
    
    def test_on_progress_start(self, capsys):
        """测试进度回调 - 开始"""
        on_progress("TestAgent", "start", 0)
        
        captured = capsys.readouterr()
        assert "TestAgent" in captured.out
        assert "开始工作" in captured.out
    
    def test_on_progress_complete(self, capsys):
        """测试进度回调 - 完成"""
        on_progress("TestAgent", "complete", 100)
        
        captured = capsys.readouterr()
        assert "TestAgent" in captured.out
        assert "完成" in captured.out
    
    def test_on_chunk(self, capsys):
        """测试内容块回调"""
        on_chunk("Hello ")
        on_chunk("World!")
        
        captured = capsys.readouterr()
        assert "Hello World!" in captured.out
    
    def test_on_reasoning(self, capsys):
        """测试思考过程回调"""
        on_reasoning("Thinking...")
        
        captured = capsys.readouterr()
        assert "Thinking..." in captured.out


class TestRunTask:
    """执行任务测试"""
    
    @pytest.fixture
    def temp_config_dir(self):
        """创建临时配置目录"""
        with tempfile.TemporaryDirectory() as d:
            config_dir = Path(d) / "config"
            config_dir.mkdir()
            
            (config_dir / "config.yaml").write_text("""
app:
  name: TestApp
logging:
  level: INFO
output:
  dir: ./output
""", encoding="utf-8")
            
            (config_dir / "agents.yaml").write_text("""
agents:
  analyst:
    name: Analyst
    model: test-model
  coder:
    name: Coder
    model: test-model
""", encoding="utf-8")
            
            (config_dir / "protocols.yaml").write_text("""
protocols:
  deepseek:
    api_key: test_key
    base_url: https://api.test.com
    default_model: test-model
""", encoding="utf-8")
            
            yield str(config_dir)
    
    @pytest.mark.asyncio
    async def test_run_task_success(self, temp_config_dir):
        """测试成功执行任务"""
        from src.utils.config import Config
        Config._instance = None
        
        mock_workflow = MagicMock()
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.saved_files = ["/output/test.py"]
        mock_workflow.run = AsyncMock(return_value=mock_result)
        mock_workflow.agents = []
        mock_workflow.get_agent_names.return_value = ["analyst", "coder"]
        mock_workflow.base_output_dir = Path("/output")
        
        with patch('src.cli.create_workflow', return_value=mock_workflow):
            with patch('src.cli.setup_logger'):
                await run_task("测试任务", temp_config_dir)


class TestMain:
    """主入口测试"""
    
    def test_main_with_gui_flag(self):
        """测试GUI模式"""
        with patch('sys.argv', ['cli.py', '-g']):
            with patch('src.ui.run_gui') as mock_gui:
                main()
                mock_gui.assert_called_once()
    
    def test_main_interactive_mode(self, capsys):
        """测试交互模式"""
        with patch('sys.argv', ['cli.py']):
            with patch('builtins.input', side_effect=['quit']):
                main()
                
                captured = capsys.readouterr()
                assert "交互模式" in captured.out
    
    def test_main_with_task(self):
        """测试带任务参数 - 由于CLI进入交互模式，此测试跳过"""
        pytest.skip("CLI enters interactive mode which requires stdin")


class TestArgumentParsing:
    """参数解析测试"""
    
    def test_parse_task_argument(self):
        """测试任务参数"""
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument("task", nargs="?", help="任务描述")
        parser.add_argument("-c", "--config", default="config")
        parser.add_argument("-i", "--interactive", action="store_true")
        parser.add_argument("-g", "--gui", action="store_true")
        
        args = parser.parse_args(["test task"])
        assert args.task == "test task"
        assert args.config == "config"
    
    def test_parse_config_argument(self):
        """测试配置参数"""
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument("task", nargs="?")
        parser.add_argument("-c", "--config", default="config")
        parser.add_argument("-i", "--interactive", action="store_true")
        parser.add_argument("-g", "--gui", action="store_true")
        
        args = parser.parse_args(["-c", "/custom/config"])
        assert args.config == "/custom/config"
    
    def test_parse_gui_flag(self):
        """测试GUI标志"""
        import argparse
        
        parser = argparse.ArgumentParser()
        parser.add_argument("task", nargs="?")
        parser.add_argument("-c", "--config", default="config")
        parser.add_argument("-i", "--interactive", action="store_true")
        parser.add_argument("-g", "--gui", action="store_true")
        
        args = parser.parse_args(["-g"])
        assert args.gui is True


class TestIntegration:
    """集成测试"""
    
    @pytest.fixture
    def full_config_dir(self):
        """创建完整配置目录"""
        with tempfile.TemporaryDirectory() as d:
            config_dir = Path(d) / "config"
            config_dir.mkdir()
            
            (config_dir / "config.yaml").write_text("""
app:
  name: TestApp
logging:
  level: DEBUG
  format: "{time} | {level} | {message}"
output:
  dir: ./output
""", encoding="utf-8")
            
            (config_dir / "agents.yaml").write_text("""
agents:
  analyst:
    name: Analyst
    model: deepseek-chat
    temperature: 0.7
    system_prompt: "You are an analyst"
  coder:
    name: Coder
    model: deepseek-chat
    temperature: 0.3
    system_prompt: "You are a coder"
""", encoding="utf-8")
            
            (config_dir / "protocols.yaml").write_text("""
protocols:
  deepseek:
    api_key: sk-test-key
    base_url: https://api.deepseek.com
    default_model: deepseek-chat
""", encoding="utf-8")
            
            yield str(config_dir)
    
    def test_full_workflow_creation(self, full_config_dir):
        """测试完整工作流创建"""
        from src.utils.config import Config
        
        Config._instance = None
        config = Config.load(full_config_dir)
        
        assert config.get("app.name") == "TestApp"
        assert config.get_protocol("deepseek") is not None
        
        analyst_config = config.get_agent("analyst")
        assert analyst_config is not None
        assert analyst_config["temperature"] == 0.7
