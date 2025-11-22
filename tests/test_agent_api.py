"""
测试智能体API服务

前置要求：
1. 后端服务运行在 http://localhost:8000
2. 用户已配置LLM API Key
3. 安装依赖：pip install httpx websockets
"""
import asyncio
import json
import sys
from typing import List, Dict, Any, Optional

try:
    import httpx
except ImportError:
    print("❌ 缺少依赖: httpx")
    print("请运行: pip install httpx")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("❌ 缺少依赖: websockets")
    print("请运行: pip install websockets")
    sys.exit(1)


class AgentAPITester:
    """智能体API测试器"""
    
    def __init__(self, base_url: str = "http://localhost:8000", user_id: int = 1):
        self.base_url = base_url
        self.user_id = user_id
        self.events_received: List[Dict[str, Any]] = []
        
        # 生成一个有效的JWT token用于测试
        from app.utils.auth import create_access_token
        from datetime import timedelta
        
        # 创建测试用的JWT token
        token_data = {"sub": str(user_id)}
        self.token = create_access_token(data=token_data, expires_delta=timedelta(hours=1))
        
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def execute_agent(
        self,
        user_prompt: str,
        document_id: Optional[int] = None,
        selected_document_ids: Optional[List[int]] = None,
        target_selection: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """执行智能体任务"""
        payload = {
            "userPrompt": user_prompt,
        }
        
        if document_id:
            payload["documentId"] = document_id
        if selected_document_ids:
            payload["selectedDocumentIds"] = selected_document_ids
        if target_selection:
            payload["targetSelection"] = target_selection
        if session_id:
            payload["sessionId"] = session_id
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/api/agent/writer/execute",
                headers=self.headers,
                json=payload
            )
            
            if response.status_code != 200:
                raise Exception(f"API请求失败: {response.status_code}")
            
            result = response.json()
            session_id = result.get("sessionId")
            return session_id
    
    async def listen_events(self, session_id: str, timeout: int = 120):
        """监听WebSocket事件"""
        # 构建WebSocket URL
        base_host = self.base_url.replace('http://', '').replace('https://', '')
        ws_url = f"ws://{base_host}/api/agent/ws/{session_id}"
        
        try:
            # 使用websockets库连接
            async with websockets.connect(ws_url, ping_interval=None) as websocket:
                start_time = asyncio.get_event_loop().time()
                
                while True:
                    try:
                        # 设置超时
                        elapsed = asyncio.get_event_loop().time() - start_time
                        if elapsed > timeout:
                            break
                        
                        # 接收事件（设置较短的超时以便检查总超时）
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=min(5.0, timeout - elapsed)
                        )
                        
                        event = json.loads(message)
                        self.events_received.append(event)
                        
                        # 只打印原始的JSON输出
                        print(json.dumps(event, ensure_ascii=False, indent=2))
                        
                        event_type = event.get("type", "unknown")
                        if event_type == "session_closed":
                            break
                        
                    except asyncio.TimeoutError:
                        # 检查是否应该继续等待
                        elapsed = asyncio.get_event_loop().time() - start_time
                        if elapsed < timeout:
                            continue
                        else:
                            break
                    
        except Exception:
            pass
    
    async def test_basic_execution(self):
        """测试基本执行（无文档）"""
        session_id = await self.execute_agent(
            user_prompt="写一篇关于库里的成长的短文，大约500字"
        )
        
        await self.listen_events(session_id, timeout=60)
    
    async def test_document_editing(self, document_id: int):
        """测试文档编辑"""
        session_id = await self.execute_agent(
            user_prompt="将文档改写成更专业的语气",
            document_id=document_id
        )
        
        await self.listen_events(session_id, timeout=120)
    
    async def test_selected_documents_search(self, document_ids: List[int]):
        """测试指定文档搜索"""
        session_id = await self.execute_agent(
            user_prompt="基于这些文档，总结一下主要内容",
            selected_document_ids=document_ids
        )
        
        await self.listen_events(session_id, timeout=120)
    
    async def test_target_selection(self, document_id: int):
        """测试选中文本编辑"""
        session_id = await self.execute_agent(
            user_prompt="将选中的文本改写得更加生动",
            document_id=document_id,
            target_selection={
                "text": "这是一段测试文本",
                "startOffset": 0,
                "endOffset": 10
            }
        )
        
        await self.listen_events(session_id, timeout=120)


async def main():
    """主测试函数"""
    # 配置
    base_url = "http://localhost:8000"
    user_id = 1
    
    tester = AgentAPITester(base_url=base_url, user_id=user_id)
    
    # 测试1: 基本执行
    try:
        await tester.test_basic_execution()
    except Exception:
        pass
    
    # 测试2: 文档编辑（需要提供真实的文档ID）
    # document_id = 123  # 替换为实际的文档ID
    # try:
    #     await tester.test_document_editing(document_id)
    # except Exception:
    #     pass
    
    # 测试3: 指定文档搜索
    # document_ids = [123, 456]  # 替换为实际的文档ID列表
    # try:
    #     await tester.test_selected_documents_search(document_ids)
    # except Exception:
    #     pass


if __name__ == "__main__":
    asyncio.run(main())

