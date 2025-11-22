"""
Agent会话模型
"""
from sqlalchemy import Column, BigInteger, String, TIMESTAMP, func, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base


class AgentSession(Base):
    __tablename__ = "agent_sessions"
    __table_args__ = {"schema": "public"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(255), unique=True, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("public.user.id", ondelete="CASCADE"), nullable=False)
    agent_type = Column(String(50), nullable=False, default="writing")
    title = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False, default="active")
    config = Column(JSONB, nullable=False, default={})
    session_metadata = Column("metadata", JSONB, nullable=False, default={})
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # 关系
    messages = relationship("AgentMessage", back_populates="session", cascade="all, delete-orphan", order_by="AgentMessage.message_order")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "userId": self.user_id,
            "agentType": self.agent_type,
            "title": self.title,
            "status": self.status,
            "config": self.config,
            "metadata": self.session_metadata,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }

