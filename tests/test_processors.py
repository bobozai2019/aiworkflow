"""
Agent处理器测试模块

测试各Agent的输出处理器功能。
"""

import pytest
import tempfile
from pathlib import Path

from src.agents.processors import (
    CodeOutputProcessor,
    TestOutputProcessor,
    ArchitectureOutputProcessor,
    RequirementOutputProcessor,
    DefaultOutputProcessor,
    ProcessedOutput,
)


class TestCodeOutputProcessor:
    """代码输出处理器测试"""
    
    def test_valid_python_code(self):
        """测试有效的Python代码"""
        processor = CodeOutputProcessor()
        content = '''
## 实现方案
简单的hello world程序

```python file: hello.py
def hello():
    print("Hello, World!")
    return True
```
'''
        errors, warnings = processor.validate(content)
        assert len(errors) == 0
        assert len(warnings) == 0
    
    def test_invalid_python_syntax(self):
        """测试无效的Python语法"""
        processor = CodeOutputProcessor()
        content = '''
```python file: bad.py
def hello(:
    print("missing parenthesis"
```
'''
        errors, warnings = processor.validate(content)
        assert len(errors) > 0
        assert "语法错误" in errors[0]
    
    def test_missing_filename_warning(self):
        """测试缺少文件名警告"""
        processor = CodeOutputProcessor()
        content = '''
```python
def hello():
    pass
```
'''
        errors, warnings = processor.validate(content)
        assert len(warnings) > 0
        assert "未指定文件名" in warnings[0]
    
    def test_no_code_blocks(self):
        """测试无代码块"""
        processor = CodeOutputProcessor()
        content = "这是一段纯文本，没有代码块"
        errors, warnings = processor.validate(content)
        assert len(warnings) > 0
        assert "未检测到代码块" in warnings[0]
    
    def test_process_extracts_files(self):
        """测试处理提取文件"""
        processor = CodeOutputProcessor()
        content = '''
```python file: main.py
def main():
    pass
```

```python file: utils.py
def helper():
    pass
```
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            result = processor.process(content, Path(tmpdir))
            assert len(result.files) == 2
            assert result.metadata["block_count"] == 2
            assert "python" in result.metadata["languages"]


class TestTestOutputProcessor:
    """测试输出处理器测试"""
    
    def test_valid_test_file(self):
        """测试有效的测试文件"""
        processor = TestOutputProcessor()
        content = '''
```python file: test_example.py
import pytest

def test_addition():
    assert 1 + 1 == 2

def test_subtraction():
    assert 2 - 1 == 1
```
'''
        errors, warnings = processor.validate(content)
        assert len(errors) == 0
    
    def test_missing_test_framework_import(self):
        """测试缺少测试框架导入"""
        processor = TestOutputProcessor()
        content = '''
```python file: test_example.py
def test_something():
    assert True
```
'''
        errors, warnings = processor.validate(content)
        assert any("测试框架导入" in w for w in warnings)
    
    def test_no_test_functions(self):
        """测试无测试函数"""
        processor = TestOutputProcessor()
        content = '''
```python file: not_test.py
def regular_function():
    return 42
```
'''
        errors, warnings = processor.validate(content)
        assert any("测试函数" in w for w in warnings)
    
    def test_metadata_extraction(self):
        """测试元数据提取"""
        processor = TestOutputProcessor()
        content = '''
```python file: test_example.py
import pytest

def test_one():
    pass

def test_two():
    pass

async def test_async():
    pass
```
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            result = processor.process(content, Path(tmpdir))
            assert result.metadata["test_count"] >= 3
            assert result.metadata["framework"] == "pytest"


class TestArchitectureOutputProcessor:
    """架构文档处理器测试"""
    
    def test_complete_architecture(self):
        """测试完整的架构文档"""
        processor = ArchitectureOutputProcessor()
        content = '''
## 架构概述
这是一个微服务架构

## 模块设计
### 用户模块
- 职责: 用户管理

## 接口定义
### 用户API
- 路径: /api/users

## 数据模型
```json
{
  "User": {
    "id": "string"
  }
}
```

```mermaid
graph TD
    A --> B
```
'''
        errors, warnings = processor.validate(content)
        assert len(errors) == 0
    
    def test_missing_required_sections(self):
        """测试缺少必要章节"""
        processor = ArchitectureOutputProcessor()
        content = '''
## 架构概述
简单描述
'''
        errors, warnings = processor.validate(content)
        assert len(errors) > 0
        assert any("模块设计" in e for e in errors)
        assert any("接口定义" in e for e in errors)
    
    def test_missing_diagram_warning(self):
        """测试缺少架构图警告"""
        processor = ArchitectureOutputProcessor()
        content = '''
## 模块设计
内容

## 接口定义
内容
'''
        errors, warnings = processor.validate(content)
        assert any("架构图" in w for w in warnings)


