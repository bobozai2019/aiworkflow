# Agent配置说明

## 配置方式

本系统支持两种Agent配置方式：

### 方式1: 代码中的SYSTEM_PROMPT（推荐，当前使用）

每个Agent类中定义了详细的SYSTEM_PROMPT，包含：
- 角色定位和职责
- 工作区域限制
- 可用工具列表和使用示例
- 工具调用格式
- 输出格式要求
- 错误分析流程（调试员）

**优点**:
- 提示词详细完整
- 包含工具使用示例
- 版本控制友好
- 易于维护和审查

**位置**:
- `src/agents/analyst.py` - 需求分析师
- `src/agents/architect.py` - 系统架构师
- `src/agents/coder.py` - 代码开发者
- `src/agents/debugger.py` - 调试员
- `src/agents/tester.py` - 测试员

### 方式2: config/agents.yaml（已废弃）

`config/agents.yaml` 中的简单提示词**不再使用**，保留仅作为参考。

**原因**:
- 提示词过于简单，缺少必要的细节
- 没有工具使用说明
- 没有权限限制说明
- 与实际使用的提示词不一致

## 当前配置

所有Agent使用代码中定义的SYSTEM_PROMPT，在Agent初始化时设置：

```python
class AnalystAgent(BaseAgent):
    DEFAULT_SYSTEM_PROMPT = SYSTEM_PROMPT  # 详细的提示词

    def __init__(self, protocol, system_prompt=None, ...):
        super().__init__(
            name="需求分析师",
            protocol=protocol,
            system_prompt=system_prompt or SYSTEM_PROMPT,  # 使用代码中的提示词
            ...
        )
```

## 自定义提示词

如果需要自定义Agent的提示词，可以在创建Agent时传入：

```python
custom_prompt = """
你是一位专业的需求分析师...
[自定义内容]
"""

analyst = AnalystAgent(
    protocol=protocol,
    system_prompt=custom_prompt  # 覆盖默认提示词
)
```

## 占位符替换

提示词中使用的占位符会在运行时替换：

- `{WORK_DIR}` - 在 `set_work_dir()` 中替换为实际工作目录
- `{OUTPUT_DIR}` - 在 `update_prompt_output_dir()` 中替换为输出目录

## 提示词版本

当前提示词版本: v2.0 (2026-03-27)

**更新内容**:
- 添加了 code_execute 和 test_run 工具说明
- 改进了工具使用示例
- 明确了文件类型限制（需求分析师）
- 改进了错误提示信息
- 统一了多行参数格式说明

## 未来改进

考虑实现配置文件覆盖机制：

```python
# 从yaml加载基础配置
base_config = load_yaml("config/agents.yaml")

# 从代码加载详细提示词
detailed_prompt = AnalystAgent.DEFAULT_SYSTEM_PROMPT

# 合并配置
final_config = merge_config(base_config, detailed_prompt)
```

但目前直接使用代码中的SYSTEM_PROMPT更简单、更可靠。
