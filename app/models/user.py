"""
用户模型
"""
from sqlalchemy import Column, BigInteger, String, Boolean, TIMESTAMP, func
from app.db.database import Base


class User(Base):
    __tablename__ = "user"
    __table_args__ = {'schema': 'public'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    username = Column(String(64), unique=True, nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    phone = Column(String(20), unique=True, nullable=True)
    phone_verified = Column(Boolean, nullable=False, default=False)
    avatar_url = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, nullable=False, default=True)
    is_deleted = Column(Boolean, nullable=False, default=False)
    wechat_openid = Column(String(64), unique=True, nullable=True)  # 微信OpenID

