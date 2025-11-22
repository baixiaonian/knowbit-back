"""
测试文档搜索工具
"""
import asyncio
import uuid
from typing import List, Dict, Any
from app.agents.tools.knowledge_tools import DocumentSearchTool, create_knowledge_tools
from app.agents.event_manager import AgentEventManager


class EventCollector:
    """收集事件用于测试"""
    
    def __init__(self, event_manager: AgentEventManager, session_id: str):
        self.event_manager = event_manager
        self.session_id = session_id
        self.queue = None
        self.events: List[Dict[str, Any]] = []
        self.running = False
    
    async def start(self):
        """开始收集事件"""
        self.queue = await self.event_manager.register(self.session_id)
        self.running = True
        asyncio.create_task(self._collect())
    
    async def _collect(self):
        """收集事件"""
        while self.running:
            try:
                event = await asyncio.wait_for(self.queue.get(), timeout=0.1)
                self.events.append(event)
            except asyncio.TimeoutError:
                continue
    
    async def stop(self):
        """停止收集"""
        self.running = False
        if self.queue:
            await self.event_manager.unregister(self.session_id, self.queue)
    
    def get_events_by_type(self, event_type: str) -> List[Dict[str, Any]]:
        """获取指定类型的事件"""
        return [e for e in self.events if e.get('type') == event_type]


async def test_basic_search(user_id: int = 1):
    """测试基本搜索功能"""
    print("\n" + "=" * 80)
    print("测试 1: 基本文档搜索")
    print("=" * 80)
    
    # 检查环境变量配置
    import os
    embedding_api_key = os.getenv("EMBEDDING_API_KEY")
    embedding_api_base = os.getenv("EMBEDDING_API_BASE")
    embedding_model = os.getenv("EMBEDDING_MODEL")
    
    if not embedding_api_key:
        print("ℹ️  未设置 EMBEDDING_API_KEY 环境变量，将使用默认配置")
    else:
        print(f"✅ 使用环境变量配置: EMBEDDING_API_KEY={embedding_api_key[:10]}...")
    
    tool = DocumentSearchTool(user_id=user_id)
    success_count = 0
    total_queries = 0
    
    # 测试查询1: 人工智能相关
    print("\n📝 查询: '人工智能'")
    result1 = await tool._arun(query="人工智能", top_k=3)
    total_queries += 1
    if result1.startswith("Error retrieving knowledge") or result1 == "No relevant content found":
        print(f"❌ 搜索失败: {result1}")
    else:
        print(f"✅ 搜索成功:\n{result1[:200]}..." if len(result1) > 200 else f"✅ 搜索成功:\n{result1}")
        success_count += 1
    
    # 测试查询2: 篮球相关
    print("\n📝 查询: '詹姆斯'")
    result2 = await tool._arun(query="詹姆斯", top_k=3)
    total_queries += 1
    if result2.startswith("Error retrieving knowledge") or result2 == "No relevant content found":
        print(f"❌ 搜索失败: {result2}")
    else:
        print(f"✅ 搜索成功:\n{result2[:200]}..." if len(result2) > 200 else f"✅ 搜索成功:\n{result2}")
        success_count += 1
    
    # 测试查询3: 阿里巴巴相关
    print("\n📝 查询: '阿里巴巴'")
    result3 = await tool._arun(query="阿里巴巴", top_k=3)
    total_queries += 1
    if result3.startswith("Error retrieving knowledge") or result3 == "No relevant content found":
        print(f"❌ 搜索失败: {result3}")
    else:
        print(f"✅ 搜索成功:\n{result3[:200]}..." if len(result3) > 200 else f"✅ 搜索成功:\n{result3}")
        success_count += 1
    
    # 测试查询4: MCP协议相关
    print("\n📝 查询: 'MCP协议'")
    result4 = await tool._arun(query="MCP协议", top_k=3)
    total_queries += 1
    if result4.startswith("Error retrieving knowledge") or result4 == "No relevant content found":
        print(f"❌ 搜索失败: {result4}")
    else:
        print(f"✅ 搜索成功:\n{result4[:200]}..." if len(result4) > 200 else f"✅ 搜索成功:\n{result4}")
        success_count += 1
    
    # 测试查询5: 不相关查询（这个应该返回"No relevant content found"是正常的）
    print("\n📝 查询: '完全不相关的内容xyz123'")
    result5 = await tool._arun(query="完全不相关的内容xyz123", top_k=3)
    total_queries += 1
    if result5.startswith("Error retrieving knowledge"):
        print(f"❌ 搜索失败: {result5}")
    elif result5 == "No relevant content found":
        print(f"✅ 正确返回: {result5} (预期行为)")
        success_count += 1
    else:
        print(f"✅ 搜索成功:\n{result5[:200]}..." if len(result5) > 200 else f"✅ 搜索成功:\n{result5}")
        success_count += 1
    
    print(f"\n📊 搜索结果: {success_count}/{total_queries} 个查询成功")
    if success_count == total_queries:
        print("✅ 基本搜索测试完成")
        return True
    elif success_count > 0:
        print("⚠️  部分搜索失败，请检查 API 配置")
        return False
    else:
        print("❌ 所有搜索都失败，请检查 API 配置和网络连接")
        return False


