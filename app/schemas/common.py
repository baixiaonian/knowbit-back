"""
通用Schema模型
"""
from pydantic import BaseModel
from typing import Generic, TypeVar, Optional, List

T = TypeVar('T')


class ResponseModel(BaseModel):
    """标准响应模型"""
    code: int = 200
    message: Optional[str] = None
    data: Optional[T] = None


class PaginationModel(BaseModel):
    """分页模型"""
    page: int
    limit: int
    total: int
    totalPages: int

