"""
智能体相关Schema
"""
from typing import List, Optional
from pydantic import BaseModel, Field


class AgentSnippet(BaseModel):
    documentId: int = Field(..., description="片段所属文档ID")
    content: str = Field(..., description="片段内容")
    source: Optional[str] = Field(None, description="片段来源说明，如手动选取/检索结果")


class AgentTaskCreate(BaseModel):
    description: str = Field(..., description="任务描述")
    priority: int = Field(0, description="任务优先级，数字越大优先级越高")


class TargetSelection(BaseModel):
    """用户选中的文本范围"""
    text: str = Field(..., description="选中的文本内容")
    startOffset: int = Field(..., description="选中文本在文档中的起始位置")
    endOffset: int = Field(..., description="选中文本在文档中的结束位置")


class AgentExecutionRequest(BaseModel):
    """智能体执行请求（统一使用段落编辑模式）"""
    userPrompt: str = Field(..., description="用户当次输入")
    documentId: Optional[int] = Field(None, description="待编辑的文档ID")
    sessionId: Optional[str] = Field(None, description="可选，会话ID；传入时复用同一session记忆")
    selectedSnippets: List[AgentSnippet] = Field(default_factory=list, description="当前对话中选中的文档片段")
    selectedDocumentIds: List[int] = Field(default_factory=list, description="当前对话涉及的文档ID集合")
    
    # 段落编辑模式字段（统一使用）
    targetSelection: Optional[TargetSelection] = Field(None, description="用户在编辑器中的选中文本信息（用于帮助智能体定位）")


class AgentExecutionResponse(BaseModel):
    sessionId: str
    status: str = "accepted"
    message: str = "Agent execution started"


class AgentEvent(BaseModel):
    type: str
    data: dict
