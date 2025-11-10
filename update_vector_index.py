"""
更新用户文档的向量索引（直接调用服务，不通过API）
"""
import asyncio
import os
from sqlalchemy import select, delete
from app.db.database import AsyncSessionLocal
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.vectorizer import DocumentVectorizer


async def update_user_vector_index(user_id: int = 1):
    """更新用户所有文档的向量索引"""
    
    # 1. 获取用户的所有文档
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document.id, Document.title, Document.content)
            .where(Document.author_id == user_id)
        )
        docs = result.fetchall()
    
    print("=" * 80)
    print(f"开始更新用户 {user_id} 的文档向量索引")
    print(f"总文档数: {len(docs)}")
    print("=" * 80)
    print()
    
    if not docs:
        print("⚠️  该用户没有文档，无需向量化")
        return
    
    # 2. 创建向量化服务
    embedding_api_key = os.getenv("EMBEDDING_API_KEY") or "sk-BgRaMMUf3rFV7WszBwp6GjSNSqJLoZhSTILfka4bJwNxLDiw"
    embedding_api_base = os.getenv("EMBEDDING_API_BASE") or "https://aiproxy.bja.sealos.run/v1"
    embedding_model = os.getenv("EMBEDDING_MODEL") or "qwen3-embedding-0.6b"
    
    vectorizer = DocumentVectorizer(
        api_key=embedding_api_key,
        api_base=embedding_api_base,
        model=embedding_model
    )
    
    # 3. 批量向量化
    success_count = 0
    fail_count = 0
    total_chunks = 0
    total_tokens = 0
    
    async with AsyncSessionLocal() as db:
        for doc in docs:
            doc_id, doc_title, doc_content = doc
            
            try:
                print(f"📄 [{doc_id}] {doc_title}")
                
                # 删除旧的chunks
                await db.execute(
                    delete(DocumentChunk).where(DocumentChunk.document_id == doc_id)
                )
                await db.commit()
                
                # 处理文档（分块 + 向量化）
                chunks_data = await vectorizer.process_document(
                    content=doc_content or "",
                    metadata={
                        'document_title': doc_title,
                        'author_id': user_id
                    }
                )
                
                if not chunks_data:
                    print(f"  ⚠️  文档内容为空，跳过")
                    continue
                
                # 保存新的chunks
                for chunk_data in chunks_data:
                    chunk = DocumentChunk(
                        document_id=doc_id,
                        content=chunk_data['content'],
                        embedding=chunk_data['embedding'],
                        chunk_index=chunk_data['chunk_index'],
                        token_count=chunk_data['token_count'],
                        chunk_metadata=chunk_data['metadata']
                    )
                    db.add(chunk)
                    total_tokens += chunk_data['token_count']
                
                await db.commit()
                
                print(f"  ✅ 成功！生成 {len(chunks_data)} 个分块，共 {sum(c['token_count'] for c in chunks_data)} tokens")
                success_count += 1
                total_chunks += len(chunks_data)
                
            except Exception as e:
                print(f"  ❌ 失败！错误: {str(e)}")
                fail_count += 1
                await db.rollback()
            
            print()
            
            # 避免API限流，稍作延迟
            await asyncio.sleep(0.5)
    
    # 4. 显示统计
    print("=" * 80)
    print("向量化完成！")
    print(f"成功: {success_count} 个文档")
    print(f"失败: {fail_count} 个文档")
    print(f"总分块数: {total_chunks}")
    print(f"总Token数: {total_tokens}")
    print("=" * 80)
    
    # 5. 查看最终统计
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_([doc[0] for doc in docs]))
        )
        chunks = result.scalars().all()
        
        print()
        print("向量索引统计:")
        print(f"  总Chunk数: {len(chunks)}")
        print(f"  平均每文档: {len(chunks) / success_count if success_count > 0 else 0:.1f} 个chunks")


if __name__ == "__main__":
    asyncio.run(update_user_vector_index(user_id=1))

