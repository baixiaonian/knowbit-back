"""
写作智能体封装
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional, List
from langchain.agents import initialize_agent, AgentType
from langchain.tools import BaseTool

from app.agents.event_manager import AgentEventManager
from app.agents.memory import DatabaseConversationMemory
from app.agents.tools import (
    create_knowledge_tools,
    create_task_tools,
    create_paragraph_edit_tool,
    create_document_analysis_tool,
)
from app.db.database import AsyncSessionLocal
from app.services.llm_provider import get_user_llm


class WriterAgentService:
    """封装 LangChain 写作智能体"""

    def __init__(self, event_manager: AgentEventManager):
        self.event_manager = event_manager

    async def start_session(self, user_id: int, payload: Dict[str, Any], session_id: Optional[str] = None) -> str:
        if session_id:
            # 如果提供了 session_id，直接使用（用于复用会话）
            pass
        else:
            # 生成新的 session_id：user_id + 时间戳（微秒级）
            # 格式：user_id-timestamp，确保唯一性
            timestamp = int(time.time() * 1000000)  # 微秒级时间戳
            session_id = f"{user_id}-{timestamp}"
        
        asyncio.create_task(self._run_agent(session_id, user_id, payload))
        return session_id

    async def _run_agent(self, session_id: str, user_id: int, payload: Dict[str, Any]) -> None:
        await self.event_manager.publish(session_id, {
            "type": "agent_status",
            "data": {"stage": "initializing"}
        })
        try:
            async with AsyncSessionLocal() as session:
                llm = await get_user_llm(session, user_id)

            # 提取请求参数
            user_prompt = payload.get("userPrompt")
            document_id = payload.get("documentId")
            selected_snippets: List[dict] = payload.get("selectedSnippets", [])
            selected_document_ids: List[int] = payload.get("selectedDocumentIds", [])
            target_selection: Optional[dict] = payload.get("targetSelection")  # 用户选中的文本范围

            # 统一使用段落编辑模式
            # 初始化工具：文档分析 + 段落编辑 + 知识检索 + 任务管理
            tools: list[BaseTool] = [
                create_document_analysis_tool(user_id),
                create_paragraph_edit_tool(
                    self.event_manager, 
                    session_id, 
                    total_paragraphs=0  # 初始值，后续根据分析结果更新
                ),
            ]
            
            # 添加其他工具
            tools.extend(create_knowledge_tools(
                user_id=user_id, 
                selected_document_ids=selected_document_ids,
                event_manager=self.event_manager,
                session_id=session_id
            ))
            tools.extend(create_task_tools(
                user_id=user_id,
                event_manager=self.event_manager,
                session_id=session_id
            ))

            # 初始化记忆模块（从数据库加载历史消息）
            memory = DatabaseConversationMemory(
                session_id=session_id,
                user_id=user_id,
                agent_type="writing",
                return_messages=True
            )
            # 加载历史消息
            await memory._load_memory_variables_async()

            agent_executor = initialize_agent(
                tools=tools,
                llm=llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True,
                memory=memory,  # 添加记忆模块
                max_iterations=15,  # 增加最大迭代次数，确保有足够机会调用工具
                max_execution_time=300  # 增加最大执行时间（5分钟）
            )

            await self.event_manager.publish(session_id, {
                "type": "agent_status",
                "data": {"stage": "intent_analysis"}
            })
            intent_summary = await self._analyze_intent(
                llm, user_prompt, selected_snippets
            )
            await self.event_manager.publish(session_id, {
                "type": "intent_summary",
                "data": intent_summary
            })

            # 保存用户消息到记忆
            await memory.save_user_message(
                content=user_prompt or "",
                metadata={
                    "document_id": document_id,
                    "selected_snippets": selected_snippets,
                    "selected_document_ids": selected_document_ids,
                    "target_selection": target_selection
                }
            )

            # 构建智能体输入
            agent_input = await self._build_agent_input(
                user_prompt=user_prompt,
                document_id=document_id,
                target_selection=target_selection,
                selected_snippets=selected_snippets,
                selected_document_ids=selected_document_ids,
                intent_summary=intent_summary,
                session_id=session_id
            )
            
            await self.event_manager.publish(session_id, {
                "type": "agent_status",
                "data": {"stage": "running"}
            })
            result = await agent_executor.ainvoke(agent_input)
            
            # 保存助手回复到记忆
            assistant_output = result.get("output", "") if isinstance(result, dict) else str(result)
            await memory.save_assistant_message(
                content=assistant_output,
                metadata={
                    "intent_summary": intent_summary,
                    "result_type": type(result).__name__
                }
            )
            
            # 发布完成事件
            assistant_output = result.get("output", "") if isinstance(result, dict) else str(result)
            
            # 判断任务类型，生成合适的摘要
            if document_id:
                summary = "根据用户需求分析了文档结构并生成编辑指令"
            else:
                # 没有文档ID时，应该是内容创作任务
                # 检查输出是否包含实际文本内容（而不是只有工具调用）
                if assistant_output and not assistant_output.strip().startswith("{"):
                    summary = "已生成完整的文本内容"
                else:
                    summary = "已完成内容创作任务"
            
            await self.event_manager.publish(session_id, {
                "type": "agent_complete",
                "data": {
                    "result": {
                        "output": assistant_output,
                        "summary": summary
                    }
                }
            })
        except Exception as exc:  # pylint: disable=broad-except
            error_msg = str(exc)
            # 如果是搜索工具的错误，不应该阻止智能体继续执行
            # 但如果是其他严重错误，需要报告
            if "search" in error_msg.lower() or "timeout" in error_msg.lower() or "duckduckgo" in error_msg.lower():
                # 搜索相关的错误，发布错误事件但不阻止执行
                await self.event_manager.publish(session_id, {
                    "type": "agent_error",
                    "data": {
                        "message": f"搜索工具错误: {error_msg}，但智能体将继续基于已有知识生成内容",
                        "code": "SEARCH_ERROR",
                        "recoverable": True
                    }
                })
            else:
                # 其他严重错误
                await self.event_manager.publish(session_id, {
                    "type": "agent_error",
                    "data": {
                        "message": error_msg,
                        "code": "UNKNOWN",
                        "recoverable": False
                    }
                })
        finally:
            # 清空会话的任务数据（内存存储）
            from app.agents.tools.task_storage import task_storage
            task_storage.clear_session(session_id)
            await self.event_manager.close_session(session_id)

    async def _analyze_intent(
        self,
        llm,
        user_prompt: Optional[str],
        selected_snippets: List[dict]
    ) -> Dict[str, Any]:
        """调用LLM生成意图理解结果"""
        if not user_prompt:
            return {
                "intent": "unknown",
                "summary": "未提供用户输入",
                "keyPoints": [],
                "suggestedActions": [],
                "toneStyle": None
            }
        
        # 构建上下文
        context_parts = []
        
        if selected_snippets:
            snippets_text = "\n\n".join(
                f"[文档{snippet.get('documentId')}] {snippet.get('content')}" 
                for snippet in selected_snippets if snippet.get("content")
            )
            if snippets_text:
                context_parts.append(f"参考片段：{snippets_text}")
        
        context_parts.append("编辑模式：段落级别精确编辑")
        context_str = "\n\n".join(context_parts) if context_parts else "无"
        
        prompt = (
            "你是写作智能体的意图理解模块，请阅读用户输入并总结写作目标。"
            "请输出JSON，包含 intent(一句话总结)、summary(概述)、keyPoints(列表)、"
            "suggestedActions(列表)、toneStyle(推荐语气)。如果信息不足，保持字段为空。\n"
            f"用户输入：{user_prompt}\n"
            f"上下文信息：{context_str}"
        )
        try:
            response = await llm.ainvoke(prompt)
            content = response.content if hasattr(response, "content") else str(response)
            content = content.strip()
            json_str = content.split("```json")[-1].split("```")[-1].strip() if "```" in content else content
            data = json.loads(json_str)
            if not isinstance(data, dict):
                raise ValueError("intent output is not dict")
            return {
                "intent": data.get("intent", ""),
                "summary": data.get("summary") or data.get("intent", ""),
                "keyPoints": data.get("keyPoints", []),
                "suggestedActions": data.get("suggestedActions", []),
                "toneStyle": data.get("toneStyle"),
            }
        except Exception:  # pylint: disable=broad-except
            return {
                "intent": "",
                "summary": user_prompt[:100],
                "keyPoints": [],
                "suggestedActions": [],
                "toneStyle": None
            }
    
    async def _build_agent_input(
        self,
        user_prompt: str,
        document_id: Optional[int],
        target_selection: Optional[dict],
        selected_snippets: List[dict],
        selected_document_ids: List[int],
        intent_summary: Dict[str, Any],
        session_id: str
    ) -> Dict[str, Any]:
        """构建智能体输入（统一使用段落编辑模式）"""
        
        intent_text = json.dumps(intent_summary, ensure_ascii=False)
        
        # 构建选中文本信息
        selection_info = ""
        if target_selection:
            selection_text = target_selection.get("text", "")
            start_offset = target_selection.get("startOffset")
            end_offset = target_selection.get("endOffset")
            selection_info = (
                f"\n\n用户选中文本：\n"
                f"内容：{selection_text}\n"
                f"位置：字符 {start_offset} - {end_offset}"
            )
        
        # 构建参考片段信息
        reference_info = ""
        if selected_snippets:
            snippets_text = "\n\n".join(
                f"[文档{snippet.get('documentId')}] {snippet.get('content')}" 
                for snippet in selected_snippets if snippet.get("content")
            )
            if snippets_text:
                reference_info = f"\n\n参考片段：\n{snippets_text}"
        
        # 构建相关文档信息
        related_docs_info = ""
        if selected_document_ids:
            related_docs_info = f"\n\n相关文档ID: {selected_document_ids}"
        
        instructions = f"""你是一名专业的AI写作助手。请根据任务类型选择合适的工作模式：

