"""
测试文档工具（使用真实的WebSocket连接）
"""
import asyncio
import json
import uuid
from typing import List, Dict, Any, Optional
from app.agents.tools.document_tools import (
    DocumentReadTool,
    DocumentAnalysisTool,
    ParagraphEditInstructionTool,
    create_document_analysis_tool,
    create_paragraph_edit_tool
)
from app.agents.event_manager import AgentEventManager
from app.db.database import AsyncSessionLocal
from app.models.document import Document


class WebSocketEventReceiver:
    """WebSocket事件接收器 - 使用真实的事件管理器"""
    
    def __init__(self, event_manager: AgentEventManager, session_id: str):
        self.event_manager = event_manager
        self.session_id = session_id
        self.events: List[Dict[str, Any]] = []
        self.queue: Optional[asyncio.Queue] = None
        self.receiving_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """启动事件接收"""
        self.queue = await self.event_manager.register(self.session_id)
        
        # 启动接收任务
        self.receiving_task = asyncio.create_task(self._receive_events())
        print(f"✅ WebSocket事件接收器已启动 (Session: {self.session_id})")
    
    async def _receive_events(self):
        """接收事件的内部任务"""
        try:
            while True:
                event = await self.queue.get()
                self.events.append({
                    "session_id": self.session_id,
                    "event": event,
                    "timestamp": asyncio.get_event_loop().time()
                })
                await self._handle_event(event)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"❌ 接收事件时出错: {str(e)}")
    
    async def _handle_event(self, event: Dict[str, Any]):
        """处理接收到的事件"""
        event_type = event.get('type', 'unknown')
        data = event.get('data', {})
        
        print(f"\n📨 [收到事件] 类型: {event_type}")
        
        if event_type == 'paragraph_edit_instruction':
            print(f"   段落ID: {data.get('paragraphId')}")
            print(f"   操作: {data.get('operation')}")
            progress = data.get('progress', {})
            print(f"   进度: {progress.get('current')}/{progress.get('total')}")
            if data.get('reasoning'):
                print(f"   理由: {data.get('reasoning')[:50]}...")
            if data.get('newContent'):
                new_content = data.get('newContent', '')
                print(f"   新内容预览: {new_content[:100]}...")
        elif event_type == 'agent_status':
            print(f"   状态: {data.get('stage', 'unknown')}")
        elif event_type == 'session_closed':
            print(f"   会话已关闭")
            await self.stop()
    
    async def stop(self):
        """停止事件接收"""
        if self.receiving_task:
            self.receiving_task.cancel()
            try:
                await self.receiving_task
            except asyncio.CancelledError:
                pass
        
        if self.queue:
            await self.event_manager.unregister(self.session_id, self.queue)
        
        print(f"✅ WebSocket事件接收器已停止 (Session: {self.session_id})")
        print(f"   共收到 {len(self.events)} 个事件")
    
    def get_events(self) -> List[Dict[str, Any]]:
        """获取所有接收的事件"""
        return self.events
    
    def get_event_summary(self) -> Dict[str, int]:
        """获取事件类型统计"""
        summary = {}
        for event_record in self.events:
            event_type = event_record.get('event', {}).get('type', 'unknown')
            summary[event_type] = summary.get(event_type, 0) + 1
        return summary


