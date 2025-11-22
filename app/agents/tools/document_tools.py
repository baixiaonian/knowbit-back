"""
文档相关工具
"""
import re
from html.parser import HTMLParser
from typing import Optional, Literal, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from langchain.tools import BaseTool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.models.document import Document
from app.agents.event_manager import AgentEventManager


def parse_html_paragraphs(html_content: str) -> List[Dict[str, Any]]:
    """解析HTML内容，识别块级元素作为段落"""
    paragraphs = []
    
    # 检查是否为HTML格式（包含HTML标签）
    if not re.search(r'<[^>]+>', html_content):
        # 不是HTML格式，按原来的方式处理（按双换行符切分）
        raw_paragraphs = html_content.split('\n\n')
        current_offset = 0
        
        for idx, para_text in enumerate(raw_paragraphs):
            para_text = para_text.strip()
            if not para_text:
                current_offset += 2
                continue
            
            start_offset = html_content.find(para_text, current_offset)
            if start_offset == -1:
                start_offset = current_offset
            end_offset = start_offset + len(para_text)
            
            paragraphs.append({
                'id': f"p_{idx + 1}",
                'tag': 'text',
                'content': para_text,
                'html_content': para_text,
                'startOffset': start_offset,
                'endOffset': end_offset,
            })
            current_offset = end_offset
        
        return paragraphs
    
    # HTML格式：使用正则表达式匹配块级元素
    # 匹配模式：<tag attr="value">content</tag>
    block_elements = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'div', 'li', 
                      'blockquote', 'pre', 'article', 'section', 'aside']
    
    # 创建匹配所有块级元素的正则表达式
    # 匹配非自闭合标签：<tag attr="value">content</tag>
    tag_pattern = '|'.join(block_elements)
    pattern = rf'<({tag_pattern})([^>]*)>(.*?)</\1>'
    
    matches = list(re.finditer(pattern, html_content, re.DOTALL | re.IGNORECASE))
    
    for idx, match in enumerate(matches):
        tag = match.group(1).lower()
        attrs_str = match.group(2)
        inner_html = match.group(3)
        
        # 提取属性（特别是id）
        id_match = re.search(r'id=["\']([^"\']+)["\']', attrs_str)
        element_id = id_match.group(1) if id_match else ""
        
        # 提取纯文本内容（递归移除内部HTML标签）
        text_content = re.sub(r'<[^>]+>', '', inner_html).strip()
        
        # 如果文本内容为空，跳过
        if not text_content:
            continue
        
        # 计算位置
        start_offset = match.start()
        end_offset = match.end()
        
        paragraphs.append({
            'id': element_id if element_id else f"{tag}_{idx + 1}",
            'tag': tag,
            'content': text_content,
            'html_content': match.group(0),  # 完整的HTML标签及其内容
            'startOffset': start_offset,
            'endOffset': end_offset,
        })
    
    # 如果没有匹配到任何块级元素，尝试按行分割
    if not paragraphs:
        # 使用HTMLParser提取文本块
        parser = HTMLTextExtractor()
        parser.feed(html_content)
        text_parts = parser.get_text().split('\n\n')
        
        current_offset = 0
        for idx, text_part in enumerate(text_parts):
            text_part = text_part.strip()
            if not text_part:
                continue
            
            # 在原始HTML中查找文本位置（近似）
            start_offset = html_content.find(text_part[:20], current_offset)
            if start_offset == -1:
                start_offset = current_offset
            
            paragraphs.append({
                'id': f"p_{idx + 1}",
                'tag': 'text',
                'content': text_part,
                'html_content': text_part,
                'startOffset': start_offset,
                'endOffset': start_offset + len(text_part),
            })
            current_offset = start_offset + len(text_part)
    
    return paragraphs


class HTMLTextExtractor(HTMLParser):
    """简单的HTML文本提取器（用于回退方案）"""
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.current_text = ""
        self.block_tags = {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                          'li', 'blockquote', 'pre', 'br'}
    
    def handle_data(self, data: str):
        self.current_text += data
    
    def handle_starttag(self, tag: str, attrs: list):
        if tag.lower() in self.block_tags:
            if self.current_text.strip():
                self.text_parts.append(self.current_text.strip())
                self.current_text = ""
    
    def handle_endtag(self, tag: str):
        if tag.lower() in {'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'}:
            if self.current_text.strip():
                self.text_parts.append(self.current_text.strip())
                self.current_text = ""
    
    def get_text(self) -> str:
        if self.current_text.strip():
            self.text_parts.append(self.current_text.strip())
        return "\n\n".join(self.text_parts)


