"""
清空数据库中除用户表外的所有数据
"""
import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text


async def clear_all_data():
    """清空除用户表外的所有表数据"""
    try:
        async with AsyncSessionLocal() as session:
            print("开始清空数据...")
            
            # 按照依赖关系的顺序删除数据（先删除依赖表，后删除被依赖表）
            tables = [
                ('document_stats', '文档统计'),
                ('comments', '评论'),
                ('documents', '文档'),
                ('folders', '文件夹'),
                ('categories', '分类')
            ]
            
            total_deleted = 0
            
            for table_name, table_desc in tables:
                # 先查询数据量
                count_result = await session.execute(
                    text(f"SELECT COUNT(*) FROM public.{table_name}")
                )
                count = count_result.scalar()
                
                if count > 0:
                    # 删除数据
                    await session.execute(
                        text(f"DELETE FROM public.{table_name}")
                    )
                    await session.commit()
                    print(f"✅ 清空 {table_desc} 表: 删除了 {count} 条记录")
                    total_deleted += count
                else:
                    print(f"⚪ {table_desc} 表: 已经是空的")
            
            print(f"\n总计删除了 {total_deleted} 条记录")
            
            # 重置序列（自增ID）
            print("\n重置自增ID序列...")
            sequences = [
                ('folders_id_seq', '文件夹'),
                ('documents_id_seq', '文档'),
                ('categories_id_seq', '分类'),
                ('comments_id_seq', '评论')
            ]
            
            for seq_name, seq_desc in sequences:
                await session.execute(
                    text(f"ALTER SEQUENCE public.{seq_name} RESTART WITH 1")
                )
                await session.commit()
                print(f"✅ 重置 {seq_desc} ID序列")
            
            # 验证用户表是否保留
            user_count_result = await session.execute(
                text("SELECT COUNT(*) FROM public.user")
            )
            user_count = user_count_result.scalar()
            
            print(f"\n✅ 用户表保留: {user_count} 个用户")
            print("\n🎉 数据清空完成！")
            
    except Exception as e:
        print(f"❌ 错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("=" * 60)
    print("清空数据库（保留用户表）")
    print("=" * 60)
    
    # 确认操作
    print("\n⚠️  警告: 此操作将删除以下表的所有数据:")
    print("  - folders (文件夹)")
    print("  - documents (文档)")
    print("  - document_stats (文档统计)")
    print("  - categories (分类)")
    print("  - comments (评论)")
    print("\n✅ 用户表 (user) 的数据将被保留\n")
    
    confirm = input("确认执行此操作? (输入 'yes' 确认): ")
    
    if confirm.lower() == 'yes':
        asyncio.run(clear_all_data())
    else:
        print("\n❌ 操作已取消")

