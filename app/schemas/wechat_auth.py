"""
微信认证相关Schema
"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class VerifyCodeRequest(BaseModel):
    """验证码验证请求"""
    code: str


class VerifyCodeResponse(BaseModel):
    """验证码验证响应"""
    token: str
    user: dict


class WechatMessage(BaseModel):
    """微信消息基础结构（用于XML解析）"""
    ToUserName: str
    FromUserName: str
    CreateTime: int
    MsgType: str
    Content: Optional[str] = None
    Event: Optional[str] = None
    EventKey: Optional[str] = None

