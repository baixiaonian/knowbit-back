"""
AI服务 - 支持不同大模型提供商的流式调用
"""
import httpx
import json
from typing import AsyncGenerator, Optional
from app.models.user_llm_config import UserLLMConfig
from app.core.prompts import prompt_manager


class AIService:
    """AI服务类，支持多种大模型提供商"""
    
    def __init__(self, config: UserLLMConfig):
        """
        初始化AI服务
        
        Args:
            config: 用户的大模型配置
        """
        self.config = config
        self.provider = config.provider.lower()
        
    async def generate_stream(
        self, 
        user_prompt: str,
        prompt_type: str = "ai_help_write",
        custom_system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        流式生成内容
        
        Args:
            user_prompt: 用户提示词
            prompt_type: 提示词类型（如 ai_help_write, ai_continue_write 等）
            custom_system_prompt: 自定义系统提示词（如果提供，会覆盖默认提示词）
            context: 文档上下文
            
        Yields:
            生成的内容片段
        """
        # 获取系统提示词（优先使用自定义提示词）
        system_prompt = prompt_manager.get_prompt(prompt_type, custom_system_prompt)
        
        if self.provider == 'openai':
            async for chunk in self._openai_stream(user_prompt, system_prompt, context):
                yield chunk
        elif self.provider == 'azure':
            async for chunk in self._azure_stream(user_prompt, system_prompt, context):
                yield chunk
        elif self.provider == 'claude':
            async for chunk in self._claude_stream(user_prompt, system_prompt, context):
                yield chunk
        else:
            # 默认使用OpenAI兼容格式
            async for chunk in self._openai_stream(user_prompt, system_prompt, context):
                yield chunk
    
    def _build_messages(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> list:
        """
        构建消息列表
        
        Args:
            user_prompt: 用户提示词
            system_prompt: 系统提示词
            context: 文档上下文
            
        Returns:
            消息列表
        """
        messages = []
        
        # 添加系统提示词
        messages.append({
            "role": "system",
            "content": system_prompt
        })
        
        # 如果有上下文，添加到用户消息中
        if context:
            full_prompt = f"当前文档内容：\n{context}\n\n用户需求：{user_prompt}"
        else:
            full_prompt = user_prompt
        
        messages.append({
            "role": "user",
            "content": full_prompt
        })
        
        return messages
    
    async def _openai_stream(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        OpenAI流式生成
        """
        messages = self._build_messages(user_prompt, system_prompt, context)
        
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": self.config.model_name or "gpt-4",
            "messages": messages,
            "max_tokens": self.config.max_tokens or 2000,
            "temperature": float(self.config.temperature) if self.config.temperature else 0.7,
            "stream": True,
        }
        
        api_base = self.config.api_base or "https://api.openai.com/v1"
        url = f"{api_base}/chat/completions"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"API调用失败: {response.status_code} - {error_text.decode()}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]  # 去掉 "data: " 前缀
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    
    async def _azure_stream(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Azure OpenAI流式生成
        """
        messages = self._build_messages(user_prompt, system_prompt, context)
        
        headers = {
            "api-key": self.config.api_key,
            "Content-Type": "application/json",
        }
        
        payload = {
            "messages": messages,
            "max_tokens": self.config.max_tokens or 2000,
            "temperature": float(self.config.temperature) if self.config.temperature else 0.7,
            "stream": True,
        }
        
        url = f"{self.config.api_base}/openai/deployments/{self.config.model_name}/chat/completions?api-version=2023-05-15"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"API调用失败: {response.status_code} - {error_text.decode()}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        
                        if data == "[DONE]":
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
    
    async def _claude_stream(
        self,
        user_prompt: str,
        system_prompt: Optional[str] = None,
        context: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Claude流式生成
        """
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        
        # Claude的系统提示词单独传递
        if context:
            full_prompt = f"当前文档内容：\n{context}\n\n用户需求：{user_prompt}"
        else:
            full_prompt = user_prompt
        
        payload = {
            "model": self.config.model_name or "claude-3-opus-20240229",
            "max_tokens": self.config.max_tokens or 2000,
            "temperature": float(self.config.temperature) if self.config.temperature else 0.7,
            "stream": True,
            "messages": [
                {
                    "role": "user",
                    "content": full_prompt
                }
            ]
        }
        
        payload["system"] = system_prompt
        
        api_base = self.config.api_base or "https://api.anthropic.com"
        url = f"{api_base}/v1/messages"
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    raise Exception(f"API调用失败: {response.status_code} - {error_text.decode()}")
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        
                        try:
                            chunk = json.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                content = delta.get("text", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

