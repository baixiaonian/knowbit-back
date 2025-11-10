"""
文件夹Schema模型
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Union
from datetime import datetime


class FolderBase(BaseModel):
    """文件夹基础模型"""
    name: str = Field(..., min_length=1, max_length=255, description="文件夹名称")


class FolderCreate(FolderBase):
    """创建文件夹请求模型"""
    parentId: Optional[int] = Field(None, description="父文件夹ID，为null表示根目录")


class FolderRename(BaseModel):
    """重命名文件夹请求模型"""
    name: str = Field(..., min_length=1, max_length=255, description="新文件夹名称")


class FolderMove(BaseModel):
    """移动文件夹请求模型"""
    parentId: Optional[int] = Field(None, description="新父文件夹ID，为null表示移动到根目录")


class FolderResponse(BaseModel):
    """文件夹响应模型"""
    id: int
    name: str
    parentId: Optional[int] = None
    ownerId: int
    createdAt: datetime
    updatedAt: datetime
    
    class Config:
        from_attributes = True


class DocumentInTree(BaseModel):
    """知识库树中的文档节点"""
    id: int
    name: str  # 对应document.title
    type: str = "document"
    folderId: Optional[int] = None
    authorId: int
    lastModified: datetime  # 对应document.updated_at
    
    class Config:
        from_attributes = True


class FolderTreeNode(BaseModel):
    """文件夹树节点模型（支持递归）"""
    id: int
    name: str
    type: str = "folder"
    parentId: Optional[int] = None
    ownerId: int
    children: Optional[List[Union['FolderTreeNode', DocumentInTree]]] = []
    createdAt: datetime
    updatedAt: datetime
    
    class Config:
        from_attributes = True


# 启用前向引用
FolderTreeNode.model_rebuild()

