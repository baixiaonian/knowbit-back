"""
智能体API
"""
import asyncio
from uuid import uuid4
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, HTTPException, status

from app.utils.auth import get_current_user_id
from app.schemas.agent import AgentExecutionRequest, AgentExecutionResponse
from app.agents.event_manager import AgentEventManager
from app.agents.writer_agent import WriterAgentService
from app.db.database import AsyncSessionLocal
from app.services.llm_provider import get_user_llm

router = APIRouter(prefix="/api/agent", tags=["写作智能体"])

event_manager = AgentEventManager()
writer_agent_service = WriterAgentService(event_manager)


@router.post("/writer/execute", response_model=AgentExecutionResponse)
async def execute_writer_agent(
    request: AgentExecutionRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    执行写作智能体任务
    
    启动智能体执行任务，返回sessionId用于后续WebSocket连接接收事件。
    如果用户未配置LLM API Key，会返回错误。
    """
    # 验证用户是否配置了LLM
    try:
        async with AsyncSessionLocal() as session:
            await get_user_llm(session, current_user_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"未配置LLM API Key: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置检查失败: {str(e)}"
        )
    
    # 执行智能体任务
    try:
        payload = request.model_dump(exclude={"sessionId"}, exclude_none=True)
        session_id = await writer_agent_service.start_session(
            current_user_id,
            payload,
            session_id=request.sessionId
        )
        return AgentExecutionResponse(sessionId=session_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"智能体启动失败: {str(e)}"
        )


@router.websocket("/ws/{session_id}")
async def agent_events(websocket: WebSocket, session_id: str):
    await websocket.accept()
    queue = await event_manager.register(session_id)
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except WebSocketDisconnect:
        await event_manager.unregister(session_id, queue)
    except Exception:
        await event_manager.unregister(session_id, queue)
        raise