class DocumentReadInput(BaseModel):
    document_id: int


class DocumentReadTool(BaseTool):
    name = "document_reader"
    description = "读取指定文档全文内容，输入 {document_id}."
    args_schema = DocumentReadInput

    def __init__(self, user_id: int):
        super().__init__()
        object.__setattr__(self, 'user_id', user_id)

    async def _arun(self, document_id: int):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Document).where(Document.id == document_id, Document.author_id == self.user_id)
            )
            document = result.scalar_one_or_none()
            if not document:
                return "Document not found"
            return document.content or ""

    async def _run(self, *args, **kwargs):
        return await self._arun(**kwargs)


# 🆕 新增: 文档分析工具（用于段落编辑模式）
class DocumentAnalysisInput(BaseModel):
    """文档分析输入"""
    document_id: int = Field(..., description="需要分析的文档ID")
    user_intent: str = Field(..., description="用户意图描述")
    target_selection: Optional[dict] = Field(None, description="用户选中的文本范围")


class DocumentAnalysisTool(BaseTool):
    """文档分析工具 - 分析文档结构并识别需要修改的段落"""
    name = "document_analyzer"
    description = (
        "分析文档结构，根据用户意图和选中文本自动识别需要修改的段落范围。"
        "使用此工具时，需要提供document_id（文档ID）和user_intent（用户意图描述）。"
        "可以可选提供target_selection（用户选中的文本范围）。"
        "返回文档的段落结构列表，包含每个段落的ID、内容和位置信息。"
    )
    args_schema = DocumentAnalysisInput

    def __init__(self, user_id: int):
        super().__init__()
        object.__setattr__(self, 'user_id', user_id)

    async def _arun(
        self, 
        document_id: int, 
        user_intent: str,
        target_selection: Optional[dict] = None
    ):
        """分析文档并返回段落结构"""
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Document).where(
                    Document.id == document_id, 
                    Document.author_id == self.user_id
                )
            )
            document = result.scalar_one_or_none()
            if not document:
                return "Document not found"
            
            content = document.content or ""
            if not content.strip():
                return "Document is empty"
            
            # 解析段落（自动识别HTML或纯文本格式）
            raw_paragraphs = parse_html_paragraphs(content)
            paragraphs = []
            
            for idx, para_data in enumerate(raw_paragraphs):
                paragraph_info = {
                    "id": para_data.get('id', f"p_{idx + 1}"),
                    "content": para_data['content'],
                    "type": para_data.get('tag', 'paragraph'),
                    "tag": para_data.get('tag', 'paragraph'),
                    "htmlContent": para_data.get('html_content', para_data['content']),
                    "startOffset": para_data['startOffset'],
                    "endOffset": para_data['endOffset'],
                    "isRelevant": self._is_relevant_to_selection(
                        para_data['startOffset'], para_data['endOffset'], target_selection
                    ),
                    # 如果没有选中文本，则所有段落都相关（用于全文档改写场景）
                    "shouldProcess": target_selection is None or self._is_relevant_to_selection(
                        para_data['startOffset'], para_data['endOffset'], target_selection
                    )
                }
                paragraphs.append(paragraph_info)
            
            # 构建返回结果
            result_data = {
                "documentId": document_id,
                "totalParagraphs": len(paragraphs),
                "paragraphs": paragraphs,
                "userIntent": user_intent,
                "targetSelection": target_selection
            }
            
            # 返回JSON字符串，方便智能体解析
            import json
            return json.dumps(result_data, ensure_ascii=False, indent=2)

    def _is_relevant_to_selection(
        self, 
        start_offset: int, 
        end_offset: int, 
        target_selection: Optional[dict]
    ) -> bool:
        """判断段落是否与用户选中的文本相关"""
        if not target_selection:
            return False
        
        sel_start = target_selection.get("startOffset")
        sel_end = target_selection.get("endOffset")
        
        if sel_start is None or sel_end is None:
            return False
        
        # 判断段落与选中范围是否有重叠
        return not (end_offset < sel_start or start_offset > sel_end)

    async def _run(self, *args, **kwargs):
        return await self._arun(*args, **kwargs)


