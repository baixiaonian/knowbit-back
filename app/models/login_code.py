"""
登录验证码模型
"""
from sqlalchemy import Column, BigInteger, String, Boolean, TIMESTAMP, ForeignKey, func
from app.db.database import Base


class LoginCode(Base):
    __tablename__ = "login_code"
    __table_args__ = {'schema': 'public'}
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    openid = Column(String(64), nullable=False)
    verification_code = Column(String(6), nullable=False)
    expire_at = Column(TIMESTAMP(timezone=True), nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    user_id = Column(BigInteger, ForeignKey('public.user.id'), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

