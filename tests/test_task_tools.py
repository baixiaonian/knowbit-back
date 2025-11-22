"""
测试任务工具功能
"""
import asyncio
import json
import uuid
from app.agents.tools.task_tools import (
    create_task_tools,
    TaskCreateTool,
    TaskUpdateTool,
    TaskListTool,
    TASK_STATUS,
    ALLOWED_STATUSES
)
from app.agents.tools.task_storage import task_storage
from app.agents.event_manager import AgentEventManager


class EventCollector:
    """事件收集器，用于测试事件推送"""
    
    def __init__(self, event_manager: AgentEventManager, session_id: str):
        self.event_manager = event_manager
        self.session_id = session_id
        self.events = []
        self.queue = None
        self.receiving_task = None
    
    async def start(self):
        """启动事件收集"""
        self.queue = await self.event_manager.register(self.session_id)
        self.receiving_task = asyncio.create_task(self._collect_events())
    
    async def _collect_events(self):
        """收集事件"""
        try:
            while True:
                event = await self.queue.get()
                if event.get("type") == "session_closed":
                    break
                if event.get("type") in ["task_created", "task_updated"]:
                    self.events.append(event)
        except asyncio.CancelledError:
            pass
    
    async def stop(self):
        """停止事件收集"""
        if self.receiving_task:
            self.receiving_task.cancel()
            try:
                await self.receiving_task
            except asyncio.CancelledError:
                pass
        await self.event_manager.unregister(self.session_id, self.queue)


async def cleanup_test_data(session_id: str):
    """清理测试数据"""
    task_storage.clear_session(session_id)
    print(f"🧹 已清理测试数据 (Session: {session_id})")


async def test_task_create():
    """测试任务创建"""
    print("\n" + "="*60)
    print("测试 1: 任务创建")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    event_manager = AgentEventManager()
    
    try:
        # 创建事件收集器
        collector = EventCollector(event_manager, session_id)
        await collector.start()
        
        # 创建任务工具
        tools = create_task_tools(user_id, event_manager, session_id)
        create_tool = tools[0]
        
        # 测试创建任务
        result_str = await create_tool._arun(description="测试任务1", priority=3)
        result = json.loads(result_str)
        
        print(f"✅ 创建任务成功: {result['message']}")
        print(f"   任务ID: {result['task']['id']}")
        print(f"   描述: {result['task']['description']}")
        print(f"   状态: {result['task']['status']}")
        print(f"   优先级: {result['task']['priority']}")
        
        # 验证任务已创建
        assert result['success'] is True
        assert result['task']['description'] == "测试任务1"
        assert result['task']['status'] == TASK_STATUS["PENDING"]
        assert result['task']['priority'] == 3
        
        # 等待事件推送
        await asyncio.sleep(0.1)
        
        # 验证事件已推送
        assert len(collector.events) > 0
        event = collector.events[0]
        assert event['type'] == 'task_created'
        assert event['data']['id'] == result['task']['id']
        print(f"✅ 事件推送成功: {event['type']}")
        
        await collector.stop()
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id)


