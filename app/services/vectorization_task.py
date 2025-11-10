"""
文档向量化后台任务服务
"""
import asyncio
import hashlib
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, text, update
from datetime import datetime, timedelta
from typing import List, Optional

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.user_llm_config import UserLLMConfig
from app.services.vectorizer import DocumentVectorizer


class VectorizationTaskService:
    """向量化任务服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @staticmethod
    def compute_content_hash(content: str) -> str:
        """
        计算内容哈希
        
        Args:
            content: 文档内容
            
        Returns:
            MD5哈希值
        """
        return hashlib.md5(content.encode('utf-8')).hexdigest()
    
    async def mark_document_for_vectorization(
        self,
        document_id: int,
        content: str
    ):
        """
        标记文档需要重新向量化
        
        Args:
            document_id: 文档ID
            content: 文档内容
        """
        content_hash = self.compute_content_hash(content)
        
        await self.db.execute(
            update(Document)
            .where(Document.id == document_id)
            .values(
                content_hash=content_hash,
                vectorization_status='pending'
            )
        )
        await self.db.commit()
    
    async def check_if_content_changed(
        self,
        document_id: int,
        new_content: str
    ) -> bool:
        """
        检查文档内容是否真正改变
        
        Args:
            document_id: 文档ID
            new_content: 新内容
            
        Returns:
            是否改变
        """
        result = await self.db.execute(
            select(Document.content_hash)
            .where(Document.id == document_id)
        )
        old_hash = result.scalar_one_or_none()
        
        new_hash = self.compute_content_hash(new_content)
        
        return old_hash != new_hash
    
    async def get_pending_documents(
        self,
        time_threshold: int = 180  # 默认3分钟
    ) -> List[Document]:
        """
        获取待向量化的文档（防抖：3分钟内无更新）
        
        Args:
            time_threshold: 时间阈值（秒），超过这个时间没有更新才处理
            
        Returns:
            待处理文档列表
        """
        threshold_time = datetime.utcnow() - timedelta(seconds=time_threshold)
        
        result = await self.db.execute(
            select(Document)
            .where(
                Document.vectorization_status == 'pending',
                Document.updated_at < threshold_time  # 3分钟内没有更新
            )
            .limit(10)  # 每次处理10个
        )
        
        return result.scalars().all()
    
    async def vectorize_document_task(
        self,
        document: Document
    ) -> bool:
        """
        执行文档向量化任务
        
        Args:
            document: 文档对象
            
        Returns:
            是否成功
        """
        try:
            # 1. 标记为处理中
            document.vectorization_status = 'processing'
            await self.db.commit()
            
            # 2. 获取用户的Embedding配置
            import os
            embedding_api_key = os.getenv("EMBEDDING_API_KEY") or "sk-BgRaMMUf3rFV7WszBwp6GjSNSqJLoZhSTILfka4bJwNxLDiw"
            embedding_api_base = os.getenv("EMBEDDING_API_BASE") or "https://aiproxy.bja.sealos.run/v1"
            embedding_model = os.getenv("EMBEDDING_MODEL") or "qwen3-embedding-0.6b"
            
            # 3. 创建向量化服务
            vectorizer = DocumentVectorizer(
                api_key=embedding_api_key,
                api_base=embedding_api_base,
                model=embedding_model
            )
            
            # 4. 删除旧的chunks
            await self.db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
            )
            await self.db.commit()
            
            # 5. 处理文档
            chunks_data = await vectorizer.process_document(
                content=document.content,
                metadata={
                    'document_title': document.title,
                    'author_id': document.author_id
                }
            )
            
            # 6. 保存新的chunks
            for chunk_data in chunks_data:
                chunk = DocumentChunk(
                    document_id=document.id,
                    content=chunk_data['content'],
                    embedding=chunk_data['embedding'],
                    chunk_index=chunk_data['chunk_index'],
                    token_count=chunk_data['token_count'],
                    chunk_metadata=chunk_data['metadata']
                )
                self.db.add(chunk)
            
            # 7. 更新文档状态
            document.vectorization_status = 'completed'
            document.vectorized_at = datetime.utcnow()
            await self.db.commit()
            
            return True
            
        except Exception as e:
            # 标记为失败
            document.vectorization_status = 'failed'
            await self.db.commit()
            print(f"向量化失败 - 文档{document.id}: {e}")
            return False
    
    async def process_pending_queue(self):
        """
        处理待向量化队列（定时任务调用）
        """
        pending_docs = await self.get_pending_documents(time_threshold=180)
        
        if not pending_docs:
            return
        
        print(f"发现 {len(pending_docs)} 个待向量化文档")
        
        for doc in pending_docs:
            print(f"处理文档 {doc.id}: {doc.title}")
            await self.vectorize_document_task(doc)
            
            # 避免API限流
            await asyncio.sleep(0.5)


async def run_vectorization_worker():
    """
    向量化工作进程（后台运行）
    每分钟检查一次待处理文档
    """
    from app.db.database import AsyncSessionLocal
    
    while True:
        try:
            async with AsyncSessionLocal() as db:
                service = VectorizationTaskService(db)
                await service.process_pending_queue()
        except Exception as e:
            print(f"向量化工作进程错误: {e}")
        
        # 每分钟执行一次
        await asyncio.sleep(60)