async def setup_test_document(user_id: int = 1, use_html: bool = False, complex_html: bool = False) -> int:
    """创建测试文档"""
    print("\n" + "=" * 80)
    print("🔧 准备测试数据")
    print("=" * 80)
    
    if use_html:
        if complex_html:
            # 复杂HTML格式测试内容（包含嵌套标签、样式等）
            test_content = """<p><span style="font-size: 18px;"><strong>引言：</strong></span></p><p><span style="font-size: 18px;">奉俊昊的《寄生游戏副本》（Parasite, 2019）不仅是一部斩获戛纳金棕榈与奥斯卡最佳影片的韩国电影，更是一面映照当代社会结构的冷峻镜子。它以黑色幽默为外衣，以精密的叙事结构为骨架，层层剥开阶级固化、空间政治与人性异化的现实疮疤。本文将从叙事结构、空间象征、视觉语言与社会批判四个维度，深入解析这部作品如何在类型片的框架下，完成一场关于现代性困境的深刻寓言。</span></p><p></p><p><span style="font-size: 18px;"><strong>一、叙事结构：精密如钟表的"阶级陷阱"</strong></span></p><p><span style="font-size: 18px;">### 气味、伪装与暴力：《寄生虫》中的阶级具象化与类型解构《寄生虫》巧妙地运用"气味"这一感官线索，将抽象的阶级差异转化为可感知的生理排斥。影片前半段以黑色幽默的喜剧风格，展现基泽一家通过精心伪装的"入侵"过程：他们凭借伪造的学历证书、编造的身份背景，以及临时习得的言行举止，成功渗透进朴社长的豪宅。这种喜剧式叙事营造出阶级流动的假象——仿佛通过谎言与表演，底层家庭便能跨越那道无形的阶级鸿沟。然而，导演奉俊昊并未止步于表面的讽刺，而是通过一场突如其来的暴雨，彻底撕碎了这种幻觉。影片的叙事转折点。当洪水淹没半地下室，基泽一家在污水中抢救微薄家当时，朴社长一家却在豪宅中安然享受雨后的清新空气。这一对比不仅凸显了物质条件的悬殊，更揭示了阶级固化的残酷本质：灾难永远优先摧毁底层生存空间，而特权阶层却能置身事外。尤其具有象征意义的是，朴社长在车内无意间提及基泽身上的"地铁气味"——这种气味成为无法洗刷的阶级烙印，无论基泽一家如何伪装，他们的出身始终通过嗅觉被上层阶级识别并排斥。影片的类型混搭策略进一步强化了社会批判的力度。前半段的犯罪喜剧与后半段的家庭悲剧、心理惊悚元素交织，恰恰对应了阶级议题的双重性：表面上的流动性幻想与本质上的固化现实。当基泽一家的真实身份在生日派对上被揭露时，喜剧氛围瞬间崩塌，取而代之的是赤裸的暴力与排斥。朴社长对气味的厌恶不再是私人偏好，而是阶级歧视的生理化表现；基泽的刺杀行为也不是简单的个人复仇，而是被压抑的阶级愤怒的总爆发。影片揭示：在高度固化的社会中，底层即使暂时伪装成功，也无法真正消除阶级印记；而上层对底层的排斥不仅是经济上的，更是文化、心理乃至生理层面的。当基泽最终躲回地下室，成为真正的"寄生虫"时，电影完成了对现代阶级社会的终极隐喻：有些人注定生活在阳光下，而更多人只能永远藏身于阴影之中。</span></p><p><span style="font-size: 18px;">。</span></p><p></p><p><span style="font-size: 18px;"><strong>二、空间政治：垂直的阶级图腾</strong></span></p><p><span style="font-size: 18px;">《寄生虫》的空间设计极具象征意义。整部电影构建了一个垂直的阶级金字塔：</span></p><p><span style="font-size: 18px;">- <strong>地上豪宅</strong>：阳光充沛，视野开阔，象征资本与权力的顶端。朴社长一家生活在此，洁净、有序，却也冷漠、空洞。</span></p><p><span style="font-size: 18px;">- <strong>半地下室</strong>：基泽一家居住的空间，一半在地面上，一半在地下，象征他们处于阶级夹缝中——既非彻底底层，也无法真正融入上层。</span></p><p><span style="font-size: 18px;">- <strong>完全地下室</strong>：前管家丈夫藏身的密室，彻底不见天日，是被社会彻底遗忘的"幽灵空间"。</span></p><p><span style="font-size: 18px;">这种垂直结构不仅是物理空间，更是社会结构的隐喻。雨水顺地势流淌，淹没了半地下室与地下室，而豪宅依旧高高在上。阶级的"自然法则"在此被具象化：灾难永远由下层承担。</span></p><p><span style="font-size: 18px;"><strong>三、视觉语言：光影与构图的意识形态</strong></span></p><p><span style="font-size: 18px;">奉俊昊的镜头从不中立。影片大量使用对称构图、广角镜头与明暗对比，强化空间的压迫感与阶级的疏离。</span></p><p><span style="font-size: 18px;">- <strong>窗户与视线</strong>：基泽一家常透过窗户窥视外界，而富人则从高处俯视。视线的不平等，正是权力关系的体现。</span></p><p><span style="font-size: 18px;">- <strong>楼梯的反复出现</strong>：上下楼梯成为阶级移动的视觉符号。每一次攀登，都伴随着身份的伪装与心理的紧张。</span></p><p><span style="font-size: 18px;">- <strong>光影对比</strong>：豪宅中光线明亮却冷峻，半地下室则常年处于阴影中。光不再是希望的象征，而是阶级特权的独占资源。</span></p><p><span style="font-size: 18px;">尤其值得注意的是，影片中几乎从未出现天空。人物被禁锢在建筑与地表之间，暗示他们无法"抬头"看见更广阔的世界，也无法真正逃离既定命运。</span></p><p><span style="font-size: 18px;"><strong>四、社会批判：寄生与宿主的双向异化</strong></span></p><p><span style="font-size: 18px;">《寄生虫》的深刻之处，在于它拒绝简单地将富人定义为"压迫者"，穷人定义为"受害者"。影片揭示的是：在极端不平等的社会中，所有人都是系统性的"寄生者"。</span></p><p><span style="font-size: 18px;">- 基泽一家为生存而欺骗，沦为制度的寄生虫；</span></p><p><span style="font-size: 18px;">- 朴社长一家依赖廉价劳动力维持体面生活，同样是寄生在底层劳动之上的"宿主"；</span></p><p><span style="font-size: 18px;">- 而前管家与她的丈夫，则是被彻底剥夺身份的"地下寄生虫"，连寄生的资格都被剥夺。</span></p><p><span style="font-size: 18px;">真正的"寄生虫"不是某个人，而是那个允许贫富悬殊、空间隔离、人性异化的社会结构本身。当基泽在生日派对上刺杀朴社长时，导火索不是金钱，而是"气味"——那无法被伪装的出身印记。这一刻，阶级的暴力不再隐匿，而是赤裸爆发。</span></p><p><span style="font-size: 18px;"><strong>结语：一面无法回避的镜子</strong></span></p><p><span style="font-size: 18px;">《寄生虫》之所以成为全球现象，正因为它超越了国界与文化，直指现代文明的核心矛盾：在物质丰裕的时代，为何人与人之间却筑起越来越深的沟壑？奉俊昊没有提供解决方案，但他用电影的语言，让我们无法再对"地下室"的存在视而不见。</span></p><p><span style="font-size: 18px;">这部电影不是寓言的终点，而是一面镜子——照见我们每个人心中那点侥幸、恐惧与沉默的共谋。正如片中那块"风水石"，看似带来好运，实则是压在底层胸口的沉重宿命。唯有正视这石头的存在，才有可能，哪怕只是微弱地，撼动它。</span></p><p><span style="font-size: 18px;"><strong>评分：★★★★★（5/5）—— 不仅是电影，更是时代的诊断书。</strong></span></p><p></p>"""
        else:
            # 简单HTML格式测试内容（TipTap格式）
            test_content = """<h1 id="heading-0">人工智能发展史</h1><h1 id="heading-1">起源阶段（1950-1956年）</h1><p>人工智能的发展历史可以追溯到20世纪50年代。</p><h1 id="heading-2">理论基础（1950年）</h1><p>1950年，图灵提出了著名的"图灵测试"，这被认为是人工智能研究的起点。</p><h1 id="heading-3">学科确立（1956年）</h1><p>1956年，达特茅斯会议正式确立了"人工智能"这一学科名称。</p><h1 id="heading-4">发展历程</h1><p>经过几十年的发展，人工智能经历了多次繁荣和低谷。</p><h1 id="heading-5">现代突破</h1><p>如今，深度学习技术的突破使得AI在各个领域都取得了重大进展。</p><h1 id="heading-6">未来展望</h1><p>未来，人工智能将继续改变我们的生活和工作方式。</p><p></p>"""
    else:
        # 纯文本格式测试内容
        test_content = """人工智能的发展历史可以追溯到20世纪50年代。

1950年，图灵提出了著名的"图灵测试"，这被认为是人工智能研究的起点。

1956年，达特茅斯会议正式确立了"人工智能"这一学科名称。

经过几十年的发展，人工智能经历了多次繁荣和低谷。

如今，深度学习技术的突破使得AI在各个领域都取得了重大进展。

未来，人工智能将继续改变我们的生活和工作方式。"""
    
    async with AsyncSessionLocal() as session:
        # 检查是否已有测试文档
        from sqlalchemy import select
        if use_html:
            if complex_html:
                doc_title_pattern = "测试文档_复杂HTML_%"
            else:
                doc_title_pattern = "测试文档_HTML_%"
        else:
            doc_title_pattern = "测试文档_%"
        
        result = await session.execute(
            select(Document).where(
                Document.author_id == user_id,
                Document.title.like(doc_title_pattern)
            ).limit(1)
        )
        existing_doc = result.scalar_one_or_none()
        
        doc_type = "复杂HTML格式" if (use_html and complex_html) else ("HTML格式" if use_html else "纯文本格式")
        if existing_doc:
            print(f"✅ 使用已有测试文档 ID: {existing_doc.id} ({doc_type})")
            return existing_doc.id
        
        # 创建新测试文档
        if use_html:
            if complex_html:
                doc_title = f"测试文档_复杂HTML_{uuid.uuid4().hex[:8]}"
            else:
                doc_title = f"测试文档_HTML_{uuid.uuid4().hex[:8]}"
        else:
            doc_title = f"测试文档_{uuid.uuid4().hex[:8]}"
        test_doc = Document(
            title=doc_title,
            content=test_content,
            author_id=user_id,
            status=1  # 草稿状态
        )
        session.add(test_doc)
        await session.commit()
        await session.refresh(test_doc)
        print(f"✅ 创建测试文档 ID: {test_doc.id} ({doc_type})")
        print(f"   标题: {test_doc.title}")
        print(f"   内容长度: {len(test_content)} 字符")
        return test_doc.id


