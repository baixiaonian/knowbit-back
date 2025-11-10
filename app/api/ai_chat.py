"""
AI问答对话API - 支持RAG检索增强生成
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from pydantic import BaseModel, Field
from typing import Optional, List, AsyncGenerator
from datetime import datetime
import os
import json

from app.db.database import get_db
from app.models.user_llm_config import UserLLMConfig
from app.models.document import Document
from app.services.ai_service import AIService
from app.services.vectorizer import DocumentVectorizer
from app.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/ai-chat", tags=["AI问答"])


class SelectedReference(BaseModel):
    """选中的引用文本"""
    text: str = Field(..., description="选中的文本内容")
    documentId: Optional[int] = Field(None, description="来源文档ID")
    source: Optional[str] = Field(None, description="来源类型：editor_selection|document_content|clipboard")


class AIChatRequest(BaseModel):
    """AI问答请求模型"""
    userId: int = Field(..., description="当前用户ID")
    question: str = Field(..., min_length=1, description="用户输入的问题")
    conversationId: Optional[str] = Field(None, description="会话ID（可选，暂时不使用）")
    documentId: Optional[int] = Field(None, description="当前文档ID（可选）")
    searchScope: Optional[str] = Field("all", description="搜索范围：all=所有文档，current=当前文档，默认all")
    ragEnabled: Optional[bool] = Field(True, description="是否启用RAG检索，默认true")
    selectedDocumentIds: Optional[List[int]] = Field(None, description="用户手动添加的文档ID列表")
    selectedReferences: Optional[List[SelectedReference]] = Field(None, description="用户手动添加的选中文本引用列表")


@router.post("/stream")
async def ai_chat_stream(
    request: AIChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    AI问答流式生成（RAG增强）
    
    返回Server-Sent Events (SSE)格式的流式数据
    格式：data: {content}\n\n
    """
    # 验证用户ID
    if request.userId != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问其他用户的配置"
        )
    
    # 查询用户的大模型配置
    result = await db.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user_id,
            UserLLMConfig.is_active == True
        )
    )
    llm_config = result.scalar_one_or_none()
    
    if not llm_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到可用的大模型配置，请先配置大模型访问信息"
        )
    
    # 更新最后使用时间
    llm_config.last_used_at = datetime.utcnow()
    await db.commit()
    
    # 构建上下文内容
    context_parts = []
    
    # 1. RAG检索相关文档（如果启用）
    if request.ragEnabled:
        rag_context = await _retrieve_rag_context(
            db=db,
            user_id=current_user_id,
            question=request.question,
            selected_document_ids=request.selectedDocumentIds,
            document_id=request.documentId,
            search_scope=request.searchScope
        )
        if rag_context:
            context_parts.append(rag_context)
        # 如果RAG启用但没找到相关文档，且用户指定了文档ID，返回错误
        elif request.selectedDocumentIds and len(request.selectedDocumentIds) > 0:
            async def error_response() -> AsyncGenerator[str, None]:
                error_data = {
                    "error": {
                        "code": "NO_RELEVANT_DOCUMENTS",
                        "message": "未找到相关文档内容，请尝试调整查询或选择其他文档"
                    }
                }
                yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
            
            return StreamingResponse(
                error_response(),
                media_type="text/event-stream"
            )
    
    # 2. 添加用户选中的引用文本
    if request.selectedReferences:
        selected_texts = [ref.text for ref in request.selectedReferences if ref.text.strip()]
        if selected_texts:
            selected_context = "用户选中的相关内容：\n\n" + "\n\n".join(selected_texts)
            context_parts.append(selected_context)
    
    # 3. 合并所有上下文
    full_context = "\n\n---\n\n".join(context_parts) if context_parts else None
    
    # 构建用户提示词（包含问题和上下文）
    if full_context:
        user_prompt = f"""基于以下知识库内容回答问题：

{full_context}

问题：{request.question}

请基于上述知识库内容准确回答问题。如果知识库中没有相关信息，请如实告知。"""
    else:
        # 如果没有RAG也没有选中文本，直接回答问题
        user_prompt = request.question
    
    # 创建AI服务
    ai_service = AIService(llm_config)
    
    async def generate() -> AsyncGenerator[str, None]:
        """
        生成流式响应（SSE格式）
        按照Server-Sent Events格式返回AI生成的回答内容
        格式：data: {"content": "..."}
        """
        try:
            # 累积内容，避免每个字符都单独发送
            accumulated_content = ""
            
            async for content in ai_service.generate_stream(
                user_prompt=user_prompt,
                prompt_type="ai_chat_qa",
                custom_system_prompt=None,
                context=None  # context已经在user_prompt中包含了
            ):
                accumulated_content += content
                
                # 当累积的内容达到一定长度或包含完整句子时发送
                if len(accumulated_content) >= 50 or content in ['。', '！', '？', '\n', '\n\n']:
                    # 按照接口说明，返回JSON格式
                    response_data = {"content": accumulated_content}
                    yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
                    accumulated_content = ""
            
            # 发送剩余内容
            if accumulated_content:
                response_data = {"content": accumulated_content}
                yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"
            
            # 发送完成标记（可选，如果需要）
            # done_data = {"done": True}
            # yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            # 错误情况下也使用SSE格式返回JSON
            error_data = {"error": {"code": "GENERATION_ERROR", "message": str(e)}}
            yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )


