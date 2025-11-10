"""
微信公众号服务
"""
import httpx
import time
from typing import Optional, Dict, Any
from app.core.config import settings


class WechatService:
    """微信公众号服务类"""
    
    _access_token: Optional[str] = None
    _access_token_expire_at: int = 0
    
    @classmethod
    async def get_access_token(cls) -> str:
        """
        获取微信Access Token（带缓存）
        Access Token有效期为2小时
        """
        current_time = int(time.time())
        
        # 如果token未过期，直接返回缓存的token
        if cls._access_token and current_time < cls._access_token_expire_at:
            return cls._access_token
        
        # 获取新token
        if not settings.WECHAT_APPID or not settings.WECHAT_APPSECRET:
            raise ValueError("微信公众号AppID或AppSecret未配置")
        
        url = "https://api.weixin.qq.com/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": settings.WECHAT_APPID,
            "secret": settings.WECHAT_APPSECRET
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if "access_token" not in data:
                raise ValueError(f"获取Access Token失败: {data}")
            
            cls._access_token = data["access_token"]
            # 提前5分钟过期，避免边界情况
            cls._access_token_expire_at = current_time + data.get("expires_in", 7200) - 300
            
            return cls._access_token
    
    @classmethod
    async def send_custom_message(cls, openid: str, content: str) -> bool:
        """
        发送客服消息给用户
        
        Args:
            openid: 用户OpenID
            content: 消息内容
        
        Returns:
            bool: 是否发送成功
        """
        try:
            access_token = await cls.get_access_token()
            url = f"https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token={access_token}"
            
            payload = {
                "touser": openid,
                "msgtype": "text",
                "text": {
                    "content": content
                }
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                
                if data.get("errcode") == 0:
                    return True
                else:
                    print(f"发送客服消息失败: {data}")
                    return False
        except Exception as e:
            print(f"发送客服消息异常: {e}")
            return False
    
    @classmethod
    async def get_user_info(cls, openid: str) -> Optional[Dict[str, Any]]:
        """
        获取用户信息（需要用户已授权）
        
        Args:
            openid: 用户OpenID
        
        Returns:
            用户信息字典，失败返回None
        """
        try:
            access_token = await cls.get_access_token()
            url = f"https://api.weixin.qq.com/cgi-bin/user/info?access_token={access_token}&openid={openid}&lang=zh_CN"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()
                
                if "errcode" in data and data["errcode"] != 0:
                    return None
                
                return data
        except Exception as e:
            print(f"获取用户信息异常: {e}")
            return None

