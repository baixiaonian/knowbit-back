"""
文件夹模型
"""
from sqlalchemy import Column, BigInteger, String, Boolean, TIMESTAMP, ForeignKey, Text, func
from app.db.database import Base


class Folder(Base):
    __tablename__ = "folders"
    __table_args__ = {'schema': 'public'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    parent_id = Column(BigInteger, ForeignKey('public.folders.id'), nullable=True)
    owner_id = Column(BigInteger, ForeignKey('public.user.id'), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    is_deleted = Column(Boolean, nullable=False, default=False)
    
    # 保留字段
    reserved_field1 = Column(Text, nullable=True)
    reserved_field2 = Column(Text, nullable=True)
    reserved_field3 = Column(Text, nullable=True)

