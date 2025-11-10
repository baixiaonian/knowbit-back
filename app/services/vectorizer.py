"""
文档向量化服务（基于LangChain）
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List, Tuple, Dict
import tiktoken
import httpx
import json
import re
from html.parser import HTMLParser


class HTMLTextExtractor(HTMLParser):
    """HTML文本提取器（提取纯文本，保留段落结构）"""
    
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self.current_text = ""
        
    def handle_data(self, data: str):
        """处理文本数据"""
        self.current_text += data
        
    def handle_starttag(self, tag: str, attrs: list):
        """处理开始标签（保留有意义的换行）"""
        # 块级元素：添加换行
        block_tags = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                     'li', 'blockquote', 'pre', 'hr', 'br']
        if tag in block_tags:
            if self.current_text.strip():
                self.text_parts.append(self.current_text.strip())
                self.current_text = ""
            if tag == 'br':
                self.current_text += "\n"
        elif tag == 'br':
            self.current_text += "\n"
            
    def handle_endtag(self, tag: str):
        """处理结束标签"""
        block_tags = ['p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                     'li', 'blockquote', 'pre']
        if tag in block_tags:
            if self.current_text.strip():
                self.text_parts.append(self.current_text.strip())
                self.current_text = ""
    
    def get_text(self) -> str:
        """获取清理后的纯文本"""
        if self.current_text.strip():
            self.text_parts.append(self.current_text.strip())
        return "\n\n".join(filter(None, self.text_parts))


class DocumentVectorizer:
    """文档向量化服务"""
    
    @staticmethod
    def clean_html(html_content: str) -> str:
        """
        清理HTML内容，提取纯文本
        
        Args:
            html_content: HTML格式的文档内容
            
        Returns:
            清理后的纯文本内容
        """
        if not html_content:
            return ""
        
        # 检查是否包含HTML标签
        has_html_tags = bool(re.search(r'<[^>]+>', html_content))
        
        if not has_html_tags:
            # 不是HTML，直接返回
            return html_content
        
        # 提取纯文本
        extractor = HTMLTextExtractor()
        extractor.feed(html_content)
        clean_text = extractor.get_text()
        
        # 额外清理：移除多余的空白字符
        clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)  # 最多保留两个换行
        clean_text = re.sub(r'[ \t]+', ' ', clean_text)     # 多个空格合并为一个
        clean_text = clean_text.strip()
        
        return clean_text
    
    def __init__(
        self,
        api_key: str,
        api_base: str = None,
        model: str = "text-embedding-3-small",
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        """
        初始化向量化服务
        
        Args:
            api_key: OpenAI API密钥
            api_base: API基础URL（可选）
            model: Embedding模型名称
            chunk_size: 每个分块的最大token数
            chunk_overlap: 分块之间的重叠token数
        """
        # 保存配置
        self.api_key = api_key
        self.api_base = api_base or "https://api.openai.com/v1"
        self.model = model
        
        # 初始化文本分块器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=self._count_tokens,
            separators=[
                "\n\n",   # 优先在段落处分割
                "\n",     # 其次在换行处
                "。",     # 中文句号
                "！",     # 中文感叹号  
                "？",     # 中文问号
                ".",      # 英文句号
                "!",      # 英文感叹号
                "?",      # 英文问号
                " ",      # 空格
                ""        # 最后才在字符处分割
            ]
        )
        
        # Token计数器
        self.encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
    
    def _count_tokens(self, text: str) -> int:
        """
        计算文本的token数量
        
        Args:
            text: 文本内容
            
        Returns:
            token数量
        """
        return len(self.encoding.encode(text))
    
    def split_text(self, content: str) -> List[str]:
        """
        文本分块（自动处理HTML内容）
        
        Args:
            content: 原始文档内容（可能是HTML格式）
            
        Returns:
            分块后的文本列表
        """
        # 清理HTML，提取纯文本
        clean_content = self.clean_html(content)
        
        # 分块
        chunks = self.text_splitter.split_text(clean_content)
        return chunks
    
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        批量向量化文本（使用原生httpx，兼容qwen等模型）
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表
        """
        url = f"{self.api_base}/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "input": texts,  # 支持数组
            "encoding_format": "float"
        }
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            
            if response.status_code != 200:
                raise Exception(f"Embedding API调用失败: {response.status_code} - {response.text}")
            
            result = response.json()
            embeddings = [item["embedding"] for item in result["data"]]
            return embeddings
    
    async def embed_query(self, text: str) -> List[float]:
        """
        向量化查询文本
        
        Args:
            text: 查询文本
            
        Returns:
            向量
        """
        # 单个文本也使用embed_texts
        embeddings = await self.embed_texts([text])
        return embeddings[0]
    
    async def process_document(
        self, 
        content: str,
        metadata: Dict = None
    ) -> List[Dict]:
        """
        完整流程：分块 + 向量化
        
        Args:
            content: 文档内容
            metadata: 额外的元数据（可选）
            
        Returns:
            处理结果列表：[{
                'content': str,
                'embedding': List[float],
                'chunk_index': int,
                'token_count': int,
                'metadata': dict
            }, ...]
        """
        # 1. 分块
        chunks = self.split_text(content)
        
        if not chunks:
            return []
        
        # 2. 批量向量化（调用OpenAI API）
        embeddings = await self.embed_texts(chunks)
        
        # 3. 组装结果
        results = []
        for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            token_count = self._count_tokens(chunk)
            
            chunk_metadata = metadata.copy() if metadata else {}
            chunk_metadata.update({
                'chunk_size': len(chunk),
                'position': idx
            })
            
            results.append({
                'content': chunk,
                'embedding': embedding,
                'chunk_index': idx,
                'token_count': token_count,
                'metadata': chunk_metadata
            })
        
        return results
    
    def get_stats(self, content: str) -> Dict:
        """
        获取文档统计信息（不调用API）
        
        Args:
            content: 文档内容（可能是HTML格式）
            
        Returns:
            统计信息：{
                'total_chars': int,
                'total_tokens': int,
                'estimated_chunks': int,
                'html_cleaned': bool  # 是否为HTML内容
            }
        """
        # 清理HTML
        clean_content = self.clean_html(content)
        has_html = content != clean_content
        
        chunks = self.split_text(content)
        total_tokens = self._count_tokens(clean_content)
        
        return {
            'total_chars': len(clean_content),  # 使用清理后的长度
            'total_tokens': total_tokens,
            'estimated_chunks': len(chunks),
            'html_cleaned': has_html,
            'original_chars': len(content) if has_html else None
        }


