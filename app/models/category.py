"""
分类模型
"""
from sqlalchemy import Column, BigInteger, String, TIMESTAMP, ForeignKey, Text, func
from app.db.database import Base


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = {'schema': 'public'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(BigInteger, ForeignKey('public.categories.id'), nullable=True)
    slug = Column(String(120), unique=True, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    
    # 保留字段
    reserved_field1 = Column(Text, nullable=True)
    reserved_field2 = Column(Text, nullable=True)
    reserved_field3 = Column(Text, nullable=True)

