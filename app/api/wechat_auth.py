"""
微信认证API
"""
import time
import xml.etree.ElementTree as ET
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db
from app.core.config import settings
from app.utils.wechat_signature import verify_signature
from app.services.auth_service import AuthService
from app.services.wechat_service import WechatService
from app.schemas.wechat_auth import VerifyCodeRequest
from app.schemas.common import ResponseModel
from app.utils.auth import create_access_token

router = APIRouter(tags=["微信认证"])


@router.get("/api/wechat/callback")
async def wechat_callback_verify(
    signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """
    微信服务器配置验证（GET请求）
    微信首次配置时会调用此接口进行验证
    """
    if not settings.WECHAT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="微信Token未配置"
        )
    
    # 验证签名
    if verify_signature(settings.WECHAT_TOKEN, timestamp, nonce, signature):
        return PlainTextResponse(content=echostr)
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="签名验证失败"
        )


@router.post("/api/wechat/callback")
async def wechat_callback_message(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    接收微信消息和事件推送（POST请求）
    处理用户发送的"666"消息
    """
    # 验证签名（微信POST请求也会带签名参数）
    query_params = request.query_params
    signature = query_params.get("signature")
    timestamp = query_params.get("timestamp")
    nonce = query_params.get("nonce")
    
    if not signature or not timestamp or not nonce:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少签名参数"
        )
    
    if not settings.WECHAT_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="微信Token未配置"
        )
    
    # 验证签名
    if not verify_signature(settings.WECHAT_TOKEN, timestamp, nonce, signature):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="签名验证失败"
        )
    
    # 解析XML消息
    body = await request.body()
    root = ET.fromstring(body)
    
    # 提取消息信息
    msg_type = root.find("MsgType").text if root.find("MsgType") is not None else ""
    from_user = root.find("FromUserName").text if root.find("FromUserName") is not None else ""
    
    # 处理文本消息
    if msg_type == "text":
        content = root.find("Content").text if root.find("Content") is not None else ""
        to_user = root.find("ToUserName").text if root.find("ToUserName") is not None else ""
        
        # 检查是否为"666"
        if content.strip() == "666":
            # 生成验证码
            try:
                verification_code = await AuthService.create_login_code(db, from_user)
                # 直接回复验证码（替代客服消息）
                response_xml = f"""<xml>
<ToUserName><![CDATA[{from_user}]]></ToUserName>
<FromUserName><![CDATA[{to_user}]]></FromUserName>
<CreateTime>{int(time.time())}</CreateTime>
<MsgType><![CDATA[text]]></MsgType>
<Content><![CDATA[您的登录验证码：{verification_code}，请在1分钟内使用]]></Content>
</xml>"""
                return PlainTextResponse(content=response_xml, media_type="application/xml")
            except Exception as e:
                print(f"处理666消息异常: {e}")
                # 即使出错也返回成功，避免微信重复推送
                return ""
    
    # 处理关注事件
    elif msg_type == "event":
        event = root.find("Event").text if root.find("Event") is not None else ""
        if event == "subscribe":
            # 用户关注，可以在这里做一些处理
            pass
    
    # 返回空响应
    return ""


@router.post("/auth/wechat/verify", response_model=ResponseModel)
async def verify_code(
    request: VerifyCodeRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    验证登录验证码
    
    请求体:
    {
        "code": "123456"
    }
    
    返回:
    {
        "code": 200,
        "data": {
            "token": "jwt_token",
            "user": {...}
        }
    }
    """
    # 验证验证码
    user = await AuthService.verify_login_code(db, request.code)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="验证码无效或已过期"
        )
    
    # 生成JWT token
    token_data = {"sub": str(user.id), "openid": user.wechat_openid}
    access_token = create_access_token(data=token_data)
    
    # 返回用户信息
    user_data = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "phone": user.phone,
        "avatar_url": user.avatar_url,
        "wechat_openid": user.wechat_openid,
        "created_at": user.created_at.isoformat() if user.created_at else None
    }
    
    return ResponseModel(
        code=200,
        message="登录成功",
        data={
            "token": access_token,
            "user": user_data
        }
    )

