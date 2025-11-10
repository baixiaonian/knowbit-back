"""
文档管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, desc, asc, delete
from typing import Optional, List
from datetime import datetime
from math import ceil

from app.db.database import get_db
from app.models.document import Document
from app.models.document_stats import DocumentStats
from app.models.folder import Folder
from app.models.category import Category
from app.models.user import User
from app.schemas.document import (
    DocumentCreate, DocumentUpdate, DocumentAutosave,
    DocumentResponse, DocumentDetailResponse, DocumentListResponse,
    DocumentBatchAction, DocumentBatchResponse, DocumentBatchResult,
    DocumentStatsResponse, DocumentStatsDetailResponse,
    AuthorInfo, FolderInfo, CategoryInfo, DocumentListItem
)
from app.schemas.common import ResponseModel
from app.utils.auth import get_current_user_id

router = APIRouter(prefix="/api", tags=["文档管理"])


@router.post("/documents", response_model=ResponseModel)
async def create_document(
    doc_data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    创建文档
    """
    # 如果指定了文件夹，验证文件夹是否存在且属于当前用户
    if doc_data.folderId:
        folder_result = await db.execute(
            select(Folder).where(
                and_(
                    Folder.id == doc_data.folderId,
                    Folder.owner_id == current_user_id,
                    Folder.is_deleted == False
                )
            )
        )
        folder = folder_result.scalar_one_or_none()
        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件夹不存在"
            )
    
    # 如果指定了分类，验证分类是否存在
    if doc_data.categoryId:
        category_result = await db.execute(
            select(Category).where(Category.id == doc_data.categoryId)
        )
        category = category_result.scalar_one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分类不存在"
            )
    
    # 创建文档
    new_document = Document(
        title=doc_data.title,
        content=doc_data.content,
        author_id=current_user_id,
        folder_id=doc_data.folderId,
        category_id=doc_data.categoryId,
        tags=doc_data.tags,
        is_public=doc_data.isPublic,
        status=doc_data.status,
        excerpt=doc_data.excerpt
    )
    
    db.add(new_document)
    await db.commit()
    await db.refresh(new_document)
    
    # 创建文档统计记录
    doc_stats = DocumentStats(
        document_id=new_document.id,
        view_count=0,
        like_count=0,
        share_count=0,
        comment_count=0
    )
    db.add(doc_stats)
    await db.commit()
    await db.refresh(doc_stats)
    
    # 构建响应
    response_data = DocumentResponse(
        id=new_document.id,
        title=new_document.title,
        content=new_document.content,
        authorId=new_document.author_id,
        folderId=new_document.folder_id,
        categoryId=new_document.category_id,
        isPublic=new_document.is_public,
        status=new_document.status,
        tags=new_document.tags,
        excerpt=new_document.excerpt,
        createdAt=new_document.created_at,
        updatedAt=new_document.updated_at,
        stats=DocumentStatsResponse(
            viewCount=doc_stats.view_count,
            likeCount=doc_stats.like_count,
            shareCount=doc_stats.share_count,
            commentCount=doc_stats.comment_count
        )
    )
    
    return ResponseModel(
        code=200,
        message="文档创建成功",
        data=response_data
    )


@router.get("/documents/{document_id}", response_model=ResponseModel)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    获取文档详情
    """
    # 查询文档
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # 权限检查：只有作者或公开文档可以访问
    if document.author_id != current_user_id and not document.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此文档"
        )
    
    # 查询作者信息
    author_result = await db.execute(
        select(User).where(User.id == document.author_id)
    )
    author = author_result.scalar_one_or_none()
    
    # 查询文件夹信息
    folder_info = None
    if document.folder_id:
        folder_result = await db.execute(
            select(Folder).where(Folder.id == document.folder_id)
        )
        folder = folder_result.scalar_one_or_none()
        if folder:
            folder_info = FolderInfo(
                id=folder.id,
                name=folder.name,
                path=folder.name  # 简化处理，实际应该构建完整路径
            )
    
    # 查询分类信息
    category_info = None
    if document.category_id:
        category_result = await db.execute(
            select(Category).where(Category.id == document.category_id)
        )
        category = category_result.scalar_one_or_none()
        if category:
            category_info = CategoryInfo(
                id=category.id,
                name=category.name,
                slug=category.slug
            )
    
    # 查询统计信息
    stats_result = await db.execute(
        select(DocumentStats).where(DocumentStats.document_id == document_id)
    )
    stats = stats_result.scalar_one_or_none()
    
    # 构建响应
    response_data = DocumentDetailResponse(
        id=document.id,
        title=document.title,
        content=document.content,
        authorId=document.author_id,
        author=AuthorInfo(
            id=author.id,
            username=author.username,
            avatar=author.avatar_url
        ) if author else None,
        folderId=document.folder_id,
        folder=folder_info,
        categoryId=document.category_id,
        category=category_info,
        isPublic=document.is_public,
        status=document.status,
        tags=document.tags,
        excerpt=document.excerpt,
        createdAt=document.created_at,
        updatedAt=document.updated_at,
        stats=DocumentStatsResponse(
            viewCount=stats.view_count if stats else 0,
            likeCount=stats.like_count if stats else 0,
            shareCount=stats.share_count if stats else 0,
            commentCount=stats.comment_count if stats else 0
        )
    )
    
    return ResponseModel(code=200, data=response_data)


@router.put("/documents/{document_id}", response_model=ResponseModel)
async def update_document(
    document_id: int,
    doc_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    更新文档
    """
    # 查询文档
    doc_result = await db.execute(
        select(Document).where(
            and_(
                Document.id == document_id,
                Document.author_id == current_user_id
            )
        )
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在或无权编辑"
        )
    
    # 更新字段
    if doc_data.title is not None:
        document.title = doc_data.title
    if doc_data.content is not None:
        document.content = doc_data.content
    if doc_data.folderId is not None:
        document.folder_id = doc_data.folderId
    if doc_data.categoryId is not None:
        document.category_id = doc_data.categoryId
    if doc_data.tags is not None:
        document.tags = doc_data.tags
    if doc_data.isPublic is not None:
        document.is_public = doc_data.isPublic
    if doc_data.status is not None:
        document.status = doc_data.status
    if doc_data.excerpt is not None:
        document.excerpt = doc_data.excerpt
    
    document.updated_at = datetime.now()
    
    await db.commit()
    await db.refresh(document)
    
    return ResponseModel(
        code=200,
        message="更新成功",
        data={
            "id": document.id,
            "title": document.title,
            "content": document.content,
            "folderId": document.folder_id,
            "categoryId": document.category_id,
            "tags": document.tags,
            "isPublic": document.is_public,
            "status": document.status,
            "excerpt": document.excerpt,
            "updatedAt": document.updated_at
        }
    )


