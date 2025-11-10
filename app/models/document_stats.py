"""
文档统计模型
"""
from sqlalchemy import Column, BigInteger, TIMESTAMP, ForeignKey, func
from app.db.database import Base


class DocumentStats(Base):
    __tablename__ = "document_stats"
    __table_args__ = {'schema': 'public'}
    
    document_id = Column(BigInteger, ForeignKey('public.documents.id'), primary_key=True)
    view_count = Column(BigInteger, nullable=False, default=0)
    like_count = Column(BigInteger, nullable=False, default=0)
    share_count = Column(BigInteger, nullable=False, default=0)
    comment_count = Column(BigInteger, nullable=False, default=0)
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

