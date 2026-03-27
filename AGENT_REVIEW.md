# Agent提示词和权限审查报告

## 🔴 发现的严重问题

### 1. **配置文件与实际代码不一致**

**问题**: `config/agents.yaml` 中的提示词与实际Agent代码中的提示词完全不同

**影响**:
- `agents.yaml` 中的简单提示词没有被使用
- 实际使用的是各Agent类中定义的详细SYSTEM_PROMPT
- 配置文件形同虚设，造成混淆

**证据**:
```yaml
# config/agents.yaml - 简单版本（未被使用）
analyst:
  system_prompt: |
    你是一位专业的需求分析师。你的职责是：
    1. 分析用户需求，提取关键信息
    ...
```

```python
# src/agents/analyst.py - 实际使用的版本
SYSTEM_PROMPT = """你是一位专业的需求分析师。你的职责是与用户进行对话...

## 角色定位
你是**需求分析师**，专注于业务需求分析，**只关注"做什么"，不关心"怎么做"**。

### 你要做的事情：
- 理解用户的业务需求和目标
...

## 工作区域限制
你的工作区域被严格限制在以下范围内：
**工作目录**: {WORK_DIR}/requirements/
...

## 可用工具
1. **file_read** - 读取文件内容
2. **file_list** - 列出目录下的文件
...
"""
```

**建议**:
- 删除或废弃 `config/agents.yaml`
- 统一使用代码中的SYSTEM_PROMPT
- 或者实现配置文件覆盖机制

---

### 2. **需求分析师提示词存在矛盾**

**问题**: 提示词中既说"不要讨论代码"，又提供了代码文件读取能力

**矛盾点**:
```python
# analyst.py:31-36
### 你**绝对不要**做的事情：
- ❌ 写代码、改代码、看代码
- ❌ 讨论技术实现细节（如"调用哪个py文件"、"用什么框架"、"如何实现"）
- ❌ 关心技术实现方案
- ❌ 读取代码文件
- ❌ 在沟通过程中讨论代码相关内容
```

但是：
```python
# analyst.py:65-68
1. **file_read** - 读取文件内容
   参数: file_path (文件路径，必须是 requirements/ 目录下的文件)
   用途: 读取需求文档
```

**实际代码中的保护**:
```python
# analyst.py:209-226
if name == "file_read" and "file_path" in params:
    file_path = Path(params["file_path"])
    ext = file_path.suffix.lower()

    if ext in self.CODE_EXTENSIONS:
        logger.warning(f"[{self.name}] ⛔ 拒绝读取代码文件: {ext}")
        results.append({
            "name": name,
            "result": f"作为需求分析师，不应该读取代码文件（{ext}）。请专注于文档文件（如 .md, .txt, .json）。"
        })
        continue
```

**评价**:
- ✅ 代码层面有保护（拒绝读取.py等代码文件）
- ⚠️ 提示词表述不够精确，应该说"不要读取代码文件"而非"不要读取文件"

---

### 3. **权限配置与提示词不完全匹配**

#### 需求分析师
**提示词说**: 只能访问 `requirements/` 目录
**权限配置**: ✅ 正确
```python
"需求分析师": AgentPermission(
    directories=[
        DirectoryPermission(
            directory="requirements",
            permission=Permission.READ_WRITE
        )
    ]
)
```

#### 系统架构师
**提示词说**:
- 可以读取 `requirements/` 目录
- 可以在 `code/` 目录读写架构文档
- 禁止访问 `tests/` 目录

**权限配置**: ✅ 正确
```python
"系统架构师": AgentPermission(
    directories=[
        DirectoryPermission(directory="requirements", permission=Permission.READ),
        DirectoryPermission(directory="code", permission=Permission.READ_WRITE)
    ]
)
```

#### 代码开发者
**提示词说**:
- 可以读取 `requirements/` 目录
- 可以在 `code/` 目录读写代码
- 禁止访问 `tests/` 目录

**权限配置**: ✅ 正确
```python
"代码开发者": AgentPermission(
    directories=[
        DirectoryPermission(directory="requirements", permission=Permission.READ),
        DirectoryPermission(directory="code", permission=Permission.READ_WRITE)
    ]
)
```

#### 调试员
**提示词说**:
- 可以读取 `requirements/` 目录
- 可以读取和修改 `code/` 目录
- 可以读取 `tests/` 目录

**权限配置**: ✅ 正确
```python
"调试员": AgentPermission(
    directories=[
        DirectoryPermission(directory="requirements", permission=Permission.READ),
        DirectoryPermission(directory="code", permission=Permission.READ_WRITE),
        DirectoryPermission(directory="tests", permission=Permission.READ)
    ]
)
```

#### 测试员
**提示词说**:
- 可以读取整个项目根目录
- 可以读取 `requirements/` 和 `code/` 目录
- 可以在 `tests/` 目录读写测试文件

**权限配置**: ✅ 正确
```python
"测试员": AgentPermission(
    directories=[
        DirectoryPermission(directory=".", permission=Permission.READ),
        DirectoryPermission(directory="requirements", permission=Permission.READ),
        DirectoryPermission(directory="code", permission=Permission.READ),
        DirectoryPermission(directory="tests", permission=Permission.READ_WRITE)
    ]
)
```

---

### 4. **工具列表不完整**

**问题**: 提示词中列出的工具与实际注册的工具不一致

**提示词中列出的工具**:
- file_read
- file_list
- file_search (部分Agent)
- file_write
- web_search (部分Agent)
- web_fetch (部分Agent)

**实际注册的工具** (src/tools/base.py):
```python
def register_default_tools() -> None:
    ToolRegistry.register(FileReadTool())
    ToolRegistry.register(FileListTool())
    ToolRegistry.register(FileSearchTool())
    ToolRegistry.register(FileWriteTool())
    ToolRegistry.register(WebSearchTool())
    ToolRegistry.register(WebFetchTool())
```

**新增的执行工具** (src/tools/executor.py):
```python
def register_executor_tools() -> None:
    ToolRegistry.register(CodeExecutorTool())
    ToolRegistry.register(TestRunnerTool())
```

**问题**:
- ❌ 调试员和测试员的提示词中没有提到 `code_execute` 和 `test_run` 工具
- ❌ 这两个工具对于验证代码和测试至关重要

---

### 5. **提示词格式不统一**

**问题**: 不同Agent的提示词结构和详细程度差异很大

**需求分析师**: 非常详细（280行）
- ✅ 明确的角色定位
- ✅ 详细的工作区域限制
- ✅ 完整的工具说明
- ✅ 工具调用格式示例
- ✅ 输出格式要求

**系统架构师**: 较详细（133行）
- ✅ 角色定位
- ✅ 工作区域限制
- ✅ 工具说明
- ✅ 输出格式

**代码开发者**: 较详细（159行）
- ✅ 角色定位
- ✅ 工作区域限制
- ✅ 工具说明
- ✅ 输出格式

**调试员**: 详细（280行）
- ✅ 角色定位
- ✅ 错误分析流程
- ✅ 工具说明
- ✅ 输出格式
- ❌ 缺少 code_execute 工具说明

**测试员**: 较详细（184行）
- ✅ 角色定位
- ✅ 工作区域限制
- ✅ 工具说明
- ✅ 输出格式
- ❌ 缺少 test_run 工具说明

---

### 6. **工具调用格式不一致**

**问题**: 提示词中的工具调用格式与实际解析逻辑不完全匹配

**提示词中的格式**:
```
<tool>
名称: 工具名称
参数:
  参数名: 参数值
</tool>
```

**实际解析代码** (base_agent.py:116-173):
```python
def parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
    pattern = r'<tool>\s*名称:\s*(\w+)\s*参数:\s*([^<]*?)\s*</tool>'
    matches = re.findall(pattern, content, re.DOTALL)
    ...
```

**评价**: ✅ 格式匹配，但提示词中应该强调：
- 参数值如果是多行，需要使用特定格式（如 `|-`）
- 参数名必须与工具定义的参数名完全匹配

---

## 🟡 次要问题

### 7. **提示词中的占位符替换**

**问题**: 提示词中使用了多个占位符，但替换逻辑分散

**占位符**:
- `{WORK_DIR}` - 在 `set_work_dir()` 中替换
- `{OUTPUT_DIR}` - 在 `update_prompt_output_dir()` 中替换

**问题**:
- 不同Agent使用不同的占位符
- 替换时机不统一
- 容易遗漏替换

**建议**: 统一占位符和替换机制

---

### 8. **缺少工具使用示例**

**问题**: 提示词中只说明了工具的参数，但没有给出具体使用示例

**当前**:
```
1. **file_read** - 读取文件内容
   参数: file_path (文件路径)
   用途: 读取需求文档
```

**建议**:
```
1. **file_read** - 读取文件内容
   参数: file_path (文件路径)
   用途: 读取需求文档

   示例:
   <tool>
   名称: file_read
   参数:
     file_path: requirements/requirements.md
   </tool>
```

---

### 9. **权限错误提示不够友好**

**问题**: 当Agent尝试访问无权限的文件时，错误信息不够清晰

**当前** (tools/base.py:182-186):
```python
return ToolResult(
    success=False,
    content="",
    error=f"权限拒绝: {agent_name} 没有读取 {file_path} 的权限\n允许访问的目录:\n{allowed_info}"
)
```

**建议**: 添加更多上下文信息
```python
error=f"""权限拒绝: {agent_name} 没有读取 {file_path} 的权限

原因: 该文件不在你的工作区域内

你可以访问的目录:
{allowed_info}

提示: 请检查文件路径是否正确，或者该文件是否应该由其他Agent处理。
"""
```

---

## ✅ 做得好的地方

### 1. **权限隔离设计合理**
- ✅ 每个Agent只能访问其职责范围内的目录
- ✅ 使用最小权限原则
- ✅ 读写权限分离

### 2. **提示词结构清晰**
- ✅ 明确的角色定位
- ✅ 清晰的工作流程
- ✅ 详细的约束说明

### 3. **代码层面的保护**
- ✅ 需求分析师拒绝读取代码文件
- ✅ 权限检查在工具执行前进行
- ✅ 详细的日志记录

### 4. **工具调用格式统一**
- ✅ 所有Agent使用相同的工具调用格式
- ✅ 解析逻辑健壮

---

## 📋 改进建议优先级

### P0 - 必须修复

1. **更新调试员和测试员的提示词**
   - 添加 `code_execute` 工具说明
   - 添加 `test_run` 工具说明
   - 说明这些工具的使用场景

2. **修正需求分析师提示词**
   - 将"不要读取文件"改为"不要读取代码文件"
   - 明确说明可以读取 .md, .txt, .json 等文档文件

3. **统一配置管理**
   - 决定是使用 `agents.yaml` 还是代码中的SYSTEM_PROMPT
   - 如果使用yaml，实现配置覆盖机制
   - 如果不使用yaml，删除或标记为废弃

### P1 - 重要改进

4. **添加工具使用示例**
   - 在每个工具说明后添加具体使用示例
   - 特别是多行参数的格式

5. **改进错误提示**
   - 权限错误提示更友好
   - 工具调用失败时给出更多上下文

6. **统一占位符机制**
   - 使用统一的占位符命名
   - 在Agent初始化时统一替换

### P2 - 优化体验

7. **提示词模板化**
   - 提取公共部分（如工具调用格式）
   - 使用模板生成提示词

8. **添加提示词版本控制**
   - 在提示词中添加版本号
   - 便于追踪和回滚

---

## 🔧 具体修复方案

### 修复1: 更新调试员提示词

在 `src/agents/debugger.py` 的 SYSTEM_PROMPT 中添加：

```python
5. **code_execute** - 执行Python代码
   参数: file_path (文件路径), timeout (超时时间，默认30秒)
   用途: 验证修复后的代码是否能正常运行

   示例:
   <tool>
   名称: code_execute
   参数:
     file_path: code/main.py
     timeout: 30
   </tool>
```

### 修复2: 更新测试员提示词

在 `src/agents/tester.py` 的 SYSTEM_PROMPT 中添加：

```python
5. **test_run** - 执行测试用例
   参数: test_path (测试路径), verbose (是否详细输出), timeout (超时时间)
   用途: 运行pytest测试并获取测试报告

   示例:
   <tool>
   名称: test_run
   参数:
     test_path: tests
     verbose: true
     timeout: 60
   </tool>
```

### 修复3: 修正需求分析师提示词

将：
```python
- ❌ 读取代码文件
```

改为：
```python
- ❌ 读取代码文件（.py, .js, .java等）
- ✅ 可以读取文档文件（.md, .txt, .json等）
```

---

## 📊 总结

### 严重问题: 3个
1. 配置文件与代码不一致
2. 调试员/测试员缺少执行工具说明
3. 需求分析师提示词表述不精确

### 次要问题: 6个
4. 提示词格式不统一
5. 缺少工具使用示例
6. 占位符替换机制分散
7. 错误提示不够友好
8. 工具列表不完整
9. 缺少版本控制

### 优点: 4个
- 权限隔离设计合理
- 提示词结构清晰
- 代码层面有保护
- 工具调用格式统一

### 建议
优先修复P0级别的3个问题，特别是添加执行工具的说明，这对于新实现的反馈循环系统至关重要。