@router.post("/documents/{document_id}/autosave", response_model=ResponseModel)
async def autosave_document(
    document_id: int,
    autosave_data: DocumentAutosave,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    自动保存文档
    """
    # 查询文档
    doc_result = await db.execute(
        select(Document).where(
            and_(
                Document.id == document_id,
                Document.author_id == current_user_id
            )
        )
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在或无权编辑"
        )
    
    # 更新内容
    document.content = autosave_data.content
    if autosave_data.excerpt:
        document.excerpt = autosave_data.excerpt
    document.updated_at = datetime.now()
    
    await db.commit()
    await db.refresh(document)
    
    return ResponseModel(
        code=200,
        message="自动保存成功",
        data={
            "id": document.id,
            "updatedAt": document.updated_at
        }
    )


@router.delete("/documents/{document_id}", response_model=ResponseModel)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    删除文档
    """
    # 查询文档
    doc_result = await db.execute(
        select(Document).where(
            and_(
                Document.id == document_id,
                Document.author_id == current_user_id
            )
        )
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在或无权删除"
        )
    
    # 先删除相关的统计记录（如果存在）
    await db.execute(
        delete(DocumentStats).where(DocumentStats.document_id == document_id)
    )
    
    # 再删除文档本身
    await db.execute(
        delete(Document).where(Document.id == document_id)
    )
    
    await db.commit()
    
    return ResponseModel(code=200, message="删除成功")


@router.get("/documents", response_model=ResponseModel)
async def get_documents(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    folderId: Optional[int] = Query(None, description="文件夹ID"),
    categoryId: Optional[int] = Query(None, description="分类ID"),
    status: Optional[int] = Query(None, ge=1, le=3, description="文档状态"),
    isPublic: Optional[bool] = Query(None, description="是否公开"),
    tags: Optional[str] = Query(None, description="标签，逗号分隔"),
    sort: Optional[str] = Query("createdAt", description="排序字段"),
    order: Optional[str] = Query("desc", description="排序方向"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    获取文档列表
    """
    # 构建查询条件
    conditions = [Document.author_id == current_user_id]
    
    if folderId is not None:
        conditions.append(Document.folder_id == folderId)
    if categoryId is not None:
        conditions.append(Document.category_id == categoryId)
    if status is not None:
        conditions.append(Document.status == status)
    if isPublic is not None:
        conditions.append(Document.is_public == isPublic)
    if tags:
        tag_list = tags.split(",")
        conditions.append(Document.tags.overlap(tag_list))
    if search:
        conditions.append(
            or_(
                Document.title.ilike(f"%{search}%"),
                Document.content.ilike(f"%{search}%")
            )
        )
    
    # 查询总数
    count_result = await db.execute(
        select(func.count(Document.id)).where(and_(*conditions))
    )
    total = count_result.scalar()
    
    # 构建排序
    order_column = getattr(Document, sort, Document.created_at)
    if order == "asc":
        order_by = asc(order_column)
    else:
        order_by = desc(order_column)
    
    # 查询文档列表
    offset = (page - 1) * limit
    docs_result = await db.execute(
        select(Document)
        .where(and_(*conditions))
        .order_by(order_by)
        .offset(offset)
        .limit(limit)
    )
    documents = docs_result.scalars().all()
    
    # 查询统计信息
    doc_ids = [doc.id for doc in documents]
    stats_result = await db.execute(
        select(DocumentStats).where(DocumentStats.document_id.in_(doc_ids))
    )
    stats_map = {stat.document_id: stat for stat in stats_result.scalars().all()}
    
    # 构建响应
    doc_items = []
    for doc in documents:
        stat = stats_map.get(doc.id)
        # 限制预览内容长度
        preview_content = doc.content[:200] + "..." if len(doc.content) > 200 else doc.content
        
        doc_items.append(DocumentListItem(
            id=doc.id,
            title=doc.title,
            content=preview_content,
            excerpt=doc.excerpt,
            authorId=doc.author_id,
            folderId=doc.folder_id,
            categoryId=doc.category_id,
            isPublic=doc.is_public,
            status=doc.status,
            tags=doc.tags,
            createdAt=doc.created_at,
            updatedAt=doc.updated_at,
            stats=DocumentStatsResponse(
                viewCount=stat.view_count if stat else 0,
                likeCount=stat.like_count if stat else 0,
                shareCount=stat.share_count if stat else 0,
                commentCount=stat.comment_count if stat else 0
            )
        ))
    
    response_data = {
        "documents": doc_items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "totalPages": ceil(total / limit) if total > 0 else 0
        }
    }
    
    return ResponseModel(code=200, data=response_data)


@router.post("/documents/batch", response_model=ResponseModel)
async def batch_documents(
    batch_data: DocumentBatchAction,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    批量操作文档
    """
    results = []
    success_count = 0
    failed_count = 0
    
    for doc_id in batch_data.documentIds:
        try:
            # 查询文档
            doc_result = await db.execute(
                select(Document).where(
                    and_(
                        Document.id == doc_id,
                        Document.author_id == current_user_id
                    )
                )
            )
            document = doc_result.scalar_one_or_none()
            
            if not document:
                results.append(DocumentBatchResult(
                    id=doc_id,
                    success=False,
                    message="文档不存在或无权操作"
                ))
                failed_count += 1
                continue
            
            # 执行操作
            if batch_data.action == "delete":
                await db.delete(document)
            elif batch_data.action == "move":
                folder_id = batch_data.data.get("folderId") if batch_data.data else None
                document.folder_id = folder_id
                document.updated_at = datetime.now()
            elif batch_data.action == "updateStatus":
                new_status = batch_data.data.get("status") if batch_data.data else None
                if new_status:
                    document.status = new_status
                    document.updated_at = datetime.now()
            elif batch_data.action == "updateCategory":
                category_id = batch_data.data.get("categoryId") if batch_data.data else None
                document.category_id = category_id
                document.updated_at = datetime.now()
            
            results.append(DocumentBatchResult(
                id=doc_id,
                success=True,
                message="操作成功"
            ))
            success_count += 1
            
        except Exception as e:
            results.append(DocumentBatchResult(
                id=doc_id,
                success=False,
                message=str(e)
            ))
            failed_count += 1
    
    await db.commit()
    
    return ResponseModel(
        code=200,
        message="批量操作成功",
        data={
            "successCount": success_count,
            "failedCount": failed_count,
            "results": results
        }
    )


@router.get("/documents/{document_id}/stats", response_model=ResponseModel)
async def get_document_stats(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    获取文档统计信息
    """
    # 查询文档
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # 权限检查
    if document.author_id != current_user_id and not document.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此文档"
        )
    
    # 查询统计信息
    stats_result = await db.execute(
        select(DocumentStats).where(DocumentStats.document_id == document_id)
    )
    stats = stats_result.scalar_one_or_none()
    
    if not stats:
        # 如果没有统计记录，创建一个
        stats = DocumentStats(
            document_id=document_id,
            view_count=0,
            like_count=0,
            share_count=0,
            comment_count=0
        )
        db.add(stats)
        await db.commit()
        await db.refresh(stats)
    
    response_data = DocumentStatsDetailResponse(
        documentId=document_id,
        viewCount=stats.view_count,
        likeCount=stats.like_count,
        shareCount=stats.share_count,
        commentCount=stats.comment_count,
        updatedAt=stats.updated_at
    )
    
    return ResponseModel(code=200, data=response_data)


@router.post("/documents/{document_id}/view", response_model=ResponseModel)
async def increment_document_view(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    增加文档查看次数
    """
    # 查询文档
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = doc_result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文档不存在"
        )
    
    # 权限检查
    if document.author_id != current_user_id and not document.is_public:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此文档"
        )
    
    # 查询统计信息
    stats_result = await db.execute(
        select(DocumentStats).where(DocumentStats.document_id == document_id)
    )
    stats = stats_result.scalar_one_or_none()
    
    if not stats:
        stats = DocumentStats(
            document_id=document_id,
            view_count=1,
            like_count=0,
            share_count=0,
            comment_count=0
        )
        db.add(stats)
    else:
        stats.view_count += 1
        stats.updated_at = datetime.now()
    
    await db.commit()
    await db.refresh(stats)
    
    return ResponseModel(
        code=200,
        data={
            "documentId": document_id,
            "viewCount": stats.view_count,
            "updatedAt": stats.updated_at
        }
    )