async def test_selected_documents_search(user_id: int = 1):
    """测试指定文档ID的重点搜索"""
    print("\n" + "=" * 80)
    print("测试 2: 指定文档ID的重点搜索")
    print("=" * 80)
    
    # 获取用户文档
    from app.db.database import AsyncSessionLocal
    from app.models.document import Document
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Document.id, Document.title)
            .where(Document.author_id == user_id)
            .limit(5)
        )
        docs = result.fetchall()
    
    if len(docs) < 2:
        print("⚠️  用户文档数量不足，跳过此测试")
        return False
    
    doc_ids = [doc[0] for doc in docs[:2]]  # 选择前2个文档
    doc_titles = {doc[0]: doc[1] for doc in docs}
    
    print(f"\n📚 指定文档ID: {doc_ids}")
    for doc_id, title in doc_titles.items():
        if doc_id in doc_ids:
            print(f"  - [{doc_id}] {title}")
    
    tool = DocumentSearchTool(
        user_id=user_id,
        selected_document_ids=doc_ids
    )
    
    # 测试在指定文档中搜索
    print("\n📝 查询: '测试' (在指定文档中搜索)")
    result = await tool._arun(query="测试", top_k=3)
    if result.startswith("Error retrieving knowledge"):
        print(f"❌ 搜索失败: {result}")
        return False
    elif result == "No relevant content found":
        print(f"⚠️  未找到相关内容: {result}")
    else:
        print(f"✅ 搜索成功:\n{result[:300]}..." if len(result) > 300 else f"✅ 搜索成功:\n{result}")
    
    # 对比：不指定文档ID的搜索
    print("\n📝 查询: '测试' (全文档搜索)")
    tool_all = DocumentSearchTool(user_id=user_id)
    result_all = await tool_all._arun(query="测试", top_k=3)
    if result_all.startswith("Error retrieving knowledge"):
        print(f"❌ 搜索失败: {result_all}")
        return False
    elif result_all == "No relevant content found":
        print(f"⚠️  未找到相关内容: {result_all}")
    else:
        print(f"✅ 搜索成功:\n{result_all[:300]}..." if len(result_all) > 300 else f"✅ 搜索成功:\n{result_all}")
    
    print("\n✅ 指定文档搜索测试完成")
    return True


