# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Multi-agent system supporting Chinese LLMs (DeepSeek, Qwen, GLM, MiniMax) with workflow orchestration, PyQt GUI, and mobile API support. The system coordinates multiple specialized agents (Analyst, Architect, Coder, Tester) to complete software development tasks.

## Essential Commands

### Running the Application
```bash
# CLI mode
python -m src.cli "实现一个用户登录功能"

# GUI mode
python -m src.main
```

### Testing (CRITICAL - Read TDD section below)
```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_workflow.py -v

# Run with coverage report
pytest tests/ -v --cov=src --cov-report=html

# Run single test
pytest tests/test_agents.py::TestAnalyst::test_execute -v
```

### Code Quality
```bash
# Linting (configured in pyproject.toml)
ruff check src/

# Type checking
mypy src/
```

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with API keys: DEEPSEEK_API_KEY, QWEN_API_KEY, etc.
```

## Architecture Overview

### Layered Architecture (Strict Dependency Rules)

```
┌─────────────────────────────────────────┐
│         UI Layer (PyQt/API)             │  ← User interaction
├─────────────────────────────────────────┤
│         Workflow Engine                 │  ← Task orchestration
├─────────────────────────────────────────┤
│    Agent Layer (Analyst/Coder/...)     │  ← Role execution
├─────────────────────────────────────────┤
│    Protocol Layer (DeepSeek/Qwen/...)  │  ← LLM API adapters
├─────────────────────────────────────────┤
│    Communication Layer (HTTP/WS)       │  ← Network primitives
└─────────────────────────────────────────┘
```

**Critical Rule**: Upper layers can depend on lower layers, but NEVER the reverse. Same-layer modules should be decoupled.

### Module Dependency Matrix

| Module | Can Depend On | Cannot Depend On |
|--------|---------------|------------------|
| ui | core, agents, utils | protocols, communication |
| core | utils | agents, protocols |
| agents | core, protocols, utils | ui, api |
| protocols | communication, utils | agents, core, ui |
| communication | utils | all business modules |
| api | core, agents | ui |

### Agent Workflow

Default workflow: `User Request → Analyst → Coder → Complete`

Agents communicate via `Context` object that stores intermediate results. Each agent:
1. Receives task + context from previous agent
2. Calls protocol layer for LLM streaming response
3. Returns `TaskResult` with success/content/duration/error
4. Updates context for next agent

### Protocol Layer

All LLM providers implement `BaseProtocol.chat()` interface with async streaming. Protocol configurations live in `config/protocols.yaml` and reference environment variables for API keys.

## TDD Requirements (MANDATORY)

**All code changes MUST follow test-driven development**:

1. **Before modifying code**: Check if `tests/test_*.py` exists for the module
2. **If no test exists**: Write test cases first
3. **If interface changes**: Update test interfaces accordingly
4. **Run tests**: Confirm baseline state before changes
5. **Make changes**: Implement the modification
6. **Run tests again**: All tests must pass before task is complete

**Coverage Requirements**:
- Core business logic: >80%
- Utility functions: >60%
- Config/initialization: >40%

**Test file naming**: `tests/test_{module}.py` (e.g., `test_agents.py`, `test_workflow.py`)

## Critical Conventions

### Configuration Management

- **Never hardcode API keys** - use environment variables in `.env`
- Config files: `config.yaml` (app settings), `agents.yaml` (agent roles), `protocols.yaml` (LLM providers)
- Load via `Config.load()` which auto-loads all configs

### Data Structures

```python
# Core message format
@dataclass
class Message:
    role: str        # "system" | "user" | "assistant"
    content: str
    metadata: dict

# Task result format
@dataclass
class TaskResult:
    success: bool
    content: str
    agent_id: str
    duration: float
    error: Optional[str]
```

### Context Passing Between Agents

```python
# Agents share data via Context
context.set(agent.name, result)           # Store result
context.get_previous_result()             # Get previous agent output
```

**Never modify another agent's data in Context**.

### Error Handling Hierarchy

```
AgentError (base)
├── ProtocolError    # API call failures
├── WorkflowError    # Orchestration errors
└── ConfigError      # Configuration issues
```

Protocol errors propagate up and get wrapped by agent layer into `TaskResult(success=False)`.

### Async/Streaming Architecture

All agent execution is async with streaming responses:

```python
async for chunk in self.protocol.chat(messages, stream=True):
    self.on_chunk(chunk)  # Real-time output
```

Never block async operations.

### Code Style

- Use Chinese comments in code
- Follow PEP 8 (enforced by ruff with 100 char line length)
- Type annotations required (Python 3.10+ syntax)
- Commit messages: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`

## Extending the System

### Adding a New Protocol

1. Create `src/protocols/{name}.py` inheriting `BaseProtocol`
2. Implement `async def chat(messages, stream) -> AsyncIterator[str]`
3. Add config to `config/protocols.yaml`
4. Register in `src/protocols/__init__.py` factory

### Adding a New Agent

1. Create `src/agents/{name}.py` inheriting `BaseAgent`
2. Define system prompt and role-specific logic
3. Add config to `config/agents.yaml` with protocol reference
4. Agent output should include: summary, details, suggestions

### Modifying Workflow

Edit `src/core/workflow.py` to change agent sequence, add conditional branching, or enable parallel execution.

## Prohibited Actions

- ❌ Cross-layer direct calls (e.g., UI → Protocol)
- ❌ Using httpx directly in agents (must go through Protocol layer)
- ❌ Hardcoding API keys anywhere
- ❌ Modifying other agents' Context data
- ❌ Blocking async operations
- ❌ Committing code without passing tests

## Project Status

Currently in MVP development phase. See `plan.md` for roadmap.
