"""
智能体API
"""
import asyncio
from uuid import uuid4
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from app.utils.auth import get_current_user_id
from app.schemas.agent import AgentExecutionRequest, AgentExecutionResponse
from app.agents.event_manager import AgentEventManager
from app.agents.writer_agent import WriterAgentService

router = APIRouter(prefix="/api/agent", tags=["写作智能体"])

event_manager = AgentEventManager()
writer_agent_service = WriterAgentService(event_manager)


@router.post("/writer/execute", response_model=AgentExecutionResponse)
async def execute_writer_agent(
    request: AgentExecutionRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    payload = request.model_dump(exclude={"sessionId"}, exclude_none=True)
    session_id = await writer_agent_service.start_session(
        current_user_id,
        payload,
        session_id=request.sessionId
    )
    return AgentExecutionResponse(sessionId=session_id)


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
