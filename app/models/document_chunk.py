"""
文档分块模型
"""
from sqlalchemy import Column, BigInteger, String, Integer, Text, TIMESTAMP, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector
from app.db.database import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = {'schema': 'public'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    document_id = Column(BigInteger, ForeignKey('public.documents.id', ondelete='CASCADE'), nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024))  # qwen3-embedding-0.6b 维度：1024
    chunk_index = Column(Integer, nullable=False)
    token_count = Column(Integer)
    chunk_metadata = Column('metadata', JSONB, default={})  # 使用别名避免冲突
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