async def _retrieve_rag_context(
    db: AsyncSession,
    user_id: int,
    question: str,
    selected_document_ids: Optional[List[int]] = None,
    document_id: Optional[int] = None,
    search_scope: str = "all"
) -> Optional[str]:
    """
    RAG检索相关文档内容
    
    Args:
        db: 数据库会话
        user_id: 用户ID
        question: 用户问题
        selected_document_ids: 指定的文档ID列表
        document_id: 当前文档ID
        search_scope: 搜索范围（all/current）
        
    Returns:
        检索到的相关文档内容（Markdown格式），如果没有找到则返回None
    """
    try:
        # 创建向量化服务
        embedding_api_key = os.getenv("EMBEDDING_API_KEY") or "sk-BgRaMMUf3rFV7WszBwp6GjSNSqJLoZhSTILfka4bJwNxLDiw"
        embedding_api_base = os.getenv("EMBEDDING_API_BASE") or "https://aiproxy.bja.sealos.run/v1"
        embedding_model = os.getenv("EMBEDDING_MODEL") or "qwen3-embedding-0.6b"
        
        vectorizer = DocumentVectorizer(
            api_key=embedding_api_key,
            api_base=embedding_api_base,
            model=embedding_model
        )
        
        # 向量化查询
        query_embedding = await vectorizer.embed_query(question)
        
        # 将向量转换为PostgreSQL数组字符串格式
        # 格式: '[0.1, 0.2, ...]'::vector(1024)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # 构建SQL查询
        # 如果传了selectedDocumentIds，就在这些文档里检索
        if selected_document_ids and len(selected_document_ids) > 0:
            # 验证文档权限
            doc_result = await db.execute(
                select(Document.id).where(
                    Document.id.in_(selected_document_ids),
                    Document.author_id == user_id
                )
            )
            valid_doc_ids = [row[0] for row in doc_result.fetchall()]
            
            if not valid_doc_ids:
                return None
            
            # 直接将文档ID列表嵌入SQL（避免参数绑定问题）
            doc_ids_str = ','.join(map(str, valid_doc_ids))
            
            sql_query = text(f"""
                SELECT 
                    dc.document_id,
                    d.title as document_title,
                    dc.content,
                    1 - (dc.embedding <=> '{embedding_str}'::vector(1024)) as similarity
                FROM public.document_chunks dc
                JOIN public.documents d ON dc.document_id = d.id
                WHERE 
                    dc.document_id IN ({doc_ids_str})
                    AND (1 - (dc.embedding <=> '{embedding_str}'::vector(1024))) >= 0.2
                ORDER BY dc.embedding <=> '{embedding_str}'::vector(1024)
                LIMIT 5
            """)
            
            result = await db.execute(sql_query)
        
        # 如果searchScope是current，只在当前文档检索
        elif search_scope == "current" and document_id:
            # 验证文档权限
            doc_result = await db.execute(
                select(Document.id).where(
                    Document.id == document_id,
                    Document.author_id == user_id
                )
            )
            if not doc_result.scalar_one_or_none():
                return None
            
            sql_query = text(f"""
                SELECT 
                    dc.document_id,
                    d.title as document_title,
                    dc.content,
                    1 - (dc.embedding <=> '{embedding_str}'::vector(1024)) as similarity
                FROM public.document_chunks dc
                JOIN public.documents d ON dc.document_id = d.id
                WHERE 
                    dc.document_id = {document_id}
                    AND (1 - (dc.embedding <=> '{embedding_str}'::vector(1024))) >= 0.2
                ORDER BY dc.embedding <=> '{embedding_str}'::vector(1024)
                LIMIT 5
            """)
            
            result = await db.execute(sql_query)
        
        # 否则，在用户所有文档中检索
        else:
            sql_query = text(f"""
                SELECT 
                    dc.document_id,
                    d.title as document_title,
                    dc.content,
                    1 - (dc.embedding <=> '{embedding_str}'::vector(1024)) as similarity
                FROM public.document_chunks dc
                JOIN public.documents d ON dc.document_id = d.id
                WHERE 
                    d.author_id = {user_id}
                    AND (1 - (dc.embedding <=> '{embedding_str}'::vector(1024))) >= 0.2
                ORDER BY dc.embedding <=> '{embedding_str}'::vector(1024)
                LIMIT 5
            """)
            
            result = await db.execute(sql_query)
        
        # 处理检索结果
        rows = result.fetchall()
        
        if not rows:
            return None
        
        # 组装上下文内容
        context_parts = []
        for row in rows:
            doc_id, doc_title, content, similarity = row
            context_parts.append(
                f"## 文档：{doc_title}\n\n{content}"
            )
        
        return "\n\n---\n\n".join(context_parts)
        
    except Exception as e:
        # 如果RAG检索失败，不影响问答，只是不提供上下文
        print(f"RAG检索失败: {e}")
        return None

