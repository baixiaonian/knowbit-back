"""
文件夹管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import List, Union
from datetime import datetime

from app.db.database import get_db
from app.models.folder import Folder
from app.models.document import Document
from app.schemas.folder import (
    FolderCreate, FolderRename, FolderMove, FolderResponse,
    FolderTreeNode, DocumentInTree
)
from app.schemas.common import ResponseModel
from app.utils.auth import get_current_user_id

router = APIRouter(prefix="/api", tags=["知识库管理"])


async def build_folder_tree(
    folders: List[Folder],
    documents: List[Document],
    parent_id: int = None
) -> List[Union[FolderTreeNode, DocumentInTree]]:
    """
    构建文件夹树结构
    """
    result = []
    
    # 获取当前层级的文件夹
    current_folders = [f for f in folders if f.parent_id == parent_id]
    
    # 获取当前层级的文档（根目录或指定父文件夹下的文档）
    current_docs = [
        DocumentInTree(
            id=doc.id,
            name=doc.title,
            type="document",
            folderId=doc.folder_id,
            authorId=doc.author_id,
            lastModified=doc.updated_at
        )
        for doc in documents if doc.folder_id == parent_id
    ]
    
    # 先添加文件夹
    for folder in current_folders:
        # 递归获取子节点
        children = await build_folder_tree(folders, documents, folder.id)
        
        node = FolderTreeNode(
            id=folder.id,
            name=folder.name,
            type="folder",
            parentId=folder.parent_id,
            ownerId=folder.owner_id,
            children=children if children else [],
            createdAt=folder.created_at,
            updatedAt=folder.updated_at
        )
        result.append(node)
    
    # 再添加文档（文件夹在前，文档在后）
    result.extend(current_docs)
    
    return result


@router.get("/knowledge-base", response_model=ResponseModel)
async def get_knowledge_base(
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    获取知识库结构（树形结构）
    """
    # 查询用户的所有未删除文件夹
    folders_result = await db.execute(
        select(Folder).where(
            and_(
                Folder.owner_id == current_user_id,
                Folder.is_deleted == False
            )
        )
    )
    folders = folders_result.scalars().all()
    
    # 查询用户的所有文档
    documents_result = await db.execute(
        select(Document).where(
            Document.author_id == current_user_id
        )
    )
    documents = documents_result.scalars().all()
    
    # 构建树形结构
    tree = await build_folder_tree(list(folders), list(documents), None)
    
    return ResponseModel(code=200, data=tree)


@router.post("/folders", response_model=ResponseModel)
async def create_folder(
    folder_data: FolderCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    创建文件夹
    """
    # 如果有父文件夹，验证父文件夹是否存在且属于当前用户
    if folder_data.parentId:
        parent_result = await db.execute(
            select(Folder).where(
                and_(
                    Folder.id == folder_data.parentId,
                    Folder.owner_id == current_user_id,
                    Folder.is_deleted == False
                )
            )
        )
        parent_folder = parent_result.scalar_one_or_none()
        if not parent_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="父文件夹不存在"
            )
    
    # 创建新文件夹
    new_folder = Folder(
        name=folder_data.name,
        parent_id=folder_data.parentId,
        owner_id=current_user_id
    )
    
    db.add(new_folder)
    await db.commit()
    await db.refresh(new_folder)
    
    response_data = FolderResponse(
        id=new_folder.id,
        name=new_folder.name,
        parentId=new_folder.parent_id,
        ownerId=new_folder.owner_id,
        createdAt=new_folder.created_at,
        updatedAt=new_folder.updated_at
    )
    
    return ResponseModel(
        code=200,
        message="文件夹创建成功",
        data=response_data
    )


@router.put("/folders/{folder_id}/rename", response_model=ResponseModel)
async def rename_folder(
    folder_id: int,
    rename_data: FolderRename,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    重命名文件夹
    """
    # 查询文件夹
    result = await db.execute(
        select(Folder).where(
            and_(
                Folder.id == folder_id,
                Folder.owner_id == current_user_id,
                Folder.is_deleted == False
            )
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
        )
    
    # 更新文件夹名称
    folder.name = rename_data.name
    folder.updated_at = datetime.now()
    
    await db.commit()
    await db.refresh(folder)
    
    return ResponseModel(
        code=200,
        message="重命名成功",
        data={
            "id": folder.id,
            "name": folder.name,
            "updatedAt": folder.updated_at
        }
    )


@router.delete("/folders/{folder_id}", response_model=ResponseModel)
async def delete_folder(
    folder_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    删除文件夹（软删除）
    """
    # 查询文件夹
    result = await db.execute(
        select(Folder).where(
            and_(
                Folder.id == folder_id,
                Folder.owner_id == current_user_id,
                Folder.is_deleted == False
            )
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
        )
    
    # 检查是否有子文件夹
    children_result = await db.execute(
        select(Folder).where(
            and_(
                Folder.parent_id == folder_id,
                Folder.is_deleted == False
            )
        )
    )
    children = children_result.scalars().all()
    
    if children:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先删除子文件夹"
        )
    
    # 检查是否有文档
    docs_result = await db.execute(
        select(Document).where(Document.folder_id == folder_id)
    )
    docs = docs_result.scalars().all()
    
    if docs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先删除或移动文件夹中的文档"
        )
    
    # 软删除文件夹
    folder.is_deleted = True
    folder.updated_at = datetime.now()
    
    await db.commit()
    
    return ResponseModel(code=200, message="删除成功")


@router.put("/folders/{folder_id}/move", response_model=ResponseModel)
async def move_folder(
    folder_id: int,
    move_data: FolderMove,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    移动文件夹
    """
    # 查询文件夹
    result = await db.execute(
        select(Folder).where(
            and_(
                Folder.id == folder_id,
                Folder.owner_id == current_user_id,
                Folder.is_deleted == False
            )
        )
    )
    folder = result.scalar_one_or_none()
    
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件夹不存在"
        )
    
    # 如果有新的父文件夹，验证父文件夹是否存在且属于当前用户
    if move_data.parentId:
        # 不能移动到自己或自己的子文件夹下
        if move_data.parentId == folder_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不能移动到自己下面"
            )
        
        parent_result = await db.execute(
            select(Folder).where(
                and_(
                    Folder.id == move_data.parentId,
                    Folder.owner_id == current_user_id,
                    Folder.is_deleted == False
                )
            )
        )
        parent_folder = parent_result.scalar_one_or_none()
        
        if not parent_folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="目标文件夹不存在"
            )
        
        # 检查是否会造成循环引用（简化检查）
        current_parent_id = parent_folder.parent_id
        while current_parent_id:
            if current_parent_id == folder_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="不能移动到自己的子文件夹下"
                )
            parent_check = await db.execute(
                select(Folder).where(Folder.id == current_parent_id)
            )
            parent = parent_check.scalar_one_or_none()
            current_parent_id = parent.parent_id if parent else None
    
    # 更新文件夹的父文件夹
    folder.parent_id = move_data.parentId
    folder.updated_at = datetime.now()
    
    await db.commit()
    await db.refresh(folder)
    
    return ResponseModel(
        code=200,
        message="移动成功",
        data={
            "id": folder.id,
            "parentId": folder.parent_id,
            "updatedAt": folder.updated_at
        }
    )

