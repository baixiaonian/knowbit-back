"""
任务管理工具
"""
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.models.agent_task import AgentTask


class CreateTaskInput(BaseModel):
    session_id: str = Field(..., description="当前会话ID")
    description: str = Field(..., description="任务描述")
    priority: int = Field(0, description="任务优先级")


class UpdateTaskInput(BaseModel):
    task_id: int
    status: str = Field(..., description="任务状态，如 pending/in_progress/completed")


class TaskCreateTool(BaseTool):
    name = "task_create"
    description = "创建新的写作任务项，输入 {session_id, description, priority}" \
        "，用于记录规划阶段的任务清单。"
    args_schema = CreateTaskInput

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def _arun(self, session_id: str, description: str, priority: int = 0):
        async with AsyncSessionLocal() as session:
            task = AgentTask(
                user_id=self.user_id,
                session_id=session_id,
                description=description,
                priority=priority,
                status="pending"
            )
            session.add(task)
            await session.commit()
            return f"Task#{task.id} created"

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


class TaskUpdateTool(BaseTool):
    name = "task_update"
    description = "更新任务状态，输入 {task_id, status}" \
        "，以跟踪智能体的执行进度。"
    args_schema = UpdateTaskInput

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def _arun(self, task_id: int, status: str):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(AgentTask).where(AgentTask.id == task_id, AgentTask.user_id == self.user_id)
            )
            task = result.scalar_one_or_none()
            if not task:
                return "Task not found"
            task.status = status
            await session.commit()
            return f"Task#{task.id} updated to {status}"

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


def create_task_tools(user_id: int):
    return [TaskCreateTool(user_id=user_id), TaskUpdateTool(user_id=user_id)]
