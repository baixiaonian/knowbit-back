# 智能体任务工具实现方案 Review

## 📋 当前实现分析

### ✅ 优点

1. **简单直接**：基础 CRUD 操作，易于理解
2. **数据持久化**：任务存储在数据库，支持查询历史
3. **用户隔离**：通过 `user_id` 确保安全
4. **状态管理**：支持任务状态跟踪

### ⚠️ 存在的问题

1. **缺少事件推送**：任务创建/更新时没有推送到前端
2. **session_id 需要手动传入**：智能体调用时需要手动传递，容易出错
3. **状态管理不够规范**：status 是自由字符串，没有约束
4. **缺少任务查询工具**：智能体无法查看当前任务列表
5. **返回值信息不足**：只返回简单字符串，缺少任务详情
6. **没有进度字段**：无法表示任务完成百分比

## 🎯 改进方案

### 方案1：轻量级改进（推荐）

**核心原则**：保持简单，只添加必要功能

#### 1.1 集成事件推送

```python
# 任务工具需要访问 EventManager
class TaskCreateTool(BaseTool):
    def __init__(self, user_id: int, event_manager: AgentEventManager, session_id: str):
        super().__init__()
        self.user_id = user_id
        self.event_manager = event_manager
        self.session_id = session_id  # 自动注入，无需手动传入
    
    async def _arun(self, description: str, priority: int = 0):
        # ... 创建任务 ...
        
        # 推送事件到前端
        await self.event_manager.publish(self.session_id, {
            "type": "task_created",
            "data": task.to_dict()
        })
        
        return f"Task#{task.id} created: {description}"
```

#### 1.2 标准化任务状态

```python
# 在 task_tools.py 中定义常量
TASK_STATUS = {
    "PENDING": "pending",
    "IN_PROGRESS": "in_progress", 
    "COMPLETED": "completed",
    "FAILED": "failed",
    "CANCELLED": "cancelled"
}
```

#### 1.3 添加任务查询工具

```python
class TaskListTool(BaseTool):
    """查询当前会话的任务列表"""
    name = "task_list"
    description = "查询当前会话的所有任务，用于了解工作进度"
    
    async def _arun(self, session_id: str, status: Optional[str] = None):
        # 查询任务列表
        # 返回格式化的任务列表
```

#### 1.4 改进返回值

```python
# 返回 JSON 格式，包含完整任务信息
return json.dumps({
    "success": True,
    "task_id": task.id,
    "description": task.description,
    "status": task.status,
    "priority": task.priority
})
```

### 方案2：增强版（可选）

如果需要更细粒度的进度管理：

#### 2.1 添加进度字段

```sql
ALTER TABLE public.agent_task 
ADD COLUMN progress INT DEFAULT 0;  -- 0-100
```

#### 2.2 添加任务结果字段

```sql
ALTER TABLE public.agent_task 
ADD COLUMN result JSONB;  -- 存储任务执行结果
```

## 🔧 具体实现建议

### 改进后的任务工具结构

```python
# app/agents/tools/task_tools.py

# 1. 定义任务状态常量
TASK_STATUS = {
    "PENDING": "pending",
    "IN_PROGRESS": "in_progress",
    "COMPLETED": "completed", 
    "FAILED": "failed"
}

# 2. TaskCreateTool - 集成事件推送
class TaskCreateTool(BaseTool):
    def __init__(self, user_id: int, event_manager: AgentEventManager, session_id: str):
        # session_id 自动注入，智能体无需手动传入
        self.session_id = session_id
        self.event_manager = event_manager
    
    async def _arun(self, description: str, priority: int = 0):
        # 创建任务
        task = AgentTask(...)
        
        # 推送事件
        await self.event_manager.publish(self.session_id, {
            "type": "task_created",
            "data": task.to_dict()
        })
        
        return json.dumps(task.to_dict())

# 3. TaskUpdateTool - 集成事件推送
class TaskUpdateTool(BaseTool):
    async def _arun(self, task_id: int, status: str):
        # 验证状态
        if status not in TASK_STATUS.values():
            return f"Invalid status. Allowed: {list(TASK_STATUS.values())}"
        
        # 更新任务
        task.status = status
        
        # 推送事件
        await self.event_manager.publish(self.session_id, {
            "type": "task_updated",
            "data": task.to_dict()
        })
        
        return json.dumps(task.to_dict())

# 4. TaskListTool - 新增查询工具
class TaskListTool(BaseTool):
    """查询当前会话的任务列表"""
    name = "task_list"
    description = "查询当前会话的所有任务，用于了解工作进度。输入 {session_id, status(可选)}"
    
    async def _arun(self, session_id: str, status: Optional[str] = None):
        # 查询任务列表
        tasks = await get_tasks_by_session(session_id, status)
        return json.dumps([task.to_dict() for task in tasks])
```

