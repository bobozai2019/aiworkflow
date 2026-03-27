# 代码执行与反馈循环系统

## 概述

本系统实现了完整的代码执行验证和自动错误修复能力，让多Agent系统能够真正完成从需求到可运行代码的完整流程。

## 核心功能

### 1. 代码执行工具 (CodeExecutorTool)

在隔离环境中执行Python代码，捕获输出和错误。

**功能**：
- 执行Python文件并返回stdout/stderr
- 捕获退出码判断执行成功/失败
- 支持超时控制（默认30秒）
- 支持命令行参数传递

**使用示例**：
```python
from src.tools.executor import CodeExecutorTool

tool = CodeExecutorTool()
result = tool.execute(
    file_path="code/main.py",
    timeout=30,
    args=""
)

if result.success:
    print(f"执行成功: {result.content}")
else:
    print(f"执行失败: {result.error}")
```

### 2. 测试运行工具 (TestRunnerTool)

执行pytest测试并返回详细报告。

**功能**：
- 执行pytest测试用例
- 解析测试结果（通过/失败/错误/跳过）
- 返回测试覆盖率统计
- 支持详细输出模式

**使用示例**：
```python
from src.tools.executor import TestRunnerTool

tool = TestRunnerTool()
result = tool.execute(
    test_path="tests",
    verbose=True,
    timeout=60
)

print(f"测试统计: {result.metadata}")
# {'passed': 5, 'failed': 0, 'errors': 0, 'skipped': 0, 'total': 5}
```

### 3. 调试员Agent (DebuggerAgent)

分析代码执行错误并自动修复。

**功能**：
- 分析语法错误、运行时错误、测试失败
- 定位问题根源
- 生成修复方案
- 使用工具自动修复代码

**工作流程**：
1. 接收错误信息和堆栈跟踪
2. 读取相关代码文件
3. 分析错误原因
4. 生成修复后的代码
5. 使用file_write工具保存修复

### 4. 带反馈循环的工作流 (WorkflowWithFeedback)

支持代码执行验证和自动重试的完整工作流。

**流程**：
```
需求分析 → 架构设计 → 代码开发
    ↓
代码执行验证
    ↓ (失败)
调试修复 → 重新执行 (最多3次)
    ↓ (成功)
测试用例开发
    ↓
测试执行验证
    ↓ (失败)
调试修复 → 重新测试 (最多3次)
    ↓ (成功)
完成 ✅
```

## 使用方法

### 基础用法

```python
from src.core.workflow_with_feedback import WorkflowWithFeedback
from src.agents import ArchitectAgent, CoderAgent, DebuggerAgent, TesterAgent
from src.protocols.deepseek import DeepSeekProtocol

# 创建协议
protocol = DeepSeekProtocol(
    api_key="your-api-key",
    base_url="https://api.deepseek.com",
    default_model="deepseek-chat"
)

# 创建工作流
workflow = WorkflowWithFeedback(
    base_output_dir=Path("./output"),
    max_retry_per_stage=3  # 每个阶段最多重试3次
)

# 添加Agent
workflow.add_agent(ArchitectAgent(protocol=protocol))
workflow.add_agent(CoderAgent(protocol=protocol))
workflow.add_agent(DebuggerAgent(protocol=protocol))
workflow.add_agent(TesterAgent(protocol=protocol))

# 执行任务
result = await workflow.run("实现一个计算器模块")

if result.success:
    print(f"✅ 项目完成: {result.saved_files[0]}")
else:
    print(f"❌ 失败: {result.error}")
```

### 配置选项

```python
workflow = WorkflowWithFeedback(
    base_output_dir=Path("./output"),      # 输出目录
    use_existing_project=False,            # 是否使用现有项目
    max_retry_per_stage=3                  # 每阶段最大重试次数
)
```

### 进度监控

```python
def on_progress(agent_name: str, status: str, progress: float):
    if status == "start":
        print(f"[{agent_name}] 开始工作...")
    elif status == "complete":
        print(f"[{agent_name}] 完成! 进度: {progress:.0f}%")
    elif status == "failed":
        print(f"[{agent_name}] 失败!")

workflow.on_progress = on_progress
```

## 执行统计

工作流会自动收集执行统计信息：

```python
stats = workflow._execution_stats
print(f"代码执行次数: {stats['code_executions']}")
print(f"测试运行次数: {stats['test_runs']}")
print(f"调试尝试次数: {stats['debug_attempts']}")
print(f"总重试次数: {stats['total_retries']}")
```

## 权限配置

调试员Agent的权限配置：

| 目录 | 权限 | 说明 |
|------|------|------|
| requirements/ | 只读 | 可读取需求文档 |
| code/ | 读写 | 可修复代码 |
| tests/ | 只读 | 可读取测试用例 |

## 错误处理

### 语法错误
- 自动检测括号、引号、缩进问题
- 直接修复语法错误

### 导入错误
- 检查模块名和文件路径
- 建议安装缺失依赖

### 运行时错误
- 分析错误堆栈
- 定位出错代码行
- 修复逻辑错误

### 测试失败
- 对比实际输出和预期输出
- 修复代码逻辑使其符合预期

## 示例

完整示例请参考：
- `examples/workflow_feedback_example.py` - 基础使用示例
- `tests/test_workflow_feedback.py` - 单元测试

## 运行测试

```bash
# 测试代码执行工具
pytest tests/test_workflow_feedback.py::test_code_executor_tool -v

# 测试测试运行工具
pytest tests/test_workflow_feedback.py::test_test_runner_tool -v

# 测试完整工作流
pytest tests/test_workflow_feedback.py::test_workflow_with_feedback_simple -v

# 测试错误修复场景
pytest tests/test_workflow_feedback.py::test_workflow_with_feedback_with_error -v
```

## 架构优势

### 1. 闭环验证
- 代码生成后立即执行验证
- 测试用例生成后立即运行测试
- 形成完整的开发-验证闭环

### 2. 自动修复
- 调试员自动分析错误
- 自动生成修复方案
- 自动应用修复并重新验证

### 3. 可配置重试
- 每个阶段独立配置重试次数
- 避免无限循环
- 提供清晰的失败信息

### 4. 详细统计
- 记录所有执行和重试
- 便于分析系统性能
- 优化Agent行为

## 与原有Workflow的对比

| 特性 | 原有Workflow | WorkflowWithFeedback |
|------|-------------|---------------------|
| 代码执行 | ❌ 不支持 | ✅ 支持 |
| 测试执行 | ❌ 不支持 | ✅ 支持 |
| 错误修复 | ❌ 不支持 | ✅ 自动修复 |
| 反馈循环 | ❌ 单向流程 | ✅ 迭代重试 |
| 验证能力 | ❌ 无法验证 | ✅ 完整验证 |
| 可用性 | 🟡 需手动验证 | ✅ 自动化完成 |

## 未来改进

- [ ] 支持更多编程语言（JavaScript, Java, Go等）
- [ ] 集成代码质量检查（linter, type checker）
- [ ] 支持依赖自动安装
- [ ] 支持Docker沙箱隔离
- [ ] 添加性能分析工具
- [ ] 支持并行测试执行
- [ ] 集成代码覆盖率报告

## 注意事项

1. **安全性**：代码执行在当前Python环境中，建议在虚拟环境或容器中运行
2. **超时设置**：根据项目复杂度调整超时时间
3. **重试次数**：避免设置过大的重试次数，防止无限循环
4. **依赖管理**：确保测试环境已安装pytest和其他必要依赖

## 贡献

欢迎提交Issue和Pull Request来改进这个系统！
