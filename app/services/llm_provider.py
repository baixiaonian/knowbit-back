"""
LLM与Embedding提供工具
"""
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_openai import ChatOpenAI
from app.models.user_llm_config import UserLLMConfig
from app.services.vectorizer import DocumentVectorizer


async def get_user_llm(session: AsyncSession, user_id: int) -> ChatOpenAI:
    result = await session.execute(
        select(UserLLMConfig).where(UserLLMConfig.user_id == user_id, UserLLMConfig.is_active == True)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise ValueError("未找到可用的LLM配置，请先在系统中配置API Key")
    return ChatOpenAI(
        api_key=config.api_key,
        base_url=config.api_base,
        model=config.model_name,
        temperature=0.3
    )


async def get_user_vectorizer(session: AsyncSession, user_id: int) -> DocumentVectorizer:
    result = await session.execute(
        select(UserLLMConfig).where(UserLLMConfig.user_id == user_id, UserLLMConfig.is_active == True)
    )
    config = result.scalar_one_or_none()
    if not config:
        raise ValueError("未找到向量化配置，请先在系统中配置API Key")
    return DocumentVectorizer(
        api_key=config.api_key,
        api_base=config.api_base,
        model=config.model_name
    )