### 在 writer_agent.py 中的使用

```python
# 创建任务工具时注入 session_id 和 event_manager
tools.extend(create_task_tools(
    user_id=user_id,
    event_manager=self.event_manager,
    session_id=session_id  # 自动注入
))
```

## 📊 前端事件格式

### task_created 事件
```json
{
  "type": "task_created",
  "data": {
    "id": 1,
    "sessionId": "xxx",
    "description": "分析文档结构",
    "status": "pending",
    "priority": 1,
    "createdAt": "2024-01-01T00:00:00Z"
  }
}
```

### task_updated 事件
```json
{
  "type": "task_updated",
  "data": {
    "id": 1,
    "sessionId": "xxx",
    "description": "分析文档结构",
    "status": "in_progress",
    "priority": 1,
    "updatedAt": "2024-01-01T00:01:00Z"
  }
}
```

### task_list 事件（可选）
```json
{
  "type": "task_list",
  "data": {
    "sessionId": "xxx",
    "tasks": [
      {"id": 1, "description": "任务1", "status": "completed"},
      {"id": 2, "description": "任务2", "status": "in_progress"}
    ],
    "summary": {
      "total": 2,
      "completed": 1,
      "in_progress": 1,
      "pending": 0
    }
  }
}
```

## 🎯 推荐实施方案

### 阶段1：基础改进（立即实施）

1. ✅ 集成事件推送（TaskCreateTool, TaskUpdateTool）
2. ✅ 自动注入 session_id（无需智能体手动传入）
3. ✅ 标准化任务状态常量
4. ✅ 改进返回值格式（JSON）

### 阶段2：功能增强（可选）

1. 添加 TaskListTool（查询任务列表）
2. 添加任务进度字段（如果需要）
3. 添加任务结果字段（如果需要）

## 💡 使用示例

### 智能体工作流程

```python
# 1. 规划阶段：创建任务清单
task_create(description="分析文档结构", priority=3)
task_create(description="改写第2段", priority=2)
task_create(description="检查语法", priority=1)

# 2. 执行阶段：更新任务状态
task_update(task_id=1, status="in_progress")
# ... 执行任务 ...
task_update(task_id=1, status="completed")

# 3. 查询阶段（可选）：查看任务列表
task_list()  # 返回所有任务及其状态
```

### 前端接收事件

```javascript
// WebSocket 监听
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'task_created':
      // 添加新任务到UI
      addTaskToUI(data.data);
      break;
      
    case 'task_updated':
      // 更新任务状态
      updateTaskStatus(data.data.id, data.data.status);
      break;
  }
};
```

## ⚖️ 复杂度评估

| 方案 | 复杂度 | 收益 | 推荐度 |
|------|--------|------|--------|
| 当前实现 | ⭐ | ⭐⭐ | - |
| 方案1（轻量级） | ⭐⭐ | ⭐⭐⭐⭐ | ✅ 推荐 |
| 方案2（增强版） | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | 可选 |

## 📝 总结

**当前实现**：基础功能完整，但缺少与前端的事件集成。

**推荐改进**：
1. 集成事件推送（核心改进）
2. 自动注入 session_id（简化使用）
3. 标准化状态管理（提高可靠性）
4. 改进返回值（便于智能体处理）

**保持简单**：不添加不必要的复杂度，只在需要时扩展功能。

