"""
用户大模型配置Schema模型
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal


class UserLLMConfigBase(BaseModel):
    """大模型配置基础模型"""
    provider: str = Field(default='OpenAI', max_length=20, description="大模型提供商")
    model_name: Optional[str] = Field(default='gpt-4', max_length=50, description="模型名称")
    api_base: Optional[str] = Field(default='https://api.openai.com/v1', max_length=255, description="API基础URL")
    max_tokens: Optional[int] = Field(default=2000, description="最大token数")
    temperature: Optional[Decimal] = Field(default=Decimal('0.7'), description="温度参数")
    is_active: Optional[bool] = Field(default=True, description="是否启用")


class UserLLMConfigCreate(UserLLMConfigBase):
    """创建大模型配置请求模型"""
    api_key: str = Field(..., max_length=255, description="API密钥")


class UserLLMConfigUpdate(BaseModel):
    """更新大模型配置请求模型"""
    provider: Optional[str] = Field(None, max_length=20, description="大模型提供商")
    api_key: Optional[str] = Field(None, max_length=255, description="API密钥")
    model_name: Optional[str] = Field(None, max_length=50, description="模型名称")
    api_base: Optional[str] = Field(None, max_length=255, description="API基础URL")
    max_tokens: Optional[int] = Field(None, description="最大token数")
    temperature: Optional[Decimal] = Field(None, description="温度参数")
    is_active: Optional[bool] = Field(None, description="是否启用")


class UserLLMConfigResponse(BaseModel):
    """大模型配置响应模型"""
    userId: int
    provider: str
    apiKey: str
    modelName: Optional[str]
    apiBase: Optional[str]
    maxTokens: Optional[int]
    temperature: Optional[Decimal]
    isActive: bool
    lastUsedAt: Optional[datetime]
    createdAt: datetime
    updatedAt: datetime
    
    class Config:
        from_attributes = True
