"""
认证工具函数
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from fastapi import Header, HTTPException, status
from app.core.config import settings


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    创建JWT访问token
    
    Args:
        data: 要编码到token中的数据
        expires_delta: token过期时间增量，默认使用配置中的时间
    
    Returns:
        str: JWT token字符串
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def verify_token(token: str, raise_on_error: bool = True) -> Optional[Dict[str, Any]]:
    """
    验证JWT token
    
    Args:
        token: JWT token字符串
        raise_on_error: 验证失败时是否抛出异常，False时返回None
    
    Returns:
        Dict: token中的payload数据，验证失败时返回None（如果raise_on_error=False）
    
    Raises:
        HTTPException: token无效或过期（如果raise_on_error=True）
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        if raise_on_error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token无效或已过期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return None


async def get_current_user_id(authorization: Optional[str] = Header(None)) -> int:
    """
    从请求头获取当前用户ID（通过JWT token）
    
    如果未提供token或token无效，为了向后兼容，返回默认用户ID 1（用于测试/开发环境）
    生产环境建议移除向后兼容逻辑，强制要求有效的JWT token
    
    Args:
        authorization: Authorization请求头，格式为 "Bearer {token}"
    
    Returns:
        int: 用户ID
    
    Raises:
        HTTPException: token格式错误但能解析到值，或token有效但格式错误
    """
    # # 如果未提供authorization或为空字符串，返回默认用户ID（向后兼容）
    # if not authorization or authorization.strip() == "":
    #     # 开发/测试环境：返回默认用户ID
    #     # 生产环境建议取消注释下面的代码，强制要求token
    #     # raise HTTPException(
    #     #     status_code=status.HTTP_401_UNAUTHORIZED,
    #     #     detail="未提供认证信息",
    #     #     headers={"WWW-Authenticate": "Bearer"},
    #     # )
    #     return 1
    
    # 尝试提取token
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            # 如果格式不对，但提供了值，尝试解析为user_id（向后兼容）
            try:
                return int(authorization.split()[-1])
            except (ValueError, IndexError):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="认证格式错误，应为: Bearer {token}",
                    headers={"WWW-Authenticate": "Bearer"},
                )
    except ValueError:
        # 如果无法分割，尝试直接解析为user_id（向后兼容）
        try:
            if authorization.startswith("Bearer "):
                user_id = int(authorization.split(" ")[1])
                return user_id
            else:
                return 1
        except (ValueError, IndexError):
            return 1
    
    # 验证JWT token（开发环境下失败时返回默认用户ID）
    if settings.DEBUG:
        # 开发环境：尝试验证token，失败则返回默认用户ID
        try:
            payload = verify_token(token, raise_on_error=False)
            if payload:
                user_id: str = payload.get("sub")
                if user_id:
                    return int(user_id)
        except Exception:
            pass
        # 验证失败或没有有效token，返回默认用户ID
        return 1
    else:
        # 生产环境：严格验证token
        payload = verify_token(token, raise_on_error=True)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token中未找到用户ID",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return int(user_id)

