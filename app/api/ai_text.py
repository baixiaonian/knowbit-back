"""
AI文本处理API - 局部段落处理
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional, AsyncGenerator, Literal
from datetime import datetime

from app.db.database import get_db
from app.models.user_llm_config import UserLLMConfig
from app.services.ai_service import AIService
from app.utils.auth import get_current_user_id

router = APIRouter(prefix="/api/ai-text", tags=["AI文本处理"])


class ProcessOptions(BaseModel):
    """处理选项"""
    targetLanguage: Optional[str] = Field(None, description="目标语言代码（translate专用）")
    sourceLanguage: Optional[str] = Field(None, description="源语言代码（translate专用）")
    summaryLength: Optional[Literal["short", "medium", "long"]] = Field(None, description="摘要长度（summarize专用）")
    expandType: Optional[Literal["detailed", "brief"]] = Field(None, description="扩写类型（expand专用）")
    targetLength: Optional[int] = Field(None, description="目标长度（abbreviate专用）")
    correctionType: Optional[Literal["grammar", "spelling", "style"]] = Field(None, description="纠错类型（correct专用）")


class AITextProcessRequest(BaseModel):
    """AI文本处理请求模型"""
    userId: int = Field(..., description="当前用户ID")
    action: Literal["expand", "continue", "abbreviate", "correct", "summarize", "translate", "format", "custom"] = Field(
        ..., 
        description="处理动作类型"
    )
    originalText: str = Field(..., min_length=1, description="原始文本内容")
    documentId: Optional[int] = Field(None, description="当前文档ID（可选）")
    context: Optional[str] = Field(None, description="周围文本上下文（可选）")
    userPrompt: Optional[str] = Field(None, description="用户个性化需求提示词（custom专用）")
    options: Optional[ProcessOptions] = Field(None, description="处理选项")


# Action到PromptType的映射
ACTION_TO_PROMPT_TYPE = {
    "expand": "ai_expand",           # 扩写
    "continue": "ai_continue_write", # 续写
    "abbreviate": "ai_summarize",    # 缩写
    "correct": "ai_correct",         # 纠错
    "summarize": "ai_summarize",     # 总结
    "translate": "ai_translate",     # 翻译
    "format": "ai_polish",           # 格式化（使用润色）
    "custom": "ai_help_write",       # 自定义（使用通用写作）
}


def build_prompt_for_action(request: AITextProcessRequest) -> str:
    """
    根据action和options构建用户提示词
    
    Args:
        request: 请求对象
        
    Returns:
        构建好的用户提示词
    """
    action = request.action
    original_text = request.originalText
    options = request.options or ProcessOptions()
    
    # 自定义action，使用用户提供的prompt
    if action == "custom":
        if not request.userPrompt:
            return f"处理以下内容：\n{original_text}"
        return f"{request.userPrompt}\n\n原文：\n{original_text}"
    
    # 扩写
    if action == "expand":
        expand_type = options.expandType or "detailed"
        type_desc = "详细" if expand_type == "detailed" else "简要"
        return f"请对以下内容进行{type_desc}扩写：\n{original_text}"
    
    # 续写
    if action == "continue":
        return f"请基于以下内容继续写作：\n{original_text}"
    
    # 缩写/总结
    if action in ["abbreviate", "summarize"]:
        if action == "summarize":
            length = options.summaryLength or "medium"
            length_desc = {"short": "简短", "medium": "中等长度", "long": "较详细"}[length]
            return f"请对以下内容进行{length_desc}的总结：\n{original_text}"
        else:
            target = options.targetLength or 100
            return f"请将以下内容精简为约{target}字：\n{original_text}"
    
    # 纠错
    if action == "correct":
        correction_type = options.correctionType or "grammar"
        type_map = {
            "grammar": "语法错误",
            "spelling": "拼写错误",
            "style": "语言风格"
        }
        return f"请修正以下内容的{type_map[correction_type]}：\n{original_text}"
    
    # 翻译
    if action == "translate":
        source = options.sourceLanguage or "自动检测"
        target = options.targetLanguage or "en"
        lang_map = {
            "zh": "中文", "en": "英文", "ja": "日文", 
            "ko": "韩文", "fr": "法文", "de": "德文",
            "es": "西班牙文", "ru": "俄文"
        }
        target_lang = lang_map.get(target, target)
        return f"请将以下内容翻译为{target_lang}：\n{original_text}"
    
    # 格式化（润色）
    if action == "format":
        return f"请对以下内容进行格式化和润色：\n{original_text}"
    
    # 默认
    return f"请处理以下内容：\n{original_text}"


@router.post("/process/stream")
async def process_text_stream(
    request: AITextProcessRequest,
    db: AsyncSession = Depends(get_db),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    局部段落AI处理流式接口
    
    根据action字段调用不同的AI处理能力：
    - expand: 扩写
    - continue: 续写
    - abbreviate: 缩写
    - correct: 纠错
    - summarize: 总结
    - translate: 翻译
    - format: 格式化
    - custom: 自定义（使用userPrompt）
    
    返回SSE格式的流式数据
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
    
    # 获取对应的prompt类型
    prompt_type = ACTION_TO_PROMPT_TYPE.get(request.action, "ai_help_write")
    
    # 构建用户提示词
    user_prompt = build_prompt_for_action(request)
    
    # 创建AI服务
    ai_service = AIService(llm_config)
    
    async def generate() -> AsyncGenerator[str, None]:
        """
        生成流式响应（SSE格式）
        """
        try:
            # 累积内容，避免每个字符都单独发送
            accumulated_content = ""
            
            async for content in ai_service.generate_stream(
                user_prompt=user_prompt,
                prompt_type=prompt_type,
                custom_system_prompt=None,  # 不使用自定义系统提示词
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
            yield f"data: [处理失败: {str(e)}]\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )

