"""
批量向量化用户的所有文档
"""
import asyncio
import httpx
from sqlalchemy import select, func
from app.db.database import AsyncSessionLocal
from app.models.document import Document


async def vectorize_all_user_documents(user_id: int = 1):
    """批量向量化用户的所有文档"""
    
    # 1. 获取用户的所有文档
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Document.id, Document.title)
            .where(Document.author_id == user_id)
        )
        docs = result.fetchall()
    
    print(f"=" * 60)
    print(f"开始向量化用户 {user_id} 的文档")
    print(f"总文档数: {len(docs)}")
    print(f"=" * 60)
    print()
    
    # 2. 批量向量化
    success_count = 0
    fail_count = 0
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for doc in docs:
            doc_id = doc.id
            doc_title = doc.title
            
            try:
                print(f"正在向量化: [{doc_id}] {doc_title}")
                
                # 调用向量化API
                response = await client.post(
                    f"http://localhost:8000/api/vectorization/documents/{doc_id}",
                    headers={"Authorization": f"Bearer {user_id}"}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ 成功！生成 {data['chunkCount']} 个分块，共 {data['totalTokens']} tokens")
                    success_count += 1
                else:
                    print(f"  ❌ 失败！状态码: {response.status_code}")
                    print(f"  错误信息: {response.text}")
                    fail_count += 1
                    
            except Exception as e:
                print(f"  ❌ 异常: {str(e)}")
                fail_count += 1
            
            print()
            
            # 避免API限流，稍作延迟
            await asyncio.sleep(0.5)
    
    # 3. 显示统计
    print("=" * 60)
    print("向量化完成！")
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")
    print("=" * 60)
    
    # 4. 查看最终统计
    from app.models.document_chunk import DocumentChunk
    
    async with AsyncSessionLocal() as db:
        
        # 统计chunks
        result = await db.execute(
            select(func.count(DocumentChunk.id))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.author_id == user_id)
        )
        chunk_count = result.scalar()
        
        # 统计tokens
        result = await db.execute(
            select(func.sum(DocumentChunk.token_count))
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.author_id == user_id)
        )
        total_tokens = result.scalar() or 0
        
        print()
        print("用户知识库统计:")
        print(f"  文档数: {len(docs)}")
        print(f"  分块数: {chunk_count}")
        print(f"  总Tokens: {total_tokens}")


if __name__ == "__main__":
    asyncio.run(vectorize_all_user_documents(user_id=1))