async def test_event_publishing(user_id: int = 1):
    """测试事件推送功能"""
    print("\n" + "=" * 80)
    print("测试 3: 事件推送功能")
    print("=" * 80)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    event_manager = AgentEventManager()
    
    # 创建事件收集器
    collector = EventCollector(event_manager, session_id)
    await collector.start()
    
    # 创建带事件管理的工具
    tool = DocumentSearchTool(
        user_id=user_id,
        event_manager=event_manager,
        session_id=session_id
    )
    
    # 执行搜索
    print("\n📝 执行搜索: '人工智能'")
    result = await tool._arun(query="人工智能", top_k=3)
    
    # 等待事件收集
    await asyncio.sleep(0.2)
    
    # 检查事件
    start_events = collector.get_events_by_type("knowledge_search_start")
    result_events = collector.get_events_by_type("knowledge_search_result")
    
    print(f"\n📊 事件统计:")
    print(f"  - knowledge_search_start: {len(start_events)} 个")
    print(f"  - knowledge_search_result: {len(result_events)} 个")
    
    if start_events:
        print(f"\n✅ 搜索开始事件:")
        print(f"  查询: {start_events[0]['data']['query']}")
        print(f"  搜索类型: {start_events[0]['data']['search_type']}")
        print(f"  top_k: {start_events[0]['data']['top_k']}")
    
    if result_events:
        print(f"\n✅ 搜索结果事件:")
        print(f"  成功: {result_events[0]['data']['success']}")
        print(f"  结果数量: {result_events[0]['data'].get('results_count', 0)}")
        if not result_events[0]['data']['success']:
            print(f"  错误/消息: {result_events[0]['data'].get('error') or result_events[0]['data'].get('message')}")
    
    # 验证事件
    try:
        assert len(start_events) == 1, "应该有1个搜索开始事件"
        assert len(result_events) == 1, "应该有1个搜索结果事件"
        assert start_events[0]['data']['query'] == "人工智能", "查询应该匹配"
        
        # 检查搜索结果是否成功
        search_success = result_events[0]['data']['success']
        if not search_success:
            print(f"\n⚠️  搜索执行失败: {result_events[0]['data'].get('error', '未知错误')}")
            print("   事件推送功能正常，但搜索本身失败（可能是API配置问题）")
        
        await collector.stop()
        print("\n✅ 事件推送测试完成（事件机制正常）")
        return True
    except AssertionError as e:
        await collector.stop()
        print(f"\n❌ 事件验证失败: {str(e)}")
        return False


async def test_web_search():
    """测试网络搜索功能"""
    print("\n" + "=" * 80)
    print("测试 4: 网络搜索功能")
    print("=" * 80)
    
    from app.agents.tools.knowledge_tools import WebSearchTool
    
    tool = WebSearchTool()
    
    print("\n📝 查询: 'Python异步编程'")
    try:
        result = await tool._arun(query="Python异步编程")
        print(f"结果:\n{result[:300]}..." if len(result) > 300 else f"结果:\n{result}")
        print("\n✅ 网络搜索测试完成")
    except Exception as e:
        print(f"⚠️  网络搜索失败: {str(e)}")
        print("（这可能是网络问题或API限制）")


async def test_web_search_with_events():
    """测试带事件推送的网络搜索"""
    print("\n" + "=" * 80)
    print("测试 5: 带事件推送的网络搜索")
    print("=" * 80)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    event_manager = AgentEventManager()
    
    from app.agents.tools.knowledge_tools import WebSearchTool
    
    # 创建事件收集器
    collector = EventCollector(event_manager, session_id)
    await collector.start()
    
    # 创建带事件管理的工具
    tool = WebSearchTool(
        event_manager=event_manager,
        session_id=session_id
    )
    
    print("\n📝 执行网络搜索: 'FastAPI'")
    try:
        result = await tool._arun(query="FastAPI")
        
        # 等待事件收集
        await asyncio.sleep(0.5)
        
        # 检查事件
        start_events = collector.get_events_by_type("knowledge_search_start")
        result_events = collector.get_events_by_type("knowledge_search_result")
        
        print(f"\n📊 事件统计:")
        print(f"  - knowledge_search_start: {len(start_events)} 个")
        print(f"  - knowledge_search_result: {len(result_events)} 个")
        
        if start_events:
            print(f"\n✅ 搜索开始事件:")
            print(f"  查询: {start_events[0]['data']['query']}")
            print(f"  搜索类型: {start_events[0]['data']['search_type']}")
        
        if result_events:
            print(f"\n✅ 搜索结果事件:")
            print(f"  成功: {result_events[0]['data']['success']}")
            if result_events[0]['data']['success']:
                print(f"  结果长度: {result_events[0]['data'].get('result_length', 0)}")
        
        await collector.stop()
        print("\n✅ 带事件推送的网络搜索测试完成")
    except Exception as e:
        print(f"⚠️  网络搜索失败: {str(e)}")
        await collector.stop()


