"""
写作智能体任务模型
"""
from sqlalchemy import Column, BigInteger, String, Text, TIMESTAMP, func, Integer
from sqlalchemy.orm import relationship
from app.db.database import Base


class AgentTask(Base):
    __tablename__ = "agent_task"
    __table_args__ = {"schema": "public"}

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False)
    session_id = Column(String(64), nullable=False, index=True)
    description = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sessionId": self.session_id,
            "description": self.description,
            "status": self.status,
            "priority": self.priority,
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None
        }
