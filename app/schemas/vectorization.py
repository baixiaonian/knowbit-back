"""
文档向量化Schema
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class VectorizeDocumentRequest(BaseModel):
    """向量化文档请求"""
    documentId: int = Field(..., description="文档ID")


class VectorizeDocumentResponse(BaseModel):
    """向量化文档响应"""
    documentId: int
    chunkCount: int
    totalTokens: int
    message: str


class DocumentChunkResponse(BaseModel):
    """文档分块响应"""
    id: int
    documentId: int
    content: str
    chunkIndex: int
    tokenCount: Optional[int]
    createdAt: datetime
    
    class Config:
        from_attributes = True


class VectorSearchRequest(BaseModel):
    """向量搜索请求"""
    query: str = Field(..., min_length=1, description="搜索查询")
    userId: Optional[int] = Field(None, description="用户ID（搜索该用户的知识库）")
    topK: Optional[int] = Field(10, ge=1, le=50, description="返回结果数量")
    similarityThreshold: Optional[float] = Field(0.7, ge=0.0, le=1.0, description="相似度阈值")


class VectorSearchResult(BaseModel):
    """向量搜索结果"""
    chunkId: int
    documentId: int
    documentTitle: str
    content: str
    similarity: float
    
    class Config:
        from_attributes = True


class VectorSearchResponse(BaseModel):
    """向量搜索响应"""
    query: str
    results: List[VectorSearchResult]
    totalResults: int


