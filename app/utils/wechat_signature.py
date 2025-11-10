"""
微信签名验证工具
"""
import hashlib
from typing import List


def verify_signature(token: str, timestamp: str, nonce: str, signature: str) -> bool:
    """
    验证微信服务器请求的签名
    
    Args:
        token: 服务器配置中的Token
        timestamp: 时间戳
        nonce: 随机字符串
        signature: 微信传来的签名
    
    Returns:
        bool: 验证是否通过
    """
    # 将token、timestamp、nonce按字典序排序
    tmp_arr: List[str] = [token, timestamp, nonce]
    tmp_arr.sort()
    
    # 拼接字符串并sha1加密
    tmp_str = ''.join(tmp_arr)
    tmp_str = hashlib.sha1(tmp_str.encode('utf-8')).hexdigest()
    
    # 与signature比对
    return tmp_str == signature

