"""
Agent消息模型
"""
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, func, ForeignKey, Integer, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.database import Base


class AgentMessage(Base):
    __tablename__ = "agent_messages"
    __table_args__ = (
        CheckConstraint("role IN ('user', 'assistant', 'system', 'tool')", name="chk_role"),
        {"schema": "public"}
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    session_id = Column(String(255), ForeignKey("public.agent_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)  # user/assistant/system/tool
    content = Column(Text, nullable=False)
    tool_name = Column(String(100), nullable=True)
    tool_calls = Column(JSONB, nullable=True)
    tool_results = Column(JSONB, nullable=True)
    message_references = Column(JSONB, nullable=True)
    message_metadata = Column("metadata", JSONB, nullable=False, default={})
    message_order = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    # 关系
    session = relationship("AgentSession", back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "role": self.role,
            "content": self.content,
            "toolName": self.tool_name,
            "toolCalls": self.tool_calls,
            "toolResults": self.tool_results,
            "references": self.message_references,
            "metadata": self.message_metadata,
            "messageOrder": self.message_order,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
        }

