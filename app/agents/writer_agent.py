"""
写作智能体封装
"""
import asyncio
import json
import uuid
from typing import Dict, Any, Optional, List
from langchain.agents import initialize_agent, AgentType
from langchain.tools import BaseTool

from app.agents.event_manager import AgentEventManager
from app.agents.tools import (
    create_document_tools,
    create_knowledge_tools,
    create_task_tools,
)
from app.db.database import AsyncSessionLocal
from app.services.llm_provider import get_user_llm


class WriterAgentService:
    """封装 LangChain 写作智能体"""

    def __init__(self, event_manager: AgentEventManager):
        self.event_manager = event_manager

    async def start_session(self, user_id: int, payload: Dict[str, Any], session_id: Optional[str] = None) -> str:
        session_id = session_id or str(uuid.uuid4())
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

            tools: list[BaseTool] = []
            tools.extend(create_document_tools(self.event_manager, user_id, session_id))
            tools.extend(create_knowledge_tools(user_id))
            tools.extend(create_task_tools(user_id))

            agent_executor = initialize_agent(
                tools=tools,
                llm=llm,
                agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
                verbose=True,
                handle_parsing_errors=True
            )

            user_prompt = payload.get("userPrompt")
            document_id = payload.get("documentId")
            selected_snippets: List[dict] = payload.get("selectedSnippets", [])
            selected_document_ids: List[int] = payload.get("selectedDocumentIds", [])

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

            reference_block = "\n\n".join(
                f"[文档{snippet.get('documentId')}] {snippet.get('content')}" for snippet in selected_snippets if snippet.get("content")
            ) or "无"
            intent_text = json.dumps(intent_summary, ensure_ascii=False)
            derived_requirements = intent_summary.get("suggestedActions") or intent_summary.get("keyPoints") or []
            derived_requirements_text = json.dumps(derived_requirements, ensure_ascii=False)

            instructions = (
                "你是一名专业写作助手。请根据用户目标规划任务，调用工具收集信息、改写文档、管理任务清单。"
                "所有文档操作必须通过 document_editor 工具完成，并附带summary。"
                f"如需记录任务，请调用 task_create/task_update，并使用会话ID {session_id} 作为参数。"
            )
            await self.event_manager.publish(session_id, {
                "type": "agent_status",
                "data": {"stage": "running"}
            })
            result = await agent_executor.ainvoke({
                "input": (
                    f"用户输入: {user_prompt}\n文档ID: {document_id}\n意图概述: {intent_text}\n"
                    f"参考片段: {reference_block}\n"
                    f"推断需求: {derived_requirements_text}\n"
                    f"相关文档ID: {selected_document_ids}\n"
                    f"当前会话ID: {session_id}\n{instructions}"
                ),
                "session_id": session_id
            })
            await self.event_manager.publish(session_id, {
                "type": "agent_complete",
                "data": {"result": result}
            })
        except Exception as exc:  # pylint: disable=broad-except
            await self.event_manager.publish(session_id, {
                "type": "agent_error",
                "data": {"message": str(exc)}
            })
        finally:
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
        snippets_text = "\n\n".join(
            f"[文档{snippet.get('documentId')}] {snippet.get('content')}" for snippet in selected_snippets if snippet.get("content")
        ) or "无"
        prompt = (
            "你是写作智能体的意图理解模块，请阅读用户输入并总结写作目标。"
            "请输出JSON，包含 intent(一句话总结)、summary(概述)、keyPoints(列表)、"
            "suggestedActions(列表)、toneStyle(推荐语气)。如果信息不足，保持字段为空。\n"
            f"用户输入：{user_prompt}\n"
            f"参考片段：{snippets_text}"
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
