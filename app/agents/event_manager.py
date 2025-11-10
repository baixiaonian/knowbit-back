"""
智能体事件广播管理
"""
import asyncio
from collections import defaultdict
from typing import Dict, Set, Any


class AgentEventManager:
    """维护每个session的事件订阅队列"""

    def __init__(self) -> None:
        self._listeners: Dict[str, Set[asyncio.Queue]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def register(self, session_id: str) -> asyncio.Queue:
        """注册一个新的事件监听队列"""
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._listeners[session_id].add(queue)
        return queue

    async def unregister(self, session_id: str, queue: asyncio.Queue) -> None:
        async with self._lock:
            listeners = self._listeners.get(session_id)
            if not listeners:
                return
            listeners.discard(queue)
            if not listeners:
                self._listeners.pop(session_id, None)

    async def publish(self, session_id: str, event: Dict[str, Any]) -> None:
        """向指定session广播事件"""
        async with self._lock:
            listeners = list(self._listeners.get(session_id, set()))
        for queue in listeners:
            await queue.put(event)

    async def close_session(self, session_id: str) -> None:
        async with self._lock:
            listeners = list(self._listeners.pop(session_id, set()))
        for queue in listeners:
            await queue.put({"type": "session_closed", "data": {}})