【模式1：文档编辑模式】- 当有 document_id 时
第一步：使用 document_analyzer 工具分析文档结构
  - 传入 document_id, user_intent, 和 target_selection（如果有）
  - 该工具会返回文档的段落列表，包含每个段落的ID、内容和位置信息

第二步：根据分析结果和用户意图，识别需要处理的段落
  - 如果用户要求改写"整个文档"或"全部内容"，应处理所有段落（参考 shouldProcess 字段）
  - 如果有选中文本，优先关注 isRelevant=true 的段落及其上下文
  - 考虑段落之间的连贯性，可能需要修改相邻段落

第三步：逐个段落调用 paragraph_editor 工具生成编辑指令
  - 必须逐个段落调用工具，不要批量处理
  - 每次调用必须填写：paragraph_id, operation, new_content, reasoning
  - 同时提供：original_content, start_offset, end_offset（从分析结果中获取）
  - reasoning 必须详细解释修改原因和如何改进

【模式2：内容创作模式】- 当没有 document_id 时（如"写一篇文章"、"创作内容"等）
第一步：理解用户需求并检索相关信息（必须执行，但不要过度搜索）
  - 明确用户要求的内容类型、主题、长度、风格等
  - 必须使用 document_knowledge_search 或 web_research_tool 检索相关信息作为参考
  - 优先使用 document_knowledge_search（如果用户提供了 selectedDocumentIds，会优先搜索这些文档）
  - 如果文档库中没有相关信息，再使用 web_research_tool 搜索互联网资料
  - 检索一次或两次即可，不要反复搜索，检索到的信息已经足够生成内容
  - 如果搜索失败或超时，不要停止执行，应该基于已有知识和理解继续生成内容
  - 检索完成后（无论成功与否），立即进入第二步生成内容

