"""
任务内存存储管理
"""
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from collections import defaultdict

# 任务状态常量（避免循环导入）
TASK_STATUS = {
    "PENDING": "pending",
    "IN_PROGRESS": "in_progress",
    "COMPLETED": "completed",
    "FAILED": "failed",
    "CANCELLED": "cancelled"
}


@dataclass
class Task:
    """任务数据类"""
    id: int
    session_id: str
    user_id: int
    description: str
    status: str
    priority: int
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }


class TaskStorage:
    """
    任务内存存储
    按 session_id 组织任务，支持任务的创建、更新、查询
    """
    
    def __init__(self):
        # {session_id: {task_id: Task}}
        self._tasks: Dict[str, Dict[int, Task]] = defaultdict(dict)
        # 全局任务ID计数器
        self._task_id_counter = 0
        self._lock = None  # 如果需要线程安全，可以使用 asyncio.Lock
    
    def create_task(
        self,
        session_id: str,
        user_id: int,
        description: str,
        priority: int = 0
    ) -> Task:
        """创建新任务"""
        self._task_id_counter += 1
        task_id = self._task_id_counter
        
        now = datetime.utcnow()
        task = Task(
            id=task_id,
            session_id=session_id,
            user_id=user_id,
            description=description,
            status=TASK_STATUS["PENDING"],
            priority=priority,
            created_at=now,
            updated_at=now
        )
        
        self._tasks[session_id][task_id] = task
        return task
    
    def get_task(self, session_id: str, task_id: int, user_id: int) -> Optional[Task]:
        """获取任务"""
        if session_id not in self._tasks:
            return None
        
        task = self._tasks[session_id].get(task_id)
        if task and task.user_id == user_id:
            return task
        return None
    
    def update_task_status(
        self,
        session_id: str,
        task_id: int,
        user_id: int,
        status: str
    ) -> Optional[Task]:
        """更新任务状态"""
        task = self.get_task(session_id, task_id, user_id)
        if not task:
            return None
        
        task.status = status
        task.updated_at = datetime.utcnow()
        return task
    
    def list_tasks(
        self,
        session_id: str,
        user_id: int,
        status: Optional[str] = None
    ) -> List[Task]:
        """查询任务列表"""
        if session_id not in self._tasks:
            return []
        
        tasks = [
            task for task in self._tasks[session_id].values()
            if task.user_id == user_id
        ]
        
        if status:
            tasks = [task for task in tasks if task.status == status]
        
        # 按优先级降序，创建时间升序排序
        tasks.sort(key=lambda t: (-t.priority, t.created_at))
        return tasks
    
    def get_task_summary(self, session_id: str, user_id: int) -> dict:
        """获取任务统计信息"""
        all_tasks = self.list_tasks(session_id, user_id)
        
        return {
            "total": len(all_tasks),
            "pending": sum(1 for t in all_tasks if t.status == TASK_STATUS["PENDING"]),
            "in_progress": sum(1 for t in all_tasks if t.status == TASK_STATUS["IN_PROGRESS"]),
            "completed": sum(1 for t in all_tasks if t.status == TASK_STATUS["COMPLETED"]),
            "failed": sum(1 for t in all_tasks if t.status == TASK_STATUS["FAILED"]),
        }
    
    def clear_session(self, session_id: str):
        """清空会话的所有任务（会话结束时调用）"""
        if session_id in self._tasks:
            del self._tasks[session_id]


# 全局任务存储实例
task_storage = TaskStorage()

