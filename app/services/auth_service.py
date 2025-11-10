"""
认证服务
"""
import random
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_
from app.core.config import settings
from app.models.user import User
from app.models.login_code import LoginCode
from app.services.wechat_service import WechatService


class AuthService:
    """认证服务类"""
    
    @staticmethod
    def generate_verification_code(length: int = None) -> str:
        """
        生成验证码
        
        Args:
            length: 验证码长度，默认使用配置中的长度
        
        Returns:
            str: 验证码
        """
        if length is None:
            length = settings.LOGIN_CODE_LENGTH
        
        return ''.join([str(random.randint(0, 9)) for _ in range(length)])
    
    @classmethod
    async def create_or_get_user(cls, db: AsyncSession, openid: str) -> User:
        """
        根据OpenID查询或创建用户
        
        Args:
            db: 数据库会话
            openid: 微信OpenID
        
        Returns:
            User: 用户对象
        """
        # 查询现有用户
        stmt = select(User).where(User.wechat_openid == openid, User.is_deleted == False)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if user:
            return user
        
        # 创建新用户
        user = User(
            wechat_openid=openid,
            is_active=True,
            is_deleted=False
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @classmethod
    async def create_login_code(cls, db: AsyncSession, openid: str) -> str:
        """
        为OpenID创建登录验证码
        
        步骤：
        1. 先使同一openid的旧验证码失效
        2. 生成新验证码
        3. 保存到数据库
        4. 通过微信客服消息发送给用户
        
        Args:
            db: 数据库会话
            openid: 微信OpenID
        
        Returns:
            str: 生成的验证码
        """
        # 1. 使同一openid的旧验证码失效
        await db.execute(
            delete(LoginCode).where(
                and_(
                    LoginCode.openid == openid,
                    LoginCode.used == False
                )
            )
        )
        
        # 2. 生成新验证码
        verification_code = cls.generate_verification_code()
        expire_at = datetime.utcnow() + timedelta(seconds=settings.LOGIN_CODE_EXPIRE_SECONDS)
        
        # 3. 保存到数据库
        login_code = LoginCode(
            openid=openid,
            verification_code=verification_code,
            expire_at=expire_at,
            used=False
        )
        db.add(login_code)
        await db.commit()
        
        # 注意：不再通过客服消息发送，改为在API层直接回复
        # 这样可以避免48001权限错误和48小时限制
        
        return verification_code
    
    @classmethod
    async def verify_login_code(cls, db: AsyncSession, code: str) -> Optional[User]:
        """
        验证登录验证码
        
        Args:
            db: 数据库会话
            code: 验证码
        
        Returns:
            User: 验证成功返回用户对象，失败返回None
        """
        # 查询验证码
        stmt = select(LoginCode).where(
            and_(
                LoginCode.verification_code == code,
                LoginCode.used == False,
                LoginCode.expire_at > datetime.utcnow()
            )
        )
        result = await db.execute(stmt)
        login_code = result.scalar_one_or_none()
        
        if not login_code:
            return None
        
        # 标记验证码为已使用
        login_code.used = True
        
        # 获取或创建用户
        user = await cls.create_or_get_user(db, login_code.openid)
        
        # 关联用户ID到验证码记录（可选，用于审计）
        login_code.user_id = user.id
        
        await db.commit()
        
        return user

