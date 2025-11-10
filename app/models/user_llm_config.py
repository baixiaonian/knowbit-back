"""
用户大模型配置模型
"""
from sqlalchemy import Column, BigInteger, String, Boolean, TIMESTAMP, ForeignKey, Integer, DECIMAL, func
from app.db.database import Base


class UserLLMConfig(Base):
    __tablename__ = "user_llm_config"
    __table_args__ = {'schema': 'public'}
    
    user_id = Column(BigInteger, ForeignKey('public.user.id'), primary_key=True)
    provider = Column(String(20), nullable=False, default='OpenAI')
    api_key = Column(String(255), nullable=False)  # 应用层需加密存储
    model_name = Column(String(50), default='gpt-4')
    api_base = Column(String(255), default='https://api.openai.com/v1')
    max_tokens = Column(Integer, default=2000)
    temperature = Column(DECIMAL(3, 2), default=0.7)
    is_active = Column(Boolean, default=True)
    last_used_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

