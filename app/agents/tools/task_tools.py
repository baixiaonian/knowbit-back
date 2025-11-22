"""
任务管理工具（内存存储版本）
"""
import json
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool

from app.agents.event_manager import AgentEventManager
from app.agents.tools.task_storage import task_storage, TASK_STATUS

ALLOWED_STATUSES = list(TASK_STATUS.values())


class CreateTaskInput(BaseModel):
    description: str = Field(..., description="任务描述")
    priority: int = Field(0, description="任务优先级，数字越大优先级越高")


class UpdateTaskInput(BaseModel):
    task_id: int = Field(..., description="任务ID")
    status: str = Field(..., description=f"任务状态，可选值: {', '.join(ALLOWED_STATUSES)}")


class ListTasksInput(BaseModel):
    status: Optional[str] = Field(None, description=f"过滤状态（可选），可选值: {', '.join(ALLOWED_STATUSES)}")


class TaskCreateTool(BaseTool):
    name = "task_create"
    description = (
        "创建新的写作任务项，用于记录规划阶段的任务清单。"
        "使用此工具时，需要提供description（任务描述）和priority（优先级，可选，默认0）。"
        "任务会自动关联到当前会话。"
    )
    args_schema = CreateTaskInput

    def __init__(self, user_id: int, event_manager: AgentEventManager, session_id: str):
        super().__init__()
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'event_manager', event_manager)
        object.__setattr__(self, 'session_id', session_id)

    async def _arun(self, description: str, priority: int = 0):
        # 使用内存存储创建任务
        task = task_storage.create_task(
            session_id=self.session_id,
            user_id=self.user_id,
            description=description,
            priority=priority
        )
        
        # 推送事件到前端
        await self.event_manager.publish(self.session_id, {
            "type": "task_created",
            "data": task.to_dict()
        })
        
        return json.dumps({
            "success": True,
            "message": f"Task#{task.id} created",
            "task": task.to_dict()
        }, ensure_ascii=False)

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


class TaskUpdateTool(BaseTool):
    name = "task_update"
    description = (
        f"更新任务状态，以跟踪智能体的执行进度。"
        f"使用此工具时，需要提供task_id（任务ID）和status（状态）。"
        f"状态可选值: {', '.join(ALLOWED_STATUSES)}"
    )
    args_schema = UpdateTaskInput

    def __init__(self, user_id: int, event_manager: AgentEventManager, session_id: str):
        super().__init__()
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'event_manager', event_manager)
        object.__setattr__(self, 'session_id', session_id)

    async def _arun(self, task_id: int, status: str):
        # 验证状态
        if status not in ALLOWED_STATUSES:
            return json.dumps({
                "success": False,
                "error": f"Invalid status '{status}'. Allowed values: {', '.join(ALLOWED_STATUSES)}"
            }, ensure_ascii=False)
        
        # 从内存存储获取任务
        task = task_storage.get_task(self.session_id, task_id, self.user_id)
        if not task:
            return json.dumps({
                "success": False,
                "error": f"Task#{task_id} not found or not accessible"
            }, ensure_ascii=False)
        
        old_status = task.status
        
        # 更新任务状态
        updated_task = task_storage.update_task_status(
            self.session_id,
            task_id,
            self.user_id,
            status
        )
        
        if not updated_task:
            return json.dumps({
                "success": False,
                "error": f"Failed to update Task#{task_id}"
            }, ensure_ascii=False)
        
        # 推送事件到前端
        await self.event_manager.publish(self.session_id, {
            "type": "task_updated",
            "data": {
                **updated_task.to_dict(),
                "old_status": old_status  # 包含旧状态，便于前端对比
            }
        })
        
        return json.dumps({
            "success": True,
            "message": f"Task#{updated_task.id} updated from {old_status} to {status}",
            "task": updated_task.to_dict()
        }, ensure_ascii=False)

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


class TaskListTool(BaseTool):
    name = "task_list"
    description = (
        "查询当前会话的所有任务列表，用于了解工作进度。"
        "使用此工具时，可以可选提供status（状态）来过滤任务。"
        f"状态可选值: {', '.join(ALLOWED_STATUSES)}"
    )
    args_schema = ListTasksInput

    def __init__(self, user_id: int, session_id: str):
        super().__init__()
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'session_id', session_id)

    async def _arun(self, status: Optional[str] = None):
        # 验证状态（如果提供）
        if status and status not in ALLOWED_STATUSES:
            return json.dumps({
                "success": False,
                "error": f"Invalid status '{status}'. Allowed values: {', '.join(ALLOWED_STATUSES)}"
            }, ensure_ascii=False)
        
        # 从内存存储查询任务
        tasks = task_storage.list_tasks(
            session_id=self.session_id,
            user_id=self.user_id,
            status=status
        )
        
        # 获取统计信息
        summary = task_storage.get_task_summary(self.session_id, self.user_id)
        
        return json.dumps({
            "success": True,
            "tasks": [task.to_dict() for task in tasks],
            "summary": summary,
            "filtered_by": status if status else "all"
        }, ensure_ascii=False)

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


def create_task_tools(user_id: int, event_manager: AgentEventManager, session_id: str):
    """
    创建任务管理工具
    
    Args:
        user_id: 用户ID
        event_manager: 事件管理器（用于推送任务更新到前端）
        session_id: 会话ID（自动注入，无需智能体手动传入）
    """
    return [
        TaskCreateTool(user_id=user_id, event_manager=event_manager, session_id=session_id),
        TaskUpdateTool(user_id=user_id, event_manager=event_manager, session_id=session_id),
        TaskListTool(user_id=user_id, session_id=session_id)
    ]
