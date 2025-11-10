"""
测试AI RAG问答接口
"""
import asyncio
import httpx
import json


async def test_ai_chat():
    """测试AI问答接口"""
    
    base_url = "http://localhost:8000"
    user_id = 1
    
    # 使用用户ID作为token（简化认证方式）
    token = str(user_id)
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    print("=" * 80)
    print("AI RAG问答接口测试")
    print("=" * 80)
    print()
    
    # 测试用例1：基础问答（在所有文档中检索）
    print("【测试1】基础问答 - 在所有文档中检索")
    print("-" * 80)
    test1_data = {
        "userId": user_id,
        "question": "《寄生虫》这部电影的主要主题是什么？",
        "ragEnabled": True,
        "searchScope": "all"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{base_url}/api/ai-chat/stream",
                headers=headers,
                json=test1_data
            ) as response:
                if response.status_code != 200:
                    print(f"❌ 请求失败！状态码: {response.status_code}")
                    error_text = await response.aread()
                    print(f"错误信息: {error_text.decode()}")
                else:
                    print("✅ 请求成功，开始接收流式响应：\n")
                    print("回答内容：")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # 去掉 "data: " 前缀
                            try:
                                data = json.loads(data_str)
                                if "error" in data:
                                    print(f"\n❌ 错误: {data['error']}")
                                    break
                                elif "content" in data:
                                    print(data["content"], end="", flush=True)
                                elif "done" in data:
                                    print(f"\n\n✅ 完成！Token使用: {data.get('usage', {})}")
                                    break
                            except json.JSONDecodeError:
                                print(f"⚠️  JSON解析失败: {data_str}")
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
    
    print("\n\n")
    
    # 测试用例2：指定文档检索
    print("【测试2】指定文档检索 - 只在文档7中检索")
    print("-" * 80)
    test2_data = {
        "userId": user_id,
        "question": "这部电影的空间设计有什么象征意义？",
        "selectedDocumentIds": [7],
        "ragEnabled": True
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{base_url}/api/ai-chat/stream",
                headers=headers,
                json=test2_data
            ) as response:
                if response.status_code != 200:
                    print(f"❌ 请求失败！状态码: {response.status_code}")
                    error_text = await response.aread()
                    print(f"错误信息: {error_text.decode()}")
                else:
                    print("✅ 请求成功，开始接收流式响应：\n")
                    print("回答内容：")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if "error" in data:
                                    print(f"\n❌ 错误: {data['error']}")
                                    break
                                elif "content" in data:
                                    print(data["content"], end="", flush=True)
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
    
    print("\n\n")
    
    # 测试用例3：带选中文本引用的问答
    print("【测试3】带选中文本引用 - 结合RAG和选中文本")
    print("-" * 80)
    test3_data = {
        "userId": user_id,
        "question": "请详细解释一下这段话的含义",
        "selectedReferences": [
            {
                "text": "《寄生虫》的空间设计极具象征意义。整部电影构建了一个垂直的阶级金字塔",
                "documentId": 7,
                "source": "editor_selection"
            }
        ],
        "ragEnabled": True,
        "searchScope": "all"
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{base_url}/api/ai-chat/stream",
                headers=headers,
                json=test3_data
            ) as response:
                if response.status_code != 200:
                    print(f"❌ 请求失败！状态码: {response.status_code}")
                    error_text = await response.aread()
                    print(f"错误信息: {error_text.decode()}")
                else:
                    print("✅ 请求成功，开始接收流式响应：\n")
                    print("回答内容：")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if "error" in data:
                                    print(f"\n❌ 错误: {data['error']}")
                                    break
                                elif "content" in data:
                                    print(data["content"], end="", flush=True)
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
    
    print("\n\n")
    
    # 测试用例4：禁用RAG，仅使用选中文本
    print("【测试4】禁用RAG - 仅使用选中文本引用")
    print("-" * 80)
    test4_data = {
        "userId": user_id,
        "question": "这段内容主要讲了什么？",
        "selectedReferences": [
            {
                "text": "基泽一家通过精心策划，逐个'寄生'进富人家庭，仿佛一场聪明人的胜利",
                "documentId": 7
            }
        ],
        "ragEnabled": False
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            async with client.stream(
                "POST",
                f"{base_url}/api/ai-chat/stream",
                headers=headers,
                json=test4_data
            ) as response:
                if response.status_code != 200:
                    print(f"❌ 请求失败！状态码: {response.status_code}")
                    error_text = await response.aread()
                    print(f"错误信息: {error_text.decode()}")
                else:
                    print("✅ 请求成功，开始接收流式响应：\n")
                    print("回答内容：")
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                                if "error" in data:
                                    print(f"\n❌ 错误: {data['error']}")
                                    break
                                elif "content" in data:
                                    print(data["content"], end="", flush=True)
                            except json.JSONDecodeError:
                                pass
        except Exception as e:
            print(f"❌ 异常: {str(e)}")
    
    print("\n\n")
    print("=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_ai_chat())

