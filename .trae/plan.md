# 解决发送消息卡顿问题

## 问题分析

### 当前问题代码位置
- `src/ui/main_window.py` 第609-617行 `_send_workflow_message` 方法
- `src/ui/main_window.py` 第603-607行 `_run_workflow` 方法中的 `start_session`

### 问题原因
```python
def _send_workflow_message(self, message: str) -> None:
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(self._workflow_machine.send_message(message))  # 阻塞UI线程！
    loop.close()
```

`loop.run_until_complete()` 会阻塞当前线程（主UI线程），直到HTTP请求完成才返回。这导致：
1. 点击发送按钮后界面立即冻结
2. 直到收到API响应才恢复响应
3. 用户感觉应用"卡死"

## 解决方案

### 方案：利用工作线程执行异步操作

已有的 `WorkflowConversationWorker` 线程运行着一个事件循环，我们可以：
1. 将消息发送任务提交到工作线程的事件循环
2. 主线程立即返回，不等待结果
3. 结果通过信号返回到主线程更新UI

### 实现步骤

#### 步骤1：修改 WorkflowConversationWorker
- 添加消息队列或方法来接收待发送的消息
- 在事件循环中执行消息发送

#### 步骤2：修改 _send_workflow_message
- 使用 `asyncio.run_coroutine_threadsafe()` 将协程提交到工作线程
- 主线程立即返回，不阻塞

#### 步骤3：优化用户反馈
- 发送后立即显示用户消息
- 显示"发送中..."状态
- 响应到达后更新状态

## 详细实现计划

### 1. 修改 WorkflowConversationWorker 类
```python
class WorkflowConversationWorker(QThread):
    # 新增信号
    send_message_requested = pyqtSignal(str)
    
    def __init__(self, machine, parent=None):
        super().__init__(parent)
        self._machine = machine
        self._loop = None
        self._message_queue = asyncio.Queue()
        
    def run(self):
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        # 启动消息处理任务
        self._loop.create_task(self._process_messages())
        
        # 运行事件循环
        self._loop.run_forever()
    
    async def _process_messages(self):
        """处理消息队列"""
        while True:
            message = await self._message_queue.get()
            await self._machine.send_message(message)
    
    def send_message(self, message: str):
        """从主线程调用，将消息放入队列"""
        if self._loop:
            asyncio.run_coroutine_threadsafe(
                self._message_queue.put(message),
                self._loop
            )
```

### 2. 修改 MainWindow._send_workflow_message
```python
def _send_workflow_message(self, message: str) -> None:
    if not self._workflow_machine or not self._conversation_worker:
        return
    
    # 立即显示用户消息
    self.chat_panel.add_message("user", message)
    self.chat_panel.set_status("发送中...")
    
    # 提交到工作线程，不阻塞
    self._conversation_worker.send_message(message)
```

### 3. 修改 _run_workflow 中的 start_session
同样使用工作线程执行，不阻塞主线程。

## 文件修改清单

1. **src/ui/main_window.py**
   - 修改 `WorkflowConversationWorker` 类
   - 修改 `_send_workflow_message` 方法
   - 修改 `_run_workflow` 方法中的启动逻辑

## 预期效果

- 点击发送后界面立即响应
- 用户消息立即显示
- API请求在后台执行
- 响应通过信号返回更新UI
- 无卡顿感