第二步：使用 paragraph_editor 工具推送内容（必须执行，这是最重要的步骤！）
  - 检索完成后，必须立即根据用户需求和检索到的信息生成完整的文本内容
  - 将生成的内容按段落拆分（通常以换行符分隔，每个段落50-200字左右）
  - 必须使用 paragraph_editor 工具逐个推送每个段落，这是推送内容的唯一方式
  - 对于新创建的内容，使用 insert_after 操作
  - paragraph_id 必须自动生成（如 p_1, p_2, p_3 等，按顺序递增）
  - 每个段落调用一次 paragraph_editor 工具，提供：
    * paragraph_id: 段落ID（如 p_1, p_2 等，必须按顺序）
    * operation: "insert_after"（新内容必须使用此操作）
    * new_content: 该段落的完整内容（必须填写，不能为空）
    * reasoning: 说明这段内容的作用和目的（必须填写）
    * original_content: 新内容时可以为 None 或空字符串
  - 必须推送至少2-5个段落，确保内容完整
  - 推送完所有段落后，在最终回复中简单说明已完成内容生成

可用工具说明：
- document_analyzer: 分析文档结构，返回段落列表（仅用于有document_id的情况）
- paragraph_editor: 生成段落编辑指令，用于向前端推送所有文档内容（必须使用，包括新创建的内容）
- document_knowledge_search: 从用户文档库中检索相关内容（支持指定文档ID重点搜索）
- web_research_tool: 使用DuckDuckGo搜索互联网公开资料
- task_create: 创建任务，用于跟踪执行进度
- task_update: 更新任务状态
- task_list: 查询当前会话的任务列表

重要要求（必须严格遵守）：
1. 如果没有document_id，在生成内容前必须先使用搜索工具检索相关信息（搜索1-2次即可，不要反复搜索）
2. 如果搜索失败或超时，不要停止执行，必须基于已有知识和理解继续生成内容
3. 搜索完成后（无论成功与否），必须立即使用 paragraph_editor 工具推送所有生成的文本内容
4. 必须使用 paragraph_editor 工具推送内容，这是向前端推送内容的唯一方式，不要直接在最终回复中返回文本
5. 所有文档内容（无论是编辑还是新创建）都必须通过 paragraph_editor 工具推送，至少推送2-5个段落
6. 保持内容的连贯性和逻辑性，合理整合检索到的信息（如果有的话）
7. 尊重用户的具体要求（长度、风格、主题等），确保内容符合要求
8. 检索知识时，优先使用 document_knowledge_search（如果提供了 selectedDocumentIds，会优先搜索这些文档），如果没有结果再使用 web_research_tool
9. 推送完所有段落后，在最终回复中简单说明已完成内容生成
10. 不要只调用工具而不生成内容，搜索工具只是辅助，最终必须生成并推送内容，即使搜索失败也要生成内容
当前会话ID: {session_id}
"""
        
        input_text = (
            f"用户需求: {user_prompt}\n\n"
            f"文档ID: {document_id or '无'}\n\n"
            f"意图分析: {intent_text}"
            f"{selection_info}"
            f"{reference_info}"
            f"{related_docs_info}\n\n"
            f"{instructions}"
        )
        
        # STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION 类型的 Agent 只需要 input 字符串
        return {"input": input_text}
