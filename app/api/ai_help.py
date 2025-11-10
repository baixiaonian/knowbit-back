"""
AI帮写API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel, Field
from typing import Optional, AsyncGenerator
from datetime import datetime

from app.db.database import get_db
from app.models.user_llm_config import UserLLMConfig
from app.services.ai_service import AIService
from app.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/ai-help", tags=["AI帮写"])


class AIHelpRequest(BaseModel):
    """AI帮写请求模型"""
    userId: int = Field(..., description="当前用户ID")
    prompt: str = Field(..., min_length=1, description="用户输入的提示内容")
    documentId: Optional[int] = Field(None, description="当前文档ID（可选）")
    context: Optional[str] = Field(None, description="当前文档内容上下文（可选）")
    promptType: Optional[str] = Field(
        default="ai_help_write",
        description="提示词类型：ai_help_write(通用写作), ai_continue_write(续写), ai_rewrite(改写), ai_expand(扩写), ai_summarize(缩写), ai_polish(润色), ai_translate(翻译), ai_correct(纠错), ai_outline(大纲), ai_title(标题)"
    )
    systemPrompt: Optional[str] = Field(None, description="自定义系统提示词（可选，如果提供会覆盖默认提示词）")


@router.post("/stream")
async def ai_help_stream(
    request: AIHelpRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    AI帮写流式生成
    
    返回Server-Sent Events (SSE)格式的流式数据
    前端接收到的是纯文本内容，直接是AI生成的文档内容
    """
    # 验证用户ID
    if request.userId != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问其他用户的配置"
        )
    
    # 查询用户的大模型配置
    result = await db.execute(
        select(UserLLMConfig).where(
            UserLLMConfig.user_id == current_user_id,
            UserLLMConfig.is_active == True
        )
    )
    llm_config = result.scalar_one_or_none()
    
    if not llm_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到可用的大模型配置，请先配置大模型访问信息"
        )
    
    # 更新最后使用时间
    llm_config.last_used_at = datetime.utcnow()
    await db.commit()
    
    # 创建AI服务
    ai_service = AIService(llm_config)
    
    async def generate() -> AsyncGenerator[str, None]:
        """
        生成流式响应（SSE格式）
        按照Server-Sent Events格式返回AI生成的文档内容
        """
        try:
            # 累积内容，避免每个字符都单独发送
            accumulated_content = ""
            
            async for content in ai_service.generate_stream(
                user_prompt=request.prompt,
                prompt_type=request.promptType,
                custom_system_prompt=request.systemPrompt,
                context=request.context
            ):
                accumulated_content += content
                
                # 当累积的内容达到一定长度或包含完整句子时发送
                if len(accumulated_content) >= 50 or content in ['。', '！', '？', '\n', '\n\n']:
                    yield f"data: {accumulated_content}\n\n"
                    accumulated_content = ""
            
            # 发送剩余内容
            if accumulated_content:
                yield f"data: {accumulated_content}\n\n"
                
        except Exception as e:
            # 错误情况下也使用SSE格式返回
            yield f"data: [生成失败: {str(e)}]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