async def test_document_read_tool(user_id: int, document_id: int):
    """测试文档读取工具"""
    print("\n" + "=" * 80)
    print("📖 测试1: DocumentReadTool - 文档读取工具")
    print("=" * 80)
    
    tool = DocumentReadTool(user_id=user_id)
    
    try:
        result = await tool._arun(document_id=document_id)
        print(f"✅ 读取成功")
        print(f"内容预览: {result[:200]}...")
        print(f"总长度: {len(result)} 字符")
        return True
    except Exception as e:
        print(f"❌ 读取失败: {str(e)}")
        return False


async def test_document_analysis_tool(user_id: int, document_id: int):
    """测试文档分析工具"""
    print("\n" + "=" * 80)
    print("🔍 测试2: DocumentAnalysisTool - 文档分析工具")
    print("=" * 80)
    
    # 使用 object.__setattr__ 绕过 Pydantic 的限制
    # 使用工厂函数创建工具
    tool = create_document_analysis_tool(user_id)
    
    # 测试用例2.1: 无选中文本（全文档分析）
    print("\n【测试2.1】全文档分析（无选中文本）")
    print("-" * 80)
    result_data = None
    try:
        result = await tool._arun(
            document_id=document_id,
            user_intent="改写整篇文档，使其更加生动有趣"
        )
        result_data = json.loads(result)
        print(f"✅ 分析成功")
        print(f"文档ID: {result_data['documentId']}")
        print(f"段落总数: {result_data['totalParagraphs']}")
        print(f"用户意图: {result_data['userIntent']}")
        print(f"\n段落列表:")
        for para in result_data['paragraphs'][:3]:  # 只显示前3个
            print(f"  - {para['id']}: {para['content'][:50]}...")
            print(f"    位置: {para['startOffset']}-{para['endOffset']}")
            print(f"    需处理: {para['shouldProcess']}")
    except Exception as e:
        print(f"❌ 分析失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    # 测试用例2.2: 带选中文本的分析
    print("\n【测试2.2】部分文档分析（有选中文本）")
    print("-" * 80)
    try:
        if result_data and result_data.get('paragraphs'):
            # 选择第二个段落的位置范围
            para = result_data['paragraphs'][1] if len(result_data['paragraphs']) > 1 else None
            if para:
                target_selection = {
                    "startOffset": para['startOffset'],
                    "endOffset": para['endOffset']
                }
                print(f"选中段落: {para['id']}")
                print(f"选中范围: {target_selection['startOffset']}-{target_selection['endOffset']}")
                print(f"选中内容: {para['content'][:60]}...")
                
                result2 = await tool._arun(
                    document_id=document_id,
                    user_intent="只改写选中的段落",
                    target_selection=target_selection
                )
                result_data2 = json.loads(result2)
                print(f"\n✅ 部分分析成功")
                print(f"文档ID: {result_data2['documentId']}")
                print(f"段落总数: {result_data2['totalParagraphs']}")
                print(f"相关段落数: {sum(1 for p in result_data2['paragraphs'] if p['isRelevant'])}")
                print(f"需处理段落数: {sum(1 for p in result_data2['paragraphs'] if p['shouldProcess'])}")
                
                # 显示相关段落的详细信息
                print(f"\n相关段落详情:")
                for p in result_data2['paragraphs']:
                    if p['isRelevant']:
                        print(f"  - {p['id']}: {p['content'][:50]}...")
                        print(f"    位置: {p['startOffset']}-{p['endOffset']}")
                        print(f"    相关: {p['isRelevant']}, 需处理: {p['shouldProcess']}")
                
                return result_data2
            else:
                print("⚠️  文档段落不足，无法测试部分分析")
        else:
            print("⚠️  未获取到段落数据，无法测试部分分析")
    except Exception as e:
        print(f"❌ 部分分析测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # 如果没有执行测试2.2，返回测试2.1的结果
    return result_data


async def test_paragraph_edit_tool(document_id: int, analysis_result: dict):
    """测试段落编辑指令工具（使用真实的事件管理器）"""
    print("\n" + "=" * 80)
    print("✏️  测试3: ParagraphEditInstructionTool - 段落编辑指令工具（真实WebSocket）")
    print("=" * 80)
    
    if not analysis_result or not analysis_result.get('paragraphs'):
        print("❌ 需要先运行文档分析测试")
        return False
    
    session_id = str(uuid.uuid4())
    # 使用真实的事件管理器
    event_manager = AgentEventManager()
    paragraphs = analysis_result['paragraphs']
    
    # 创建WebSocket事件接收器
    event_receiver = WebSocketEventReceiver(event_manager, session_id)
    await event_receiver.start()
    
    # 等待一下，确保接收器已注册
    await asyncio.sleep(0.1)
    
    tool = ParagraphEditInstructionTool(
        event_manager=event_manager,
        session_id=session_id,
        total_paragraphs=len(paragraphs)
    )
    
    print(f"\n会话ID: {session_id}")
    print(f"总段落数: {len(paragraphs)}")
    print(f"使用真实事件管理器，事件将通过WebSocket接收...\n")
    
    # 测试不同的编辑操作
    test_cases = [
        {
            "paragraph_id": paragraphs[0]['id'],
            "operation": "replace",
            "new_content": "【改写后的内容】人工智能的发展历程源远流长，可以追溯到20世纪50年代。",
            "reasoning": "改写第一段，使其更加生动",
            "original_content": paragraphs[0]['content'],
            "start_offset": paragraphs[0]['startOffset'],
            "end_offset": paragraphs[0]['endOffset']
        },
        {
            "paragraph_id": paragraphs[1]['id'],
            "operation": "replace",
            "new_content": "【改写后的内容】1950年，计算机科学之父图灵提出了著名的\"图灵测试\"，为人工智能研究奠定了基础。",
            "reasoning": "增加更多细节，使描述更丰富",
            "original_content": paragraphs[1]['content'],
            "start_offset": paragraphs[1]['startOffset'],
            "end_offset": paragraphs[1]['endOffset']
        },
        {
            "paragraph_id": "p_new_1",
            "operation": "insert_after",
            "new_content": "【新增段落】这段历史展现了人类对智能的不断探索和追求。",
            "reasoning": "在第二段后插入新段落，补充说明",
            "original_content": None,
            "start_offset": None,
            "end_offset": None
        }
    ]
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n【编辑指令 {i}/{len(test_cases)}】")
        print("-" * 80)
        try:
            result = await tool._arun(**test_case)
            print(f"✅ {result}")
            success_count += 1
            # 等待事件接收
            await asyncio.sleep(0.2)
        except Exception as e:
            print(f"❌ 生成编辑指令失败: {str(e)}")
            import traceback
            traceback.print_exc()
    
    # 等待所有事件接收完成
    await asyncio.sleep(0.5)
    
    # 停止事件接收器
    await event_receiver.stop()
    
    print(f"\n✅ 成功生成 {success_count}/{len(test_cases)} 个编辑指令")
    
    # 显示事件摘要
    events = event_receiver.get_events()
    print(f"\n📊 事件统计:")
    print(f"   共收到 {len(events)} 个事件")
    
    summary = event_receiver.get_event_summary()
    for event_type, count in summary.items():
        print(f"   - {event_type}: {count}个")
    
    # 显示事件详情
    print("\n事件详情:")
    for i, event_record in enumerate(events, 1):
        event = event_record['event']
        data = event.get('data', {})
        event_type = event.get('type')
        if event_type == 'paragraph_edit_instruction':
            print(f"  {i}. {event_type} - {data.get('operation')} {data.get('paragraphId')}")
            print(f"     进度: {data.get('progress', {}).get('current')}/{data.get('progress', {}).get('total')}")
        else:
            print(f"  {i}. {event_type}")
    
    return success_count == len(test_cases)


async def test_integration_workflow(user_id: int, document_id: int):
    """测试完整工作流程（使用真实的事件管理器）"""
    print("\n" + "=" * 80)
    print("🔄 测试4: 完整工作流程集成测试（真实WebSocket）")
    print("=" * 80)
    
    print("\n步骤1: 读取文档")
    read_tool = DocumentReadTool(user_id=user_id)
    content = await read_tool._arun(document_id=document_id)
    print(f"✅ 读取文档成功，长度: {len(content)} 字符")
    
    print("\n步骤2: 分析文档结构")
    analysis_tool = create_document_analysis_tool(user_id)
    analysis_result = await analysis_tool._arun(
        document_id=document_id,
        user_intent="改写文档，使其更加专业和学术化"
    )
    analysis_data = json.loads(analysis_result)
    print(f"✅ 分析完成，识别出 {analysis_data['totalParagraphs']} 个段落")
    
    print("\n步骤3: 生成编辑指令（使用真实事件管理器）")
    session_id = str(uuid.uuid4())
    event_manager = AgentEventManager()
    
    # 创建WebSocket事件接收器
    event_receiver = WebSocketEventReceiver(event_manager, session_id)
    await event_receiver.start()
    await asyncio.sleep(0.1)  # 等待注册完成
    
    edit_tool = ParagraphEditInstructionTool(
        event_manager=event_manager,
        session_id=session_id,
        total_paragraphs=analysis_data['totalParagraphs']
    )
    
    # 为前两个段落生成编辑指令
    for para in analysis_data['paragraphs'][:2]:
        await edit_tool._arun(
            paragraph_id=para['id'],
            operation="replace",
            new_content=f"【专业改写】{para['content']}",
            reasoning=f"将段落 {para['id']} 改写为更专业的学术风格",
            original_content=para['content'],
            start_offset=para['startOffset'],
            end_offset=para['endOffset']
        )
        await asyncio.sleep(0.1)  # 等待事件接收
    
    # 等待所有事件接收完成
    await asyncio.sleep(0.5)
    await event_receiver.stop()
    
    events = event_receiver.get_events()
    print(f"✅ 工作流程完成，共生成 {len(events)} 个编辑指令")
    
    # 显示事件统计
    summary = event_receiver.get_event_summary()
    print(f"\n事件统计:")
    for event_type, count in summary.items():
        print(f"  - {event_type}: {count}个")


async def main():
    """主测试函数"""
    print("=" * 80)
    print("🧪 文档工具测试套件")
    print("=" * 80)
    
    user_id = 1  # 测试用户ID
    
    try:
        # 准备测试数据（纯文本格式）
        document_id = await setup_test_document(user_id, use_html=False)
        
        # 准备HTML格式测试数据（简单格式）
        print("\n" + "=" * 80)
        print("🔧 准备HTML格式测试数据（简单格式）")
        print("=" * 80)
        html_document_id = await setup_test_document(user_id, use_html=True, complex_html=False)
        
        # 准备复杂HTML格式测试数据（包含嵌套标签、样式等）
        print("\n" + "=" * 80)
        print("🔧 准备复杂HTML格式测试数据（嵌套标签、样式）")
        print("=" * 80)
        complex_html_document_id = await setup_test_document(user_id, use_html=True, complex_html=True)
        
        # 测试1: 文档读取工具
        await test_document_read_tool(user_id, document_id)
        
        # 测试2: 文档分析工具
        analysis_result = await test_document_analysis_tool(user_id, document_id)
        
        # 测试3: 段落编辑指令工具
        if analysis_result:
            await test_paragraph_edit_tool(document_id, analysis_result)
        
        # 测试4: 完整工作流程
        await test_integration_workflow(user_id, document_id)
        
        # 测试5: HTML格式文档测试（简单格式）
        print("\n" + "=" * 80)
        print("🌐 测试5: HTML格式文档分析测试（简单格式）")
        print("=" * 80)
        html_analysis_result = await test_document_analysis_tool(user_id, html_document_id)
        if html_analysis_result:
            print(f"\n✅ HTML格式文档分析成功")
            print(f"识别出 {html_analysis_result['totalParagraphs']} 个段落")
            print(f"\n段落类型统计:")
            tag_count = {}
            for para in html_analysis_result['paragraphs']:
                tag = para.get('tag', 'unknown')
                tag_count[tag] = tag_count.get(tag, 0) + 1
            for tag, count in tag_count.items():
                print(f"  - {tag}: {count}个")
        
        # 测试6: 复杂HTML格式文档测试（嵌套标签、样式等）
        print("\n" + "=" * 80)
        print("🌐 测试6: 复杂HTML格式文档分析测试（嵌套标签、样式）")
        print("=" * 80)
        complex_html_analysis_result = await test_document_analysis_tool(user_id, complex_html_document_id)
        if complex_html_analysis_result:
            print(f"\n✅ 复杂HTML格式文档分析成功")
            print(f"识别出 {complex_html_analysis_result['totalParagraphs']} 个段落")
            print(f"\n段落类型统计:")
            tag_count = {}
            for para in complex_html_analysis_result['paragraphs']:
                tag = para.get('tag', 'unknown')
                tag_count[tag] = tag_count.get(tag, 0) + 1
            for tag, count in tag_count.items():
                print(f"  - {tag}: {count}个")
            
            # 显示前几个段落的详细信息，验证嵌套标签解析
            print(f"\n前5个段落详情（验证嵌套标签解析）:")
            for i, para in enumerate(complex_html_analysis_result['paragraphs'][:5], 1):
                print(f"\n  段落 {i}:")
                print(f"    ID: {para.get('id', 'N/A')}")
                print(f"    标签: {para.get('tag', 'N/A')}")
                print(f"    纯文本内容: {para.get('content', '')[:60]}...")
                print(f"    位置: {para.get('startOffset')}-{para.get('endOffset')}")
                # 显示HTML内容的前100个字符
                html_content = para.get('htmlContent', '')
                if html_content:
                    print(f"    HTML内容预览: {html_content[:100]}...")
            
            # 测试选中文本功能
            if len(complex_html_analysis_result['paragraphs']) > 2:
                print(f"\n测试选中文本功能:")
                test_para = complex_html_analysis_result['paragraphs'][2]
                target_selection = {
                    "startOffset": test_para['startOffset'],
                    "endOffset": test_para['endOffset']
                }
                print(f"  选中段落: {test_para['id']}")
                print(f"  选中范围: {target_selection['startOffset']}-{target_selection['endOffset']}")
                
                # 重新分析，测试选中文本功能
                analysis_tool = create_document_analysis_tool(user_id)
                result = await analysis_tool._arun(
                    document_id=complex_html_document_id,
                    user_intent="只改写选中的段落",
                    target_selection=target_selection
                )
                result_data = json.loads(result)
                relevant_count = sum(1 for p in result_data['paragraphs'] if p['isRelevant'])
                process_count = sum(1 for p in result_data['paragraphs'] if p['shouldProcess'])
                print(f"  ✅ 选中文本分析完成")
                print(f"  相关段落数: {relevant_count}")
                print(f"  需处理段落数: {process_count}")
        
        print("\n" + "=" * 80)
        print("✅ 所有测试完成")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 测试过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

