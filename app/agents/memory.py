"""
基于数据库的 LangChain Memory 实现
"""
from typing import List, Optional, Dict, Any
from langchain.memory import ConversationBufferMemory
from langchain.schema import BaseMessage, HumanMessage, AIMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from app.db.database import AsyncSessionLocal


class DatabaseConversationMemory(ConversationBufferMemory):
    """
    基于数据库的对话记忆实现
    将消息历史存储到 PostgreSQL 数据库中
    """

    def __init__(
        self,
        session_id: str,
        user_id: int,
        agent_type: str = "writing",
        return_messages: bool = True,
        **kwargs
    ):
        """
        初始化数据库记忆
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            agent_type: 智能体类型
            return_messages: 是否返回消息对象（而非字符串）
        """
        super().__init__(return_messages=return_messages, **kwargs)
        # 使用 object.__setattr__ 绕过 Pydantic 的限制
        object.__setattr__(self, 'session_id', session_id)
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'agent_type', agent_type)
        object.__setattr__(self, '_session_initialized', False)

    async def _ensure_session(self) -> None:
        """确保会话记录存在"""
        if getattr(self, '_session_initialized', False):
            return

        async with AsyncSessionLocal() as session:
            # 检查会话是否存在
            result = await session.execute(
                select(AgentSession).where(AgentSession.session_id == self.session_id)
            )
            existing_session = result.scalar_one_or_none()

            if not existing_session:
                # 创建新会话
                new_session = AgentSession(
                    session_id=self.session_id,
                    user_id=self.user_id,
                    agent_type=self.agent_type,
                    status="active"
                )
                session.add(new_session)
                await session.commit()

            object.__setattr__(self, '_session_initialized', True)

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        """
        从数据库加载历史消息（同步方法，内部使用异步）
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # 如果事件循环正在运行，需要同步等待
            # 这里我们使用一个临时方案：先尝试加载，如果失败则使用空记忆
            try:
                loop.run_until_complete(self._load_memory_variables_async())
            except Exception:
                pass  # 如果加载失败，使用空记忆
        else:
            loop.run_until_complete(self._load_memory_variables_async())

        # 调用父类方法返回格式化后的记忆
        return super().load_memory_variables(inputs)

    async def _load_memory_variables_async(self) -> None:
        """异步加载历史消息"""
        await self._ensure_session()

        async with AsyncSessionLocal() as session:
            # 查询会话中的所有消息，按顺序排列
            result = await session.execute(
                select(AgentMessage)
                .where(AgentMessage.session_id == self.session_id)
                .order_by(AgentMessage.message_order.asc(), AgentMessage.created_at.asc())
            )
            messages = result.scalars().all()

            # 转换为 LangChain 消息对象
            memory_messages: List[BaseMessage] = []
            for msg in messages:
                if msg.role == "user":
                    memory_messages.append(HumanMessage(content=msg.content))
                elif msg.role == "assistant":
                    memory_messages.append(AIMessage(content=msg.content))
                elif msg.role == "system":
                    memory_messages.append(SystemMessage(content=msg.content))

            # 更新内部缓冲区
            self.chat_memory.messages = memory_messages

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        """
        保存对话上下文到数据库（同步方法，内部使用异步）
        注意：由于 LangChain 的 save_context 是同步方法，我们使用后台任务保存
        """
        # 调用父类方法更新内部缓冲区
        super().save_context(inputs, outputs)
        
        # 在后台异步保存（不阻塞）
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环正在运行，创建后台任务
                asyncio.create_task(self._save_context_async())
            else:
                # 否则直接运行
                loop.run_until_complete(self._save_context_async())
        except RuntimeError:
            # 如果没有事件循环，创建新的
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._save_context_async())
            loop.close()

    async def _save_context_async(self) -> None:
        """异步保存上下文到数据库"""
        await self._ensure_session()

        async with AsyncSessionLocal() as session:
            # 获取最新的消息（刚添加的）
            new_messages = self.chat_memory.messages

            # 查询数据库中已有的消息数量，确定新的 message_order
            result = await session.execute(
                select(AgentMessage)
                .where(AgentMessage.session_id == self.session_id)
            )
            existing_messages = result.scalars().all()
            next_order = len(existing_messages)

            # 保存新消息
            # 通常 save_context 会添加两条消息：用户输入和助手回复
            # 我们需要找到新增的消息
            existing_count = len(existing_messages)
            new_count = len(new_messages)

            if new_count > existing_count:
                # 保存新增的消息
                for i in range(existing_count, new_count):
                    msg = new_messages[i]
                    role = "user" if isinstance(msg, HumanMessage) else "assistant"
                    
                    db_message = AgentMessage(
                        session_id=self.session_id,
                        role=role,
                        content=msg.content,
                        message_order=next_order
                    )
                    session.add(db_message)
                    next_order += 1

            await session.commit()

    def clear(self) -> None:
        """
        清空记忆（从数据库删除消息）
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            asyncio.create_task(self._clear_async())
        else:
            loop.run_until_complete(self._clear_async())

        # 清空内部缓冲区
        super().clear()

    async def _clear_async(self) -> None:
        """异步清空记忆"""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import delete
            await session.execute(
                delete(AgentMessage)
                .where(AgentMessage.session_id == self.session_id)
            )
            await session.commit()

    async def save_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        直接保存用户消息（用于手动记录）
        """
        await self._ensure_session()

        async with AsyncSessionLocal() as session:
            # 获取下一个 message_order
            result = await session.execute(
                select(AgentMessage)
                .where(AgentMessage.session_id == self.session_id)
            )
            existing_messages = result.scalars().all()
            next_order = len(existing_messages)

            db_message = AgentMessage(
                session_id=self.session_id,
                role="user",
                content=content,
                message_order=next_order,
                message_metadata=metadata or {}
            )
            session.add(db_message)
            await session.commit()

    async def save_assistant_message(
        self,
        content: str,
        tool_calls: Optional[Dict[str, Any]] = None,
        tool_results: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        直接保存助手消息（用于手动记录）
        """
        await self._ensure_session()

        async with AsyncSessionLocal() as session:
            # 获取下一个 message_order
            result = await session.execute(
                select(AgentMessage)
                .where(AgentMessage.session_id == self.session_id)
            )
            existing_messages = result.scalars().all()
            next_order = len(existing_messages)

            db_message = AgentMessage(
                session_id=self.session_id,
                role="assistant",
                content=content,
                tool_calls=tool_calls,
                tool_results=tool_results,
                message_order=next_order,
                message_metadata=metadata or {}
            )
            session.add(db_message)
            await session.commit()

    async def get_message_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取消息历史（返回字典列表）
        """
        await self._ensure_session()

        async with AsyncSessionLocal() as session:
            query = (
                select(AgentMessage)
                .where(AgentMessage.session_id == self.session_id)
                .order_by(AgentMessage.message_order.asc(), AgentMessage.created_at.asc())
            )
            if limit:
                query = query.limit(limit)

            result = await session.execute(query)
            messages = result.scalars().all()
            return [msg.to_dict() for msg in messages]

