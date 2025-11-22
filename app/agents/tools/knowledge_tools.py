"""
知识检索 / 网络搜索工具
"""
import os
from typing import Optional, List
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from langchain_community.tools import DuckDuckGoSearchRun
from sqlalchemy import text

from app.db.database import AsyncSessionLocal
from app.services.vectorizer import DocumentVectorizer
from app.agents.event_manager import AgentEventManager


class DocumentSearchInput(BaseModel):
    query: str = Field(..., description="检索问题或关键词")
    top_k: int = Field(3, description="返回片段数量")


class DocumentSearchTool(BaseTool):
    name = "document_knowledge_search"
    description = (
        "从用户文档知识库中检索与查询最相关的片段。"
        "在创作内容前，应该先使用此工具检索相关信息，以确保内容的准确性和丰富性。"
        "使用此工具时，需要提供query（检索问题或关键词）和top_k（返回片段数量，默认3）。"
        "返回格式化的文本片段列表，包含相关文档的内容片段。"
        "如果用户提供了selectedDocumentIds，会优先在这些文档中搜索。"
    )
    args_schema = DocumentSearchInput

    def __init__(
        self, 
        user_id: int, 
        selected_document_ids: Optional[List[int]] = None,
        event_manager: Optional[AgentEventManager] = None,
        session_id: Optional[str] = None
    ):
        super().__init__()
        object.__setattr__(self, 'user_id', user_id)
        object.__setattr__(self, 'selected_document_ids', selected_document_ids or [])
        object.__setattr__(self, 'event_manager', event_manager)
        object.__setattr__(self, 'session_id', session_id)

    async def _arun(self, query: str, top_k: int = 3):
        # 发布搜索开始事件
        if self.event_manager and self.session_id:
            await self.event_manager.publish(self.session_id, {
                "type": "knowledge_search_start",
                "data": {
                    "query": query,
                    "top_k": top_k,
                    "selected_document_ids": self.selected_document_ids,
                    "search_type": "document"
                }
            })
        
        try:
            # 使用统一的Embedding配置（环境变量或默认值）
            embedding_api_key = os.getenv("EMBEDDING_API_KEY") or "sk-BgRaMMUf3rFV7WszBwp6GjSNSqJLoZhSTILfka4bJwNxLDiw"
            embedding_api_base = os.getenv("EMBEDDING_API_BASE") or "https://aiproxy.bja.sealos.run/v1"
            embedding_model = os.getenv("EMBEDDING_MODEL") or "qwen3-embedding-0.6b"
            
            vectorizer = DocumentVectorizer(
                api_key=embedding_api_key,
                api_base=embedding_api_base,
                model=embedding_model
            )
            
            async with AsyncSessionLocal() as session:
                query_embedding = await vectorizer.embed_query(query)
                
                # 将向量转换为PostgreSQL数组字符串格式，避免参数绑定问题
                # 格式: '[0.1, 0.2, ...]'::vector(1024)
                embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
                
                # 如果指定了文档ID列表，优先搜索这些文档
                if self.selected_document_ids:
                    # 验证文档权限：确保这些文档属于当前用户
                    from app.models.document import Document
                    from sqlalchemy import select
                    
                    doc_result = await session.execute(
                        select(Document.id).where(
                            Document.id.in_(self.selected_document_ids),
                            Document.author_id == self.user_id
                        )
                    )
                    valid_doc_ids = [row[0] for row in doc_result.fetchall()]
                    
                    if valid_doc_ids:
                        # 使用 CASE WHEN 调整排序：指定文档的片段优先返回
                        # 通过给指定文档的相似度分数减去一个固定值来提升优先级
                        # 将文档ID列表转换为字符串用于IN子句（已验证为整数，安全）
                        doc_ids_str = ','.join(map(str, valid_doc_ids))
                        sql = text(
                            f"""
                            SELECT dc.content,
                                   CASE 
                                       WHEN dc.document_id IN ({doc_ids_str})
                                       THEN (dc.embedding <-> '{embedding_str}'::vector(1024)) - 0.1
                                       ELSE (dc.embedding <-> '{embedding_str}'::vector(1024))
                                   END as adjusted_distance
                            FROM public.document_chunks dc
                            JOIN public.documents d ON dc.document_id = d.id
                            WHERE d.author_id = :user_id
                            ORDER BY adjusted_distance ASC
                            LIMIT :limit
                            """
                        )
                        rows = await session.execute(
                            sql,
                            {
                                "user_id": self.user_id,
                                "limit": top_k
                            }
                        )
                    else:
                        # 如果指定的文档ID都无效，回退到普通搜索
                        sql = text(
                            f"""
                            SELECT dc.content
                            FROM public.document_chunks dc
                            JOIN public.documents d ON dc.document_id = d.id
                            WHERE d.author_id = :user_id
                            ORDER BY dc.embedding <-> '{embedding_str}'::vector(1024)
                            LIMIT :limit
                            """
                        )
                        rows = await session.execute(
                            sql,
                            {"user_id": self.user_id, "limit": top_k}
                        )
                else:
                    # 未指定文档ID，使用原来的查询方式
                    sql = text(
                        f"""
                        SELECT dc.content
                        FROM public.document_chunks dc
                        JOIN public.documents d ON dc.document_id = d.id
                        WHERE d.author_id = :user_id
                        ORDER BY dc.embedding <-> '{embedding_str}'::vector(1024)
                        LIMIT :limit
                        """
                    )
                    rows = await session.execute(
                        sql,
                        {"user_id": self.user_id, "limit": top_k}
                    )
                
                records = [row[0] for row in rows.fetchall() if row[0]]
                
                # 发布搜索结果事件
                if self.event_manager and self.session_id:
                    if not records:
                        await self.event_manager.publish(self.session_id, {
                            "type": "knowledge_search_result",
                            "data": {
                                "query": query,
                                "success": False,
                                "message": "No relevant content found",
                                "results_count": 0,
                                "search_type": "document"
                            }
                        })
                    else:
                        await self.event_manager.publish(self.session_id, {
                            "type": "knowledge_search_result",
                            "data": {
                                "query": query,
                                "success": True,
                                "results_count": len(records),
                                "search_type": "document",
                                "selected_document_ids": self.selected_document_ids
                            }
                        })
                
                if not records:
                    return "No relevant content found"
                return "\n\n".join(f"片段{i+1}:\n{content}" for i, content in enumerate(records))
        except Exception as exc:  # pylint: disable=broad-except
            # 发布搜索错误事件
            if self.event_manager and self.session_id:
                await self.event_manager.publish(self.session_id, {
                    "type": "knowledge_search_result",
                    "data": {
                        "query": query,
                        "success": False,
                        "error": str(exc),
                        "search_type": "document"
                    }
                })
            return f"Error retrieving knowledge: {exc}"

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