# 🆕 新增: 段落编辑指令生成工具
class ParagraphEditInstructionInput(BaseModel):
    """段落编辑指令输入"""
    paragraph_id: str = Field(..., description="目标段落ID")
    operation: Literal["replace", "delete", "insert_before", "insert_after"] = Field(
        ..., description="操作类型"
    )
    new_content: Optional[str] = Field(None, description="新内容（delete操作时为空）")
    reasoning: Optional[str] = Field(None, description="修改理由说明")
    original_content: Optional[str] = Field(None, description="原始段落内容")
    start_offset: Optional[int] = Field(None, description="段落在文档中的起始位置")
    end_offset: Optional[int] = Field(None, description="段落在文档中的结束位置")


class ParagraphEditInstructionTool(BaseTool):
    """段落编辑指令生成工具（不直接修改数据库）"""
    name = "paragraph_editor"
    description = (
        "生成段落编辑指令，用于前端实时预览。不直接修改数据库。"
        "这是向前端推送文档内容的唯一方式，所有生成的文本内容都必须通过此工具推送。"
        "请逐个段落调用此工具，每次生成一个段落的编辑指令。"
        "使用此工具时，必须提供paragraph_id（段落ID）和operation（操作类型）。"
        "operation可选值: replace（替换段落）、delete（删除段落）、insert_before（在前插入）、insert_after（在后插入）。"
        "对于新创建的内容（没有document_id时），使用insert_after操作，paragraph_id可以是自动生成的（如p_1, p_2等）。"
        "可以可选提供new_content（新内容）、reasoning（修改原因，建议填写）、original_content（原始内容，新内容时可为空）、start_offset（起始位置）、end_offset（结束位置）。"
        "reasoning字段用于向用户解释修改原因，请务必填写。"
        "重要：所有生成的文档内容都必须通过此工具推送，不要直接在最终回复中返回文本内容。"
    )
    args_schema = ParagraphEditInstructionInput

    def __init__(self, event_manager: AgentEventManager, session_id: str, total_paragraphs: int = 0):
        super().__init__()
        object.__setattr__(self, 'event_manager', event_manager)
        object.__setattr__(self, 'session_id', session_id)
        object.__setattr__(self, 'total_paragraphs', total_paragraphs)
        object.__setattr__(self, 'current_progress', 0)

    async def _arun(
        self, 
        paragraph_id: str,
        operation: str,
        new_content: Optional[str] = None,
        reasoning: Optional[str] = None,
        original_content: Optional[str] = None,
        start_offset: Optional[int] = None,
        end_offset: Optional[int] = None
    ):
        """生成并发布段落编辑指令事件"""
        current_progress = getattr(self, 'current_progress', 0)
        object.__setattr__(self, 'current_progress', current_progress + 1)
        
        # 构建编辑指令数据
        instruction_data = {
            "paragraphId": paragraph_id,
            "operation": operation,
            "newContent": new_content,
            "originalContent": original_content,
            "reasoning": reasoning or f"对段落 {paragraph_id} 执行 {operation} 操作",
            "metadata": {
                "startOffset": start_offset,
                "endOffset": end_offset,
                "originalLength": len(original_content) if original_content else 0,
                "newLength": len(new_content) if new_content else 0,
                "confidence": 0.95
            },
            "timestamp": datetime.utcnow().isoformat(),
            "progress": {
                "current": getattr(self, 'current_progress', 0),
                "total": getattr(self, 'total_paragraphs', 0)
            }
        }
        
        # 立即发布事件到前端
        await self.event_manager.publish(
            self.session_id,
            {
                "type": "paragraph_edit_instruction",
                "data": instruction_data
            }
        )
        
        return f"Edit instruction for paragraph {paragraph_id} generated and sent to frontend"

    async def _run(self, *args, **kwargs):
        return await self._arun(*args, **kwargs)


def create_document_analysis_tool(user_id: int):
    """创建文档分析工具"""
    return DocumentAnalysisTool(user_id=user_id)


def create_paragraph_edit_tool(event_manager: AgentEventManager, session_id: str, total_paragraphs: int = 0):
    """创建段落编辑指令工具"""
    return ParagraphEditInstructionTool(
        event_manager=event_manager,
        session_id=session_id,
        total_paragraphs=total_paragraphs
    )
