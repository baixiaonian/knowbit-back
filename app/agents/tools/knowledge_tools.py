"""
知识检索 / 网络搜索工具
"""
from typing import Optional
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_community.tools import DuckDuckGoSearchRun
from sqlalchemy import text

from app.db.database import AsyncSessionLocal
from app.services.llm_provider import get_user_vectorizer


class DocumentSearchInput(BaseModel):
    query: str = Field(..., description="检索问题或关键词")
    top_k: int = Field(3, description="返回片段数量")


class DocumentSearchTool(BaseTool):
    name = "document_knowledge_search"
    description = (
        "从用户文档知识库中检索与查询最相关的片段。"
        "输入 {query, top_k}，返回格式化的文本片段列表。"
    )
    args_schema = DocumentSearchInput

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    async def _arun(self, query: str, top_k: int = 3):
        try:
            async with AsyncSessionLocal() as session:
                vectorizer = await get_user_vectorizer(session, self.user_id)
                query_embedding = await vectorizer.embed_query(query)
                sql = text(
                    """
                    SELECT dc.content
                    FROM public.document_chunks dc
                    JOIN public.documents d ON dc.document_id = d.id
                    WHERE d.author_id = :user_id
                    ORDER BY dc.embedding <-> :embedding::vector(1024)
                    LIMIT :limit
                    """
                )
                rows = await session.execute(
                    sql,
                    {"user_id": self.user_id, "embedding": query_embedding, "limit": top_k}
                )
                records = [row[0] for row in rows.fetchall() if row[0]]
                if not records:
                    return "No relevant content found"
                return "\n\n".join(f"片段{i+1}:\n{content}" for i, content in enumerate(records))
        except Exception as exc:  # pylint: disable=broad-except
            return f"Error retrieving knowledge: {exc}"

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


class WebSearchInput(BaseModel):
    query: str


class WebSearchTool(BaseTool):
    name = "web_research_tool"
    description = "使用DuckDuckGo搜索互联网上的公开资料。输入 {query}."
    args_schema = WebSearchInput

    def __init__(self):
        super().__init__()
        self.client = DuckDuckGoSearchRun()

    async def _arun(self, query: str):
        return await self.client.arun(query)

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


def create_knowledge_tools(user_id: int):
    return [
        DocumentSearchTool(user_id=user_id),
        WebSearchTool()
    ]
