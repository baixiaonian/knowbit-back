"""
文档模型
"""
from sqlalchemy import Column, BigInteger, String, Text, Boolean, SmallInteger, TIMESTAMP, ForeignKey, ARRAY, func
from app.db.database import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = {'schema': 'public'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    author_id = Column(BigInteger, ForeignKey('public.user.id'), nullable=False)
    folder_id = Column(BigInteger, ForeignKey('public.folders.id'), nullable=True)
    is_public = Column(Boolean, nullable=False, default=False)
    status = Column(SmallInteger, nullable=False, default=1)  # 1=草稿, 2=发布, 3=归档
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    excerpt = Column(Text, nullable=True)
    category_id = Column(BigInteger, ForeignKey('public.categories.id'), nullable=True)
    tags = Column(ARRAY(Text), nullable=True)
    
    # 保留字段
    reserved_field1 = Column(Text, nullable=True)
    reserved_field2 = Column(Text, nullable=True)
    reserved_field3 = Column(Text, nullable=True)

