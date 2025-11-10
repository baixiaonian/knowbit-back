"""
文档相关工具
"""
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.models.document import Document
from app.agents.event_manager import AgentEventManager


class DocumentEditInput(BaseModel):
    document_id: int = Field(..., description="需要修改的文档ID")
    mode: str = Field("replace", description="修改方式: replace/append/prepend")
    content: str = Field(..., description="要写入的文本内容")
    summary: Optional[str] = Field(None, description="此次修改的概述")


class DocumentEditTool(BaseTool):
    name = "document_editor"
    description = (
        "对指定文档执行写作操作。"
        "输入JSON字段: {document_id, mode, content, summary}."
        "mode取值: replace(替换全文), append(在末尾追加), prepend(在开头插入)。"
        "content请包含完整文本片段，summary用于向用户说明此次修改。"
    )
    args_schema = DocumentEditInput

    def __init__(self, event_manager: AgentEventManager, user_id: int, session_id: str):
        super().__init__()
        self.event_manager = event_manager
        self.user_id = user_id
        self.session_id = session_id

    async def _arun(self, document_id: int, mode: str = "replace", content: str = "", summary: Optional[str] = None):
        data = DocumentEditInput(document_id=document_id, mode=mode, content=content, summary=summary)
        async with AsyncSessionLocal() as session:
            document = await self._get_document(session, data.document_id)
            if document is None:
                return "Document not found"
            original = document.content or ""
            if data.mode == "replace":
                document.content = data.content
            elif data.mode == "append":
                document.content = f"{original}\n\n{data.content}" if original else data.content
            elif data.mode == "prepend":
                document.content = f"{data.content}\n\n{original}" if original else data.content
            else:
                return "Unsupported mode"
            await session.commit()
        await self.event_manager.publish(
            self.session_id,
            {
                "type": "document_update",
                "data": {
                    "documentId": data.document_id,
                    "mode": data.mode,
                    "summary": data.summary,
                    "content": data.content
                }
            }
        )
        return "Document updated successfully"

    async def _run(self, *args, **kwargs):
        return await self._arun(*args, **kwargs)

    async def _get_document(self, session: AsyncSession, document_id: int) -> Optional[Document]:
        result = await session.execute(
            select(Document).where(Document.id == document_id, Document.author_id == self.user_id)
        )
        return result.scalar_one_or_none()


class DocumentReadInput(BaseModel):
    document_id: int


class DocumentReadTool(BaseTool):
    name = "document_reader"
    description = "读取指定文档全文内容，输入 {document_id}."
    args_schema = DocumentReadInput

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def _arun(self, document_id: int):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id, Document.author_id == self.user_id)
            )
            document = result.scalar_one_or_none()
            if not document:
                return "Document not found"
            return document.content or ""

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


def create_document_tools(event_manager: AgentEventManager, user_id: int, session_id: str):
    return [
        DocumentEditTool(event_manager=event_manager, user_id=user_id, session_id=session_id),
        DocumentReadTool(user_id=user_id)
    ]
