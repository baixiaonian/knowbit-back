"""
评论模型
"""
from sqlalchemy import Column, BigInteger, Text, SmallInteger, TIMESTAMP, ForeignKey, func
from app.db.database import Base


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = {'schema': 'public'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    document_id = Column(BigInteger, ForeignKey('public.documents.id'), nullable=False)
    author_id = Column(BigInteger, ForeignKey('public.user.id'), nullable=False)
    parent_id = Column(BigInteger, ForeignKey('public.comments.id'), nullable=True)
    content = Column(Text, nullable=False)
    status = Column(SmallInteger, nullable=False, default=1)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    # 保留字段
    reserved_field1 = Column(Text, nullable=True)
    reserved_field2 = Column(Text, nullable=True)
    reserved_field3 = Column(Text, nullable=True)