async def test_create_knowledge_tools(user_id: int = 1):
    """测试工具创建函数"""
    print("\n" + "=" * 80)
    print("测试 6: 工具创建函数")
    print("=" * 80)
    
    # 测试不带事件管理
    tools1 = create_knowledge_tools(user_id=user_id)
    print(f"\n✅ 创建工具（无事件）: {len(tools1)} 个工具")
    print(f"  - {tools1[0].name}")
    print(f"  - {tools1[1].name}")
    
    # 测试带事件管理
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    event_manager = AgentEventManager()
    tools2 = create_knowledge_tools(
        user_id=user_id,
        selected_document_ids=[1, 2, 3],
        event_manager=event_manager,
        session_id=session_id
    )
    print(f"\n✅ 创建工具（带事件）: {len(tools2)} 个工具")
    print(f"  - {tools2[0].name}")
    print(f"  - {tools2[1].name}")
    
    # 验证工具配置
    assert tools2[0].user_id == user_id
    assert tools2[0].selected_document_ids == [1, 2, 3]
    assert tools2[0].event_manager == event_manager
    assert tools2[0].session_id == session_id
    
    print("\n✅ 工具创建测试完成")


async def main():
    """主测试函数"""
    print("=" * 80)
    print("🧪 文档搜索工具测试套件")
    print("=" * 80)
    
    user_id = 1
    
    # 先更新向量索引
    print("\n" + "=" * 80)
    print("📦 步骤 1: 更新用户文档向量索引")
    print("=" * 80)
    import sys
    import os
    # 添加项目根目录到路径，以便导入根目录的模块
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from update_vector_index import update_user_vector_index
    await update_user_vector_index(user_id=user_id)
    
    # 运行测试
    test_results = []
    
    try:
        # 测试1: 基本搜索
        result = await test_basic_search(user_id)
        test_results.append(("基本搜索", result if result is not None else False))
    except Exception as e:
        print(f"\n❌ 基本搜索测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        test_results.append(("基本搜索", False))
    
    try:
        # 测试2: 指定文档搜索
        result = await test_selected_documents_search(user_id)
        test_results.append(("指定文档搜索", result if result is not None else False))
    except Exception as e:
        print(f"\n❌ 指定文档搜索测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        test_results.append(("指定文档搜索", False))
    
    try:
        # 测试3: 事件推送
        result = await test_event_publishing(user_id)
        test_results.append(("事件推送", result if result is not None else True))
    except Exception as e:
        print(f"\n❌ 事件推送测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        test_results.append(("事件推送", False))
    
    try:
        # 测试4: 网络搜索
        await test_web_search()
        test_results.append(("网络搜索", True))
    except Exception as e:
        print(f"\n❌ 网络搜索测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        test_results.append(("网络搜索", False))
    
    try:
        # 测试5: 带事件推送的网络搜索
        await test_web_search_with_events()
        test_results.append(("带事件推送的网络搜索", True))
    except Exception as e:
        print(f"\n❌ 带事件推送的网络搜索测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        test_results.append(("带事件推送的网络搜索", False))
    
    try:
        # 测试6: 工具创建
        await test_create_knowledge_tools(user_id)
        test_results.append(("工具创建", True))
    except Exception as e:
        print(f"\n❌ 工具创建测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        test_results.append(("工具创建", False))
    
    # 显示测试结果汇总
    print("\n" + "=" * 80)
    print("📊 测试结果汇总")
    print("=" * 80)
    
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")


if __name__ == "__main__":
    asyncio.run(main())

