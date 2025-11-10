"""
文档Schema模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DocumentBase(BaseModel):
    """文档基础模型"""
    title: str = Field(..., min_length=1, max_length=255, description="文档标题")
    content: str = Field(..., description="文档内容")


class DocumentCreate(DocumentBase):
    """创建文档请求模型"""
    folderId: Optional[int] = Field(None, description="文件夹ID")
    categoryId: Optional[int] = Field(None, description="分类ID")
    tags: Optional[List[str]] = Field(None, description="标签数组")
    isPublic: bool = Field(False, description="是否公开")
    status: int = Field(1, ge=1, le=3, description="文档状态：1=草稿，2=发布，3=归档")
    excerpt: Optional[str] = Field(None, description="文档摘要")


class DocumentUpdate(BaseModel):
    """更新文档请求模型"""
    title: Optional[str] = Field(None, min_length=1, max_length=255, description="文档标题")
    content: Optional[str] = Field(None, description="文档内容")
    folderId: Optional[int] = Field(None, description="文件夹ID")
    categoryId: Optional[int] = Field(None, description="分类ID")
    tags: Optional[List[str]] = Field(None, description="标签数组")
    isPublic: Optional[bool] = Field(None, description="是否公开")
    status: Optional[int] = Field(None, ge=1, le=3, description="文档状态：1=草稿，2=发布，3=归档")
    excerpt: Optional[str] = Field(None, description="文档摘要")


class DocumentAutosave(BaseModel):
    """自动保存文档请求模型"""
    content: str = Field(..., description="文档内容")
    excerpt: Optional[str] = Field(None, description="文档摘要")


class DocumentStatsResponse(BaseModel):
    """文档统计响应模型"""
    viewCount: int = 0
    likeCount: int = 0
    shareCount: int = 0
    commentCount: int = 0
    
    class Config:
        from_attributes = True


class AuthorInfo(BaseModel):
    """作者信息"""
    id: int
    username: Optional[str] = None
    avatar: Optional[str] = None


class FolderInfo(BaseModel):
    """文件夹信息"""
    id: int
    name: str
    path: str


class CategoryInfo(BaseModel):
    """分类信息"""
    id: int
    name: str
    slug: Optional[str] = None


class DocumentResponse(BaseModel):
    """文档响应模型"""
    id: int
    title: str
    content: str
    authorId: int
    folderId: Optional[int] = None
    categoryId: Optional[int] = None
    isPublic: bool
    status: int
    tags: Optional[List[str]] = None
    excerpt: Optional[str] = None
    createdAt: datetime
    updatedAt: datetime
    stats: Optional[DocumentStatsResponse] = None
    
    class Config:
        from_attributes = True


class DocumentDetailResponse(DocumentResponse):
    """文档详情响应模型（包含关联信息）"""
    author: Optional[AuthorInfo] = None
    folder: Optional[FolderInfo] = None
    category: Optional[CategoryInfo] = None


class DocumentListItem(BaseModel):
    """文档列表项模型"""
    id: int
    title: str
    content: str  # 预览内容
    excerpt: Optional[str] = None
    authorId: int
    folderId: Optional[int] = None
    categoryId: Optional[int] = None
    isPublic: bool
    status: int
    tags: Optional[List[str]] = None
    createdAt: datetime
    updatedAt: datetime
    stats: Optional[DocumentStatsResponse] = None
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """文档列表响应模型"""
    documents: List[DocumentListItem]
    pagination: Dict[str, Any]


class DocumentBatchAction(BaseModel):
    """批量操作文档请求模型"""
    action: str = Field(..., description="操作类型：delete|move|updateStatus|updateCategory")
    documentIds: List[int] = Field(..., description="文档ID列表")
    data: Optional[Dict[str, Any]] = Field(None, description="操作数据")


class DocumentBatchResult(BaseModel):
    """批量操作结果项"""
    id: int
    success: bool
    message: str


class DocumentBatchResponse(BaseModel):
    """批量操作响应模型"""
    successCount: int
    failedCount: int
    results: List[DocumentBatchResult]


class DocumentStatsDetailResponse(BaseModel):
    """文档统计详情响应模型"""
    documentId: int
    viewCount: int
    likeCount: int
    shareCount: int
    commentCount: int
    updatedAt: datetime
    
    class Config:
        from_attributes = True