class WebSearchInput(BaseModel):
    query: str


class WebSearchTool(BaseTool):
    name = "web_research_tool"
    description = (
        "使用DuckDuckGo搜索互联网上的公开资料。"
        "在创作内容前，如果文档库中没有相关信息，应该使用此工具搜索互联网资料。"
        "使用此工具时，需要提供query（搜索关键词）。"
        "返回搜索到的相关网页内容摘要。"
    )
    args_schema = WebSearchInput

    def __init__(
        self,
        event_manager: Optional[AgentEventManager] = None,
        session_id: Optional[str] = None
    ):
        super().__init__()
        object.__setattr__(self, 'client', DuckDuckGoSearchRun())
        object.__setattr__(self, 'event_manager', event_manager)
        object.__setattr__(self, 'session_id', session_id)

    async def _arun(self, query: str):
        # 发布搜索开始事件
        if self.event_manager and self.session_id:
            await self.event_manager.publish(self.session_id, {
                "type": "knowledge_search_start",
                "data": {
                    "query": query,
                    "search_type": "web"
                }
            })
        
        try:
            result = await self.client.arun(query)
            
            # 发布搜索结果事件
            if self.event_manager and self.session_id:
                await self.event_manager.publish(self.session_id, {
                    "type": "knowledge_search_result",
                    "data": {
                        "query": query,
                        "success": True,
                        "search_type": "web",
                        "result_length": len(result) if result else 0
                    }
                })
            
            return result
        except Exception as exc:  # pylint: disable=broad-except
            # 发布搜索错误事件
            error_msg = str(exc)
            if self.event_manager and self.session_id:
                await self.event_manager.publish(self.session_id, {
                    "type": "knowledge_search_result",
                    "data": {
                        "query": query,
                        "success": False,
                        "error": error_msg,
                        "search_type": "web",
                        "message": "网络搜索失败，请基于已有知识生成内容"
                    }
                })
            # 不抛出异常，而是返回友好的错误信息，让智能体可以继续执行
            return f"网络搜索失败: {error_msg}。请基于已有知识和理解生成内容。"

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


def create_knowledge_tools(
    user_id: int, 
    selected_document_ids: Optional[List[int]] = None,
    event_manager: Optional[AgentEventManager] = None,
    session_id: Optional[str] = None
):
    """
    创建知识检索工具
    
    Args:
        user_id: 用户ID
        selected_document_ids: 可选，指定要重点搜索的文档ID列表
        event_manager: 可选，事件管理器，用于向前端推送搜索事件
        session_id: 可选，会话ID，用于事件推送
    """
    return [
        DocumentSearchTool(
            user_id=user_id, 
            selected_document_ids=selected_document_ids,
            event_manager=event_manager,
            session_id=session_id
        ),
        WebSearchTool(
            event_manager=event_manager,
            session_id=session_id
        )
    ]
