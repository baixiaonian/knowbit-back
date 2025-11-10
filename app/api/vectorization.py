"""
文档向量化API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text
from typing import List

from app.db.database import get_db
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user_llm_config import UserLLMConfig
from app.schemas.vectorization import (
    VectorizeDocumentRequest,
    VectorizeDocumentResponse,
    DocumentChunkResponse,
    VectorSearchRequest,
    VectorSearchResponse,
    VectorSearchResult
)
from app.services.vectorizer import DocumentVectorizer
from app.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/vectorization", tags=["文档向量化"])


@router.post("/documents/{document_id}", response_model=VectorizeDocumentResponse)
async def vectorize_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    向量化文档
    
    将文档内容分块并生成向量，存储到document_chunks表
    """
    # 1. 获取文档
    result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.author_id == current_user_id
        )
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在或无权访问"
        )
    
    # 2. 获取用户的大模型配置
    config_result = await db.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user_id,
            UserLLMConfig.is_active == True
        )
    )
    config = config_result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未配置大模型访问信息"
        )
    
    # 3. 删除已存在的chunks（重新向量化）
    await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    await db.commit()
    
    # 4. 创建向量化服务
    # Embedding配置（支持自定义）
    import os
    
    # 优先使用环境变量配置
    embedding_api_key = os.getenv("EMBEDDING_API_KEY") or "sk-BgRaMMUf3rFV7WszBwp6GjSNSqJLoZhSTILfka4bJwNxLDiw"
    embedding_api_base = os.getenv("EMBEDDING_API_BASE") or "https://aiproxy.bja.sealos.run/v1"
    embedding_model = os.getenv("EMBEDDING_MODEL") or "qwen3-embedding-0.6b"
    
    vectorizer = DocumentVectorizer(
        api_key=embedding_api_key,
        api_base=embedding_api_base,
        model=embedding_model
    )
    
    # 5. 处理文档（分块 + 向量化）
    chunks_data = await vectorizer.process_document(
        content=document.content,
        metadata={
            'document_title': document.title,
            'author_id': document.author_id
        }
    )
    
    # 6. 保存到数据库
    total_tokens = 0
    for chunk_data in chunks_data:
        chunk = DocumentChunk(
            document_id=document_id,
            content=chunk_data['content'],
            embedding=chunk_data['embedding'],
            chunk_index=chunk_data['chunk_index'],
            token_count=chunk_data['token_count'],
            chunk_metadata=chunk_data['metadata']
        )
        db.add(chunk)
        total_tokens += chunk_data['token_count']
    
    await db.commit()
    
    return VectorizeDocumentResponse(
        documentId=document_id,
        chunkCount=len(chunks_data),
        totalTokens=total_tokens,
        message=f"文档向量化成功，生成{len(chunks_data)}个分块"
    )


@router.get("/documents/{document_id}/chunks", response_model=List[DocumentChunkResponse])
async def get_document_chunks(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    获取文档的所有分块
    """
    # 验证文档权限
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.author_id == current_user_id
        )
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在或无权访问"
        )
    
    # 获取chunks
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = result.scalars().all()
    
    return [
        DocumentChunkResponse(
            id=chunk.id,
            documentId=chunk.document_id,
            content=chunk.content,
            chunkIndex=chunk.chunk_index,
            tokenCount=chunk.token_count,
            createdAt=chunk.created_at
        )
        for chunk in chunks
    ]


@router.post("/search", response_model=VectorSearchResponse)
async def search_knowledge_base(
    search_request: VectorSearchRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    向量搜索知识库
    
    如果提供userId，则搜索该用户的知识库（所有文档）
    如果不提供，则搜索全站公开文档
    """
    # 获取用户的大模型配置
    config_result = await db.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user_id,
            UserLLMConfig.is_active == True
        )
    )
    config = config_result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未配置大模型访问信息"
        )
    
    # 创建向量化服务
    import os
    
    # 使用统一的Embedding配置
    embedding_api_key = os.getenv("EMBEDDING_API_KEY") or "sk-BgRaMMUf3rFV7WszBwp6GjSNSqJLoZhSTILfka4bJwNxLDiw"
    embedding_api_base = os.getenv("EMBEDDING_API_BASE") or "https://aiproxy.bja.sealos.run/v1"
    embedding_model = os.getenv("EMBEDDING_MODEL") or "qwen3-embedding-0.6b"
    
    vectorizer = DocumentVectorizer(
        api_key=embedding_api_key,
        api_base=embedding_api_base,
        model=embedding_model
    )
    
    # 向量化查询
    query_embedding = await vectorizer.embed_query(search_request.query)
    
    # 构建SQL查询
    if search_request.userId:
        # 搜索指定用户的知识库
        sql_query = text("""
            SELECT 
                dc.id as chunk_id,
                dc.document_id,
                d.title as document_title,
                dc.content,
                1 - (dc.embedding <=> :embedding::vector(1024)) as similarity
            FROM public.document_chunks dc
            JOIN public.documents d ON dc.document_id = d.id
            WHERE 
                d.author_id = :user_id
                AND (1 - (dc.embedding <=> :embedding::vector(1024))) >= :threshold
            ORDER BY dc.embedding <=> :embedding::vector(1024)
            LIMIT :limit
        """)
        
        result = await db.execute(
            sql_query,
            {
                "embedding": query_embedding,
                "user_id": search_request.userId,
                "threshold": search_request.similarityThreshold,
                "limit": search_request.topK
            }
        )
    else:
        # 搜索全站公开文档
        sql_query = text("""
            SELECT 
                dc.id as chunk_id,
                dc.document_id,
                d.title as document_title,
                dc.content,
                1 - (dc.embedding <=> :embedding::vector(1024)) as similarity
            FROM public.document_chunks dc
            JOIN public.documents d ON dc.document_id = d.id
            WHERE 
                d.is_public = true
                AND d.status = 1
                AND (1 - (dc.embedding <=> :embedding::vector(1024))) >= :threshold
            ORDER BY dc.embedding <=> :embedding::vector(1024)
            LIMIT :limit
        """)
        
        result = await db.execute(
            sql_query,
            {
                "embedding": query_embedding,
                "threshold": search_request.similarityThreshold,
                "limit": search_request.topK
            }
        )
    
    # 处理结果
    rows = result.fetchall()
    search_results = [
        VectorSearchResult(
            chunkId=row.chunk_id,
            documentId=row.document_id,
            documentTitle=row.document_title,
            content=row.content,
            similarity=float(row.similarity)
        )
        for row in rows
    ]
    
    return VectorSearchResponse(
        query=search_request.query,
        results=search_results,
        totalResults=len(search_results)
    )


@router.delete("/documents/{document_id}/chunks")
async def delete_document_chunks(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    删除文档的所有向量分块
    """
    # 验证文档权限
    doc_result = await db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.author_id == current_user_id
        )
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在或无权访问"
        )
    
    # 删除chunks
    result = await db.execute(
        delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
    )
    
    await db.commit()
    
    return {
        "message": "文档向量已删除",
        "documentId": document_id
    }


