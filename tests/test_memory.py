"""
测试记忆模块功能
"""
import asyncio
import uuid
from app.agents.memory import DatabaseConversationMemory
from app.db.database import AsyncSessionLocal
from app.models.agent_session import AgentSession
from app.models.agent_message import AgentMessage
from sqlalchemy import select, delete


async def cleanup_test_data(session_id: str, user_id: int):
    """清理测试数据"""
    async with AsyncSessionLocal() as session:
        # 删除消息
        await session.execute(
            delete(AgentMessage).where(AgentMessage.session_id == session_id)
        )
        # 删除会话
        await session.execute(
            delete(AgentSession).where(AgentSession.session_id == session_id)
        )
        await session.commit()
    print(f"🧹 已清理测试数据 (Session: {session_id})")


async def test_basic_memory_operations():
    """测试基本记忆操作"""
    print("\n" + "="*60)
    print("测试 1: 基本记忆操作")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    
    try:
        # 创建记忆实例
        memory = DatabaseConversationMemory(
            session_id=session_id,
            user_id=user_id,
            agent_type="writing",
            return_messages=True
        )
        print(f"✅ 创建记忆实例 (Session: {session_id})")
        
        # 测试1: 保存用户消息
        await memory.save_user_message(
            content="你好，我想写一篇关于AI的文章",
            metadata={"document_id": 123, "intent": "writing"}
        )
        print("✅ 保存用户消息成功")
        
        # 测试2: 保存助手消息
        await memory.save_assistant_message(
            content="好的，我来帮您写一篇关于AI的文章。",
            metadata={"tool_used": "document_analyzer"}
        )
        print("✅ 保存助手消息成功")
        
        # 测试3: 加载历史消息
        await memory._load_memory_variables_async()
        history = memory.chat_memory.messages
        print(f"✅ 加载历史消息成功，共 {len(history)} 条")
        for i, msg in enumerate(history):
            role = "用户" if msg.__class__.__name__ == "HumanMessage" else "助手"
            content_preview = msg.content[:50] + "..." if len(msg.content) > 50 else msg.content
            print(f"   [{i+1}] {role}: {content_preview}")
        
        # 测试4: 获取消息历史（字典格式）
        message_history = await memory.get_message_history()
        print(f"✅ 获取消息历史成功，共 {len(message_history)} 条")
        for msg in message_history:
            print(f"   - {msg['role']}: {msg['content'][:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id, user_id)


async def test_memory_persistence():
    """测试记忆持久化（跨实例）"""
    print("\n" + "="*60)
    print("测试 2: 记忆持久化（跨实例）")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    
    try:
        # 第一个记忆实例：保存消息
        memory1 = DatabaseConversationMemory(
            session_id=session_id,
            user_id=user_id,
            agent_type="writing"
        )
        
        await memory1.save_user_message("第一轮对话：什么是人工智能？")
        await memory1.save_assistant_message("人工智能是计算机科学的一个分支...")
        await memory1.save_user_message("第二轮对话：AI有哪些应用？")
        await memory1.save_assistant_message("AI在医疗、金融、自动驾驶等领域有广泛应用。")
        print("✅ 第一个实例：保存了 4 条消息")
        
        # 第二个记忆实例：加载历史（模拟新会话）
        memory2 = DatabaseConversationMemory(
            session_id=session_id,
            user_id=user_id,
            agent_type="writing"
        )
        await memory2._load_memory_variables_async()
        
        history = memory2.chat_memory.messages
        print(f"✅ 第二个实例：成功加载了 {len(history)} 条历史消息")
        
        # 验证消息顺序
        assert len(history) == 4, f"期望 4 条消息，实际 {len(history)} 条"
        assert history[0].content == "第一轮对话：什么是人工智能？"
        assert history[1].content == "人工智能是计算机科学的一个分支..."
        assert history[2].content == "第二轮对话：AI有哪些应用？"
        assert history[3].content == "AI在医疗、金融、自动驾驶等领域有广泛应用。"
        print("✅ 消息顺序验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id, user_id)


async def test_save_context():
    """测试 LangChain save_context 方法"""
    print("\n" + "="*60)
    print("测试 3: LangChain save_context 方法")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    
    try:
        memory = DatabaseConversationMemory(
            session_id=session_id,
            user_id=user_id,
            agent_type="writing"
        )
        
        # 使用 LangChain 的 save_context 方法
        memory.save_context(
            inputs={"input": "用户说：帮我写一篇文章"},
            outputs={"output": "助手回复：好的，我来帮您写文章"}
        )
        
        # 等待异步保存完成
        await asyncio.sleep(0.5)
        
        # 验证消息已保存
        await memory._load_memory_variables_async()
        history = memory.chat_memory.messages
        print(f"✅ save_context 保存了 {len(history)} 条消息")
        
        if len(history) >= 2:
            print(f"   用户消息: {history[-2].content[:50]}...")
            print(f"   助手消息: {history[-1].content[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id, user_id)


async def test_message_metadata():
    """测试消息元数据"""
    print("\n" + "="*60)
    print("测试 4: 消息元数据")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    
    try:
        memory = DatabaseConversationMemory(
            session_id=session_id,
            user_id=user_id,
            agent_type="writing"
        )
        
        # 保存带元数据的消息
        await memory.save_user_message(
            content="分析文档结构",
            metadata={
                "document_id": 123,
                "action": "analyze",
                "timestamp": "2024-01-01T00:00:00"
            }
        )
        
        await memory.save_assistant_message(
            content="文档分析完成",
            tool_calls={"tool": "document_analyzer", "args": {"doc_id": 123}},
            tool_results={"paragraphs": 5, "words": 1000},
            metadata={"processing_time": 1.5}
        )
        
        # 验证元数据
        message_history = await memory.get_message_history()
        user_msg = message_history[0]
        assistant_msg = message_history[1]
        
        print(f"✅ 用户消息元数据: {user_msg['metadata']}")
        print(f"✅ 助手消息元数据: {assistant_msg['metadata']}")
        print(f"✅ 工具调用记录: {assistant_msg.get('toolCalls')}")
        print(f"✅ 工具结果: {assistant_msg.get('toolResults')}")
        
        assert user_msg['metadata'].get('document_id') == 123
        assert assistant_msg.get('toolCalls') is not None
        assert assistant_msg.get('toolResults') is not None
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id, user_id)


async def test_clear_memory():
    """测试清空记忆"""
    print("\n" + "="*60)
    print("测试 5: 清空记忆")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    
    try:
        memory = DatabaseConversationMemory(
            session_id=session_id,
            user_id=user_id,
            agent_type="writing"
        )
        
        # 保存一些消息
        await memory.save_user_message("消息1")
        await memory.save_assistant_message("回复1")
        await memory.save_user_message("消息2")
        
        # 验证消息已保存
        history = await memory.get_message_history()
        print(f"✅ 保存了 {len(history)} 条消息")
        
        # 清空记忆
        memory.clear()
        await asyncio.sleep(0.5)  # 等待异步删除完成
        
        # 验证消息已删除
        history_after = await memory.get_message_history()
        print(f"✅ 清空后剩余 {len(history_after)} 条消息")
        
        assert len(history_after) == 0, "清空后应该没有消息"
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id, user_id)


async def test_session_isolation():
    """测试会话隔离（不同会话的消息互不影响）"""
    print("\n" + "="*60)
    print("测试 6: 会话隔离")
    print("="*60)
    
    session_id_1 = f"test_session_1_{uuid.uuid4().hex[:8]}"
    session_id_2 = f"test_session_2_{uuid.uuid4().hex[:8]}"
    user_id = 1
    
    try:
        # 会话1
        memory1 = DatabaseConversationMemory(
            session_id=session_id_1,
            user_id=user_id,
            agent_type="writing"
        )
        await memory1.save_user_message("会话1的消息")
        await memory1.save_assistant_message("会话1的回复")
        
        # 会话2
        memory2 = DatabaseConversationMemory(
            session_id=session_id_2,
            user_id=user_id,
            agent_type="writing"
        )
        await memory2.save_user_message("会话2的消息")
        await memory2.save_assistant_message("会话2的回复")
        
        # 验证隔离
        history1 = await memory1.get_message_history()
        history2 = await memory2.get_message_history()
        
        print(f"✅ 会话1有 {len(history1)} 条消息")
        print(f"✅ 会话2有 {len(history2)} 条消息")
        
        assert len(history1) == 2, "会话1应该有2条消息"
        assert len(history2) == 2, "会话2应该有2条消息"
        assert history1[0]['content'] == "会话1的消息"
        assert history2[0]['content'] == "会话2的消息"
        
        print("✅ 会话隔离验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id_1, user_id)
        await cleanup_test_data(session_id_2, user_id)


async def test_message_order():
    """测试消息顺序"""
    print("\n" + "="*60)
    print("测试 7: 消息顺序")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    
    try:
        memory = DatabaseConversationMemory(
            session_id=session_id,
            user_id=user_id,
            agent_type="writing"
        )
        
        # 快速连续保存多条消息
        messages = [
            ("user", "消息1"),
            ("assistant", "回复1"),
            ("user", "消息2"),
            ("assistant", "回复2"),
            ("user", "消息3"),
        ]
        
        for role, content in messages:
            if role == "user":
                await memory.save_user_message(content)
            else:
                await memory.save_assistant_message(content)
        
        # 验证顺序
        history = await memory.get_message_history()
        print(f"✅ 保存了 {len(history)} 条消息")
        
        for i, msg in enumerate(history):
            expected_content = messages[i][1]
            actual_content = msg['content']
            assert actual_content == expected_content, f"消息{i}顺序错误: 期望 '{expected_content}', 实际 '{actual_content}'"
            print(f"   [{i+1}] {msg['role']}: {msg['content']} (order: {msg['messageOrder']})")
        
        print("✅ 消息顺序验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id, user_id)


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试记忆模块")
    print("="*60)
    
    tests = [
        ("基本记忆操作", test_basic_memory_operations),
        ("记忆持久化", test_memory_persistence),
        ("save_context方法", test_save_context),
        ("消息元数据", test_message_metadata),
        ("清空记忆", test_clear_memory),
        ("会话隔离", test_session_isolation),
        ("消息顺序", test_message_order),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ 测试 '{test_name}' 发生异常: {str(e)}")
            results.append((test_name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {test_name}")
    
    print(f"\n总计: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  有 {total - passed} 个测试失败")


if __name__ == "__main__":
    asyncio.run(main())