async def test_task_update():
    """测试任务更新"""
    print("\n" + "="*60)
    print("测试 2: 任务更新")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    event_manager = AgentEventManager()
    
    try:
        # 创建事件收集器
        collector = EventCollector(event_manager, session_id)
        await collector.start()
        
        # 创建任务工具
        tools = create_task_tools(user_id, event_manager, session_id)
        create_tool = tools[0]
        update_tool = tools[1]
        
        # 先创建任务
        create_result = json.loads(await create_tool._arun(description="测试任务", priority=1))
        task_id = create_result['task']['id']
        print(f"✅ 创建任务: Task#{task_id}")
        
        # 更新任务状态
        update_result_str = await update_tool._arun(task_id=task_id, status=TASK_STATUS["IN_PROGRESS"])
        update_result = json.loads(update_result_str)
        
        print(f"✅ 更新任务成功: {update_result['message']}")
        print(f"   旧状态: {update_result['task']['status']}")
        
        # 验证任务已更新
        assert update_result['success'] is True
        assert update_result['task']['status'] == TASK_STATUS["IN_PROGRESS"]
        
        # 再次更新
        update_result_str = await update_tool._arun(task_id=task_id, status=TASK_STATUS["COMPLETED"])
        update_result = json.loads(update_result_str)
        assert update_result['task']['status'] == TASK_STATUS["COMPLETED"]
        print(f"✅ 再次更新成功: {update_result['task']['status']}")
        
        # 等待事件推送
        await asyncio.sleep(0.1)
        
        # 验证事件已推送（应该有2个更新事件）
        update_events = [e for e in collector.events if e['type'] == 'task_updated']
        assert len(update_events) == 2
        print(f"✅ 事件推送成功: 收到 {len(update_events)} 个更新事件")
        
        await collector.stop()
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id)


async def test_task_list():
    """测试任务查询"""
    print("\n" + "="*60)
    print("测试 3: 任务查询")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    event_manager = AgentEventManager()
    
    try:
        # 创建任务工具
        tools = create_task_tools(user_id, event_manager, session_id)
        create_tool = tools[0]
        list_tool = tools[2]
        
        # 创建多个任务
        tasks_created = []
        for i in range(5):
            result = json.loads(await create_tool._arun(
                description=f"任务{i+1}",
                priority=i
            ))
            tasks_created.append(result['task'])
        
        print(f"✅ 创建了 {len(tasks_created)} 个任务")
        
        # 查询所有任务
        list_result_str = await list_tool._arun()
        list_result = json.loads(list_result_str)
        
        print(f"✅ 查询任务成功: 共 {len(list_result['tasks'])} 个任务")
        print(f"   统计信息: {list_result['summary']}")
        
        # 验证查询结果
        assert list_result['success'] is True
        assert len(list_result['tasks']) == 5
        assert list_result['summary']['total'] == 5
        assert list_result['summary']['pending'] == 5
        
        # 验证任务按优先级排序（优先级高的在前）
        priorities = [t['priority'] for t in list_result['tasks']]
        assert priorities == [4, 3, 2, 1, 0], f"优先级排序错误: {priorities}"
        print("✅ 任务按优先级排序正确")
        
        # 按状态过滤查询
        # 先更新一个任务为 completed
        update_tool = tools[1]
        await update_tool._arun(task_id=tasks_created[0]['id'], status=TASK_STATUS["COMPLETED"])
        
        # 查询已完成的任务
        completed_result_str = await list_tool._arun(status=TASK_STATUS["COMPLETED"])
        completed_result = json.loads(completed_result_str)
        
        assert len(completed_result['tasks']) == 1
        assert completed_result['tasks'][0]['status'] == TASK_STATUS["COMPLETED"]
        print(f"✅ 按状态过滤查询成功: 找到 {len(completed_result['tasks'])} 个已完成任务")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id)


