"""
文件工具模块测试
"""

import pytest
import tempfile
from pathlib import Path

from src.utils.file_tool import FileTool, CodeBlock


class TestCodeBlock:
    """代码块数据结构测试"""
    
    def test_init(self):
        """测试初始化"""
        block = CodeBlock(
            language="python",
            filename="test.py",
            content="print('hello')"
        )
        assert block.language == "python"
        assert block.filename == "test.py"
        assert block.content == "print('hello')"
    
    def test_optional_filename(self):
        """测试可选文件名"""
        block = CodeBlock(
            language="python",
            filename=None,
            content="print('hello')"
        )
        assert block.filename is None


class TestFileTool:
    """文件工具测试"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)
    
    @pytest.fixture
    def file_tool(self, temp_dir):
        """创建文件工具实例"""
        return FileTool(temp_dir)
    
    def test_init(self, temp_dir):
        """测试初始化"""
        tool = FileTool(temp_dir)
        assert tool.output_dir == temp_dir
        assert tool.output_dir.exists()
    
    def test_parse_simple_code_block(self, file_tool):
        """测试解析简单代码块"""
        content = """
这是一些文本
```python
print('hello')
```
其他内容
"""
        blocks = file_tool.parse_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].language == "python"
        assert "print('hello')" in blocks[0].content
    
    def test_parse_code_block_with_filename(self, file_tool):
        """测试解析带文件名的代码块"""
        content = """
```python file: main.py
def main():
    print('hello')
```
"""
        blocks = file_tool.parse_code_blocks(content)
        assert len(blocks) == 1
        assert blocks[0].language == "python"
        assert blocks[0].filename == "main.py"
    
    def test_parse_multiple_code_blocks(self, file_tool):
        """测试解析多个代码块"""
        content = """
```python file: a.py
print('a')
```

```javascript file: b.js
console.log('b');
```
"""
        blocks = file_tool.parse_code_blocks(content)
        assert len(blocks) == 2
        assert blocks[0].language == "python"
        assert blocks[0].filename == "a.py"
        assert blocks[1].language == "javascript"
        assert blocks[1].filename == "b.js"
    
    def test_parse_no_code_blocks(self, file_tool):
        """测试无代码块"""
        content = "这是一段普通文本，没有代码块。"
        blocks = file_tool.parse_code_blocks(content)
        assert len(blocks) == 0
    
    def test_guess_filename_python(self, file_tool):
        """测试猜测Python文件名"""
        filename = file_tool._guess_filename("some content", "python")
        assert filename == "output.py"
    
    def test_guess_filename_javascript(self, file_tool):
        """测试猜测JavaScript文件名"""
        filename = file_tool._guess_filename("some content", "javascript")
        assert filename == "output.js"
    
    def test_guess_filename_unknown(self, file_tool):
        """测试猜测未知语言文件名"""
        filename = file_tool._guess_filename("some content", "unknownlang")
        assert filename == "output.unknownlang"
    
    def test_save_code_block(self, file_tool, temp_dir):
        """测试保存代码块"""
        block = CodeBlock(
            language="python",
            filename="test.py",
            content="print('hello')"
        )
        
        path = file_tool.save_code_block(block)
        assert path is not None
        assert path.exists()
        assert path.name == "test.py"
        assert path.read_text(encoding='utf-8') == "print('hello')"
    
    def test_save_code_block_with_subdir(self, file_tool, temp_dir):
        """测试保存代码块到子目录"""
        block = CodeBlock(
            language="python",
            filename="test.py",
            content="print('hello')"
        )
        
        path = file_tool.save_code_block(block, sub_dir="subfolder")
        assert path is not None
        assert path.exists()
        assert "subfolder" in str(path)
    
    def test_save_code_block_no_filename(self, file_tool):
        """测试保存无文件名的代码块"""
        block = CodeBlock(
            language="python",
            filename=None,
            content="print('hello')"
        )
        
        path = file_tool.save_code_block(block)
        assert path is None
    
    def test_process_content(self, file_tool, temp_dir):
        """测试处理内容"""
        content = """
```python file: main.py
print('hello')
```
"""
        result_content, saved_paths = file_tool.process_content(content)
        assert result_content == content
        assert len(saved_paths) == 1
        assert saved_paths[0].name == "main.py"
    
    def test_process_content_multiple(self, file_tool, temp_dir):
        """测试处理多个代码块"""
        content = """
```python file: a.py
print('a')
```
```javascript file: b.js
console.log('b');
```
"""
        result_content, saved_paths = file_tool.process_content(content)
        assert len(saved_paths) == 2
        names = [p.name for p in saved_paths]
        assert "a.py" in names
        assert "b.js" in names