class TestRequirementOutputProcessor:
    """需求文档处理器测试"""
    
    def test_complete_requirement(self):
        """测试完整的需求文档"""
        processor = RequirementOutputProcessor()
        content = '''
## 需求概述
用户管理系统

## 功能列表
1. 用户注册 - 优先级: 高
2. 用户登录 - 优先级: 高
3. 密码重置 - 优先级: 中

## 详细需求
### 用户注册
- 描述: 用户可以通过邮箱注册
- 验收标准:
  - [ ] 支持邮箱注册
  - [ ] 密码强度验证

## 技术建议
使用JWT进行认证
'''
        errors, warnings = processor.validate(content)
        assert len(errors) == 0
    
    def test_missing_feature_list(self):
        """测试缺少功能列表"""
        processor = RequirementOutputProcessor()
        content = '''
## 需求概述
简单描述
'''
        errors, warnings = processor.validate(content)
        assert len(errors) > 0
        assert any("功能列表" in e for e in errors)
    
    def test_priority_distribution(self):
        """测试优先级分布统计"""
        processor = RequirementOutputProcessor()
        content = '''
## 功能列表
1. 功能A - 优先级: 高
2. 功能B - 优先级: 高
3. 功能C - 优先级: 中
4. 功能D - 优先级: 低
5. 功能E
'''
        with tempfile.TemporaryDirectory() as tmpdir:
            result = processor.process(content, Path(tmpdir))
            assert "priority_distribution" in result.metadata
            assert "feature_count" in result.metadata
            assert result.metadata["feature_count"] == 5


class TestDefaultOutputProcessor:
    """默认处理器测试"""
    
    def test_always_valid(self):
        """测试默认处理器总是有效"""
        processor = DefaultOutputProcessor()
        content = "任意内容"
        errors, warnings = processor.validate(content)
        assert len(errors) == 0
        assert len(warnings) == 0
    
    def test_process_returns_content(self):
        """测试处理返回内容"""
        processor = DefaultOutputProcessor()
        content = "测试内容"
        with tempfile.TemporaryDirectory() as tmpdir:
            result = processor.process(content, Path(tmpdir))
            assert result.content == content
            assert result.is_valid


class TestProcessedOutput:
    """处理结果测试"""
    
    def test_is_valid_property(self):
        """测试is_valid属性"""
        valid_result = ProcessedOutput(content="test", validation_errors=[])
        assert valid_result.is_valid
        
        invalid_result = ProcessedOutput(
            content="test",
            validation_errors=["错误1", "错误2"]
        )
        assert not invalid_result.is_valid


class TestAgentWithProcessor:
    """Agent与处理器集成测试"""
    
    def test_coder_agent_has_code_processor(self):
        """测试CoderAgent使用CodeOutputProcessor"""
        from src.agents.coder import CoderAgent
        from src.agents.processors import CodeOutputProcessor
        
        class MockProtocol:
            base_url = "https://mock.api"
            api_key = "mock_key"
            default_model = "mock-model"
            async def chat(self, messages, **kwargs):
                from src.core.message import ChatChunk
                yield ChatChunk(content="test")
        
        agent = CoderAgent(protocol=MockProtocol())
        assert isinstance(agent._processor, CodeOutputProcessor)
    
    def test_analyst_agent_has_requirement_processor(self):
        """测试AnalystAgent使用RequirementOutputProcessor"""
        from src.agents.analyst import AnalystAgent
        from src.agents.processors import RequirementOutputProcessor
        
        class MockProtocol:
            base_url = "https://mock.api"
            api_key = "mock_key"
            default_model = "mock-model"
        
        agent = AnalystAgent(protocol=MockProtocol())
        assert isinstance(agent._processor, RequirementOutputProcessor)
    
    def test_architect_agent_has_architecture_processor(self):
        """测试ArchitectAgent使用ArchitectureOutputProcessor"""
        from src.agents.architect import ArchitectAgent
        from src.agents.processors import ArchitectureOutputProcessor
        
        class MockProtocol:
            base_url = "https://mock.api"
            api_key = "mock_key"
            default_model = "mock-model"
        
        agent = ArchitectAgent(protocol=MockProtocol())
        assert isinstance(agent._processor, ArchitectureOutputProcessor)
    
    def test_tester_agent_has_test_processor(self):
        """测试TesterAgent使用TestOutputProcessor"""
        from src.agents.tester import TesterAgent
        from src.agents.processors import TestOutputProcessor
        
        class MockProtocol:
            base_url = "https://mock.api"
            api_key = "mock_key"
            default_model = "mock-model"
        
        agent = TesterAgent(protocol=MockProtocol())
        assert isinstance(agent._processor, TestOutputProcessor)
    
    def test_agent_info_includes_processor(self):
        """测试Agent信息包含处理器"""
        from src.agents.coder import CoderAgent
        
        class MockProtocol:
            base_url = "https://mock.api"
            api_key = "mock_key"
            default_model = "mock-model"
        
        agent = CoderAgent(protocol=MockProtocol())
        info = agent.info
        assert "processor" in info
        assert "CodeOutputProcessor" in info["processor"]
    
    def test_custom_processor_injection(self):
        """测试自定义处理器注入"""
        from src.agents.base_agent import BaseAgent
        from src.agents.processors import DefaultOutputProcessor
        
        class MockProtocol:
            base_url = "https://mock.api"
            api_key = "mock_key"
            default_model = "mock-model"
        
        custom_processor = DefaultOutputProcessor()
        agent = BaseAgent(
            name="自定义Agent",
            protocol=MockProtocol(),
            processor=custom_processor
        )
        assert agent._processor is custom_processor


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