async def test_task_status_validation():
    """测试任务状态验证"""
    print("\n" + "="*60)
    print("测试 4: 任务状态验证")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    event_manager = AgentEventManager()
    
    try:
        # 创建任务工具
        tools = create_task_tools(user_id, event_manager, session_id)
        create_tool = tools[0]
        update_tool = tools[1]
        
        # 创建任务
        create_result = json.loads(await create_tool._arun(description="测试任务", priority=1))
        task_id = create_result['task']['id']
        
        # 测试无效状态
        invalid_result_str = await update_tool._arun(task_id=task_id, status="invalid_status")
        invalid_result = json.loads(invalid_result_str)
        
        assert invalid_result['success'] is False
        assert 'Invalid status' in invalid_result['error']
        print(f"✅ 无效状态验证成功: {invalid_result['error']}")
        
        # 测试所有有效状态
        for status in ALLOWED_STATUSES:
            result_str = await update_tool._arun(task_id=task_id, status=status)
            result = json.loads(result_str)
            assert result['success'] is True
            assert result['task']['status'] == status
            print(f"   ✅ 状态 '{status}' 验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id)


async def test_task_not_found():
    """测试任务不存在的情况"""
    print("\n" + "="*60)
    print("测试 5: 任务不存在处理")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    event_manager = AgentEventManager()
    
    try:
        # 创建任务工具
        tools = create_task_tools(user_id, event_manager, session_id)
        update_tool = tools[1]
        
        # 尝试更新不存在的任务
        result_str = await update_tool._arun(task_id=99999, status=TASK_STATUS["IN_PROGRESS"])
        result = json.loads(result_str)
        
        assert result['success'] is False
        assert 'not found' in result['error'].lower()
        print(f"✅ 任务不存在处理正确: {result['error']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id)


async def test_session_isolation():
    """测试会话隔离"""
    print("\n" + "="*60)
    print("测试 6: 会话隔离")
    print("="*60)
    
    session_id_1 = f"test_session_1_{uuid.uuid4().hex[:8]}"
    session_id_2 = f"test_session_2_{uuid.uuid4().hex[:8]}"
    user_id = 1
    event_manager = AgentEventManager()
    
    try:
        # 会话1
        tools_1 = create_task_tools(user_id, event_manager, session_id_1)
        create_tool_1 = tools_1[0]
        list_tool_1 = tools_1[2]
        
        # 会话2
        tools_2 = create_task_tools(user_id, event_manager, session_id_2)
        create_tool_2 = tools_2[0]
        list_tool_2 = tools_2[2]
        
        # 在会话1创建任务
        result_1 = json.loads(await create_tool_1._arun(description="会话1的任务", priority=1))
        task_id_1 = result_1['task']['id']
        print(f"✅ 会话1创建任务: Task#{task_id_1}")
        
        # 在会话2创建任务
        result_2 = json.loads(await create_tool_2._arun(description="会话2的任务", priority=1))
        task_id_2 = result_2['task']['id']
        print(f"✅ 会话2创建任务: Task#{task_id_2}")
        
        # 验证会话隔离
        list_result_1 = json.loads(await list_tool_1._arun())
        list_result_2 = json.loads(await list_tool_2._arun())
        
        assert len(list_result_1['tasks']) == 1
        assert len(list_result_2['tasks']) == 1
        assert list_result_1['tasks'][0]['id'] == task_id_1
        assert list_result_2['tasks'][0]['id'] == task_id_2
        assert list_result_1['tasks'][0]['description'] == "会话1的任务"
        assert list_result_2['tasks'][0]['description'] == "会话2的任务"
        
        print("✅ 会话隔离验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id_1)
        await cleanup_test_data(session_id_2)


async def test_task_priority():
    """测试任务优先级"""
    print("\n" + "="*60)
    print("测试 7: 任务优先级")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    event_manager = AgentEventManager()
    
    try:
        # 创建任务工具
        tools = create_task_tools(user_id, event_manager, session_id)
        create_tool = tools[0]
        list_tool = tools[2]
        
        # 创建不同优先级的任务
        priorities = [1, 5, 3, 2, 4]
        for priority in priorities:
            await create_tool._arun(description=f"优先级{priority}的任务", priority=priority)
        
        # 查询任务（应该按优先级降序排列）
        list_result_str = await list_tool._arun()
        list_result = json.loads(list_result_str)
        
        # 验证排序（优先级高的在前）
        actual_priorities = [t['priority'] for t in list_result['tasks']]
        expected_priorities = sorted(priorities, reverse=True)
        
        assert actual_priorities == expected_priorities, \
            f"优先级排序错误: 期望 {expected_priorities}, 实际 {actual_priorities}"
        
        print(f"✅ 任务优先级排序正确: {actual_priorities}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id)


async def test_task_summary():
    """测试任务统计"""
    print("\n" + "="*60)
    print("测试 8: 任务统计")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    event_manager = AgentEventManager()
    
    try:
        # 创建任务工具
        tools = create_task_tools(user_id, event_manager, session_id)
        create_tool = tools[0]
        update_tool = tools[1]
        list_tool = tools[2]
        
        # 创建5个任务
        task_ids = []
        for i in range(5):
            result = json.loads(await create_tool._arun(description=f"任务{i+1}", priority=1))
            task_ids.append(result['task']['id'])
        
        # 更新任务状态
        await update_tool._arun(task_id=task_ids[0], status=TASK_STATUS["IN_PROGRESS"])
        await update_tool._arun(task_id=task_ids[1], status=TASK_STATUS["COMPLETED"])
        await update_tool._arun(task_id=task_ids[2], status=TASK_STATUS["COMPLETED"])
        await update_tool._arun(task_id=task_ids[3], status=TASK_STATUS["FAILED"])
        
        # 查询统计
        list_result_str = await list_tool._arun()
        list_result = json.loads(list_result_str)
        
        summary = list_result['summary']
        print(f"✅ 任务统计:")
        print(f"   总数: {summary['total']}")
        print(f"   待处理: {summary['pending']}")
        print(f"   进行中: {summary['in_progress']}")
        print(f"   已完成: {summary['completed']}")
        print(f"   失败: {summary['failed']}")
        
        # 验证统计
        assert summary['total'] == 5
        assert summary['pending'] == 1
        assert summary['in_progress'] == 1
        assert summary['completed'] == 2
        assert summary['failed'] == 1
        
        print("✅ 任务统计验证通过")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id)


async def test_event_pushing():
    """测试事件推送"""
    print("\n" + "="*60)
    print("测试 9: 事件推送")
    print("="*60)
    
    session_id = f"test_session_{uuid.uuid4().hex[:8]}"
    user_id = 1
    event_manager = AgentEventManager()
    
    try:
        # 创建事件收集器
        collector = EventCollector(event_manager, session_id)
        await collector.start()
        
        # 创建任务工具
        tools = create_task_tools(user_id, event_manager, session_id)
        create_tool = tools[0]
        update_tool = tools[1]
        
        # 创建任务
        create_result = json.loads(await create_tool._arun(description="测试任务", priority=1))
        task_id = create_result['task']['id']
        
        # 等待事件
        await asyncio.sleep(0.1)
        
        # 验证创建事件
        created_events = [e for e in collector.events if e['type'] == 'task_created']
        assert len(created_events) == 1
        assert created_events[0]['data']['id'] == task_id
        print(f"✅ 任务创建事件推送成功")
        
        # 更新任务
        await update_tool._arun(task_id=task_id, status=TASK_STATUS["IN_PROGRESS"])
        await update_tool._arun(task_id=task_id, status=TASK_STATUS["COMPLETED"])
        
        # 等待事件
        await asyncio.sleep(0.1)
        
        # 验证更新事件
        updated_events = [e for e in collector.events if e['type'] == 'task_updated']
        assert len(updated_events) == 2
        print(f"✅ 任务更新事件推送成功: 收到 {len(updated_events)} 个更新事件")
        
        # 验证事件数据
        for event in updated_events:
            assert 'old_status' in event['data']
            assert event['data']['id'] == task_id
        
        await collector.stop()
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await cleanup_test_data(session_id)


async def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试任务工具")
    print("="*60)
    
    tests = [
        ("任务创建", test_task_create),
        ("任务更新", test_task_update),
        ("任务查询", test_task_list),
        ("状态验证", test_task_status_validation),
        ("任务不存在处理", test_task_not_found),
        ("会话隔离", test_session_isolation),
        ("任务优先级", test_task_priority),
        ("任务统计", test_task_summary),
        ("事件推送", test_event_pushing),
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

