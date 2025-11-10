"""
AI写作工具API演示脚本
展示所有知识库管理和文档管理功能
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"
HEADERS = {
    "Authorization": "Bearer 1",  # 使用已创建的用户ID 1
    "Content-Type": "application/json"
}


def print_response(title, response):
    """打印响应结果"""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")
    print(f"状态码: {response.status_code}")
    if response.status_code == 200:
        print(f"响应: {json.dumps(response.json(), ensure_ascii=False, indent=2)}")
    else:
        print(f"错误: {response.text}")
    return response.status_code == 200


def demo_knowledge_base():
    """演示知识库管理功能"""
    print("\n" + "🚀 AI写作工具 - 知识库管理演示".center(60))
    
    # 1. 获取知识库结构
    response = requests.get(f"{BASE_URL}/api/knowledge-base", headers=HEADERS)
    print_response("📁 获取知识库结构", response)
    
    # 2. 创建根文件夹
    data = {"name": "工作文档", "parentId": None}
    response = requests.post(f"{BASE_URL}/api/folders", headers=HEADERS, json=data)
    success = print_response("📁 创建根文件夹", response)
    if success:
        work_folder_id = response.json()["data"]["id"]
    else:
        work_folder_id = None
    
    # 3. 创建子文件夹
    if work_folder_id:
        data = {"name": "项目资料", "parentId": work_folder_id}
        response = requests.post(f"{BASE_URL}/api/folders", headers=HEADERS, json=data)
        success = print_response("📁 创建子文件夹", response)
        if success:
            project_folder_id = response.json()["data"]["id"]
        else:
            project_folder_id = None
    else:
        project_folder_id = None
    
    # 4. 重命名文件夹
    if work_folder_id:
        data = {"name": "我的工作文档"}
        response = requests.put(f"{BASE_URL}/api/folders/{work_folder_id}/rename", headers=HEADERS, json=data)
        print_response("📁 重命名文件夹", response)
    
    # 5. 获取更新后的知识库结构
    response = requests.get(f"{BASE_URL}/api/knowledge-base", headers=HEADERS)
    print_response("📁 更新后的知识库结构", response)
    
    return project_folder_id


def demo_document_management(folder_id):
    """演示文档管理功能"""
    print("\n" + "📝 AI写作工具 - 文档管理演示".center(60))
    
    # 1. 创建文档
    data = {
        "title": "AI写作工具需求文档",
        "content": """
# AI写作工具需求文档

## 项目概述
这是一个基于AI的智能写作工具，旨在帮助用户提高写作效率和质量。

## 核心功能
1. **AI写作辅助**
   - 智能生成内容
   - 文本扩写和润色
   - 多语言翻译

2. **知识库管理**
   - 文件夹结构管理
   - 文档分类和标签
   - 全文搜索

3. **协作功能**
   - 文档分享
   - 评论系统
   - 版本控制

## 技术栈
- 后端: FastAPI + SQLAlchemy
- 数据库: PostgreSQL
- 前端: React/Vue (待开发)
        """,
        "folderId": folder_id,
        "tags": ["需求", "AI", "写作工具"],
        "isPublic": False,
        "status": 2,  # 发布状态
        "excerpt": "AI写作工具的完整需求文档，包含核心功能和技术架构"
    }
    response = requests.post(f"{BASE_URL}/api/documents", headers=HEADERS, json=data)
    success = print_response("📝 创建文档", response)
    if success:
        doc_id = response.json()["data"]["id"]
    else:
        doc_id = None
    
    # 2. 获取文档详情
    if doc_id:
        response = requests.get(f"{BASE_URL}/api/documents/{doc_id}", headers=HEADERS)
        print_response("📝 获取文档详情", response)
    
    # 3. 自动保存文档
    if doc_id:
        data = {
            "content": """
# AI写作工具需求文档 (更新版)

## 项目概述
这是一个基于AI的智能写作工具，旨在帮助用户提高写作效率和质量。

## 核心功能
1. **AI写作辅助**
   - 智能生成内容
   - 文本扩写和润色
   - 多语言翻译
   - 语法检查

2. **知识库管理**
   - 文件夹结构管理
   - 文档分类和标签
   - 全文搜索
   - 智能推荐

3. **协作功能**
   - 文档分享
   - 评论系统
   - 版本控制
   - 实时协作

## 技术栈
- 后端: FastAPI + SQLAlchemy + PostgreSQL
- 前端: React/Vue + TypeScript
- AI: OpenAI GPT / 本地模型
            """,
            "excerpt": "AI写作工具的完整需求文档，包含核心功能、技术架构和最新更新"
        }
        response = requests.post(f"{BASE_URL}/api/documents/{doc_id}/autosave", headers=HEADERS, json=data)
        print_response("💾 自动保存文档", response)
    
    # 4. 获取文档列表
    response = requests.get(f"{BASE_URL}/api/documents?page=1&limit=5", headers=HEADERS)
    print_response("📝 获取文档列表", response)
    
    # 5. 搜索文档
    response = requests.get(f"{BASE_URL}/api/documents?search=AI&status=2", headers=HEADERS)
    print_response("🔍 搜索文档", response)
    
    # 6. 增加文档查看次数
    if doc_id:
        response = requests.post(f"{BASE_URL}/api/documents/{doc_id}/view", headers=HEADERS)
        print_response("👁️ 增加查看次数", response)
        
        # 7. 获取文档统计
        response = requests.get(f"{BASE_URL}/api/documents/{doc_id}/stats", headers=HEADERS)
        print_response("📊 获取文档统计", response)
    
    return doc_id


def demo_batch_operations():
    """演示批量操作功能"""
    print("\n" + "⚡ AI写作工具 - 批量操作演示".center(60))
    
    # 获取文档列表
    response = requests.get(f"{BASE_URL}/api/documents", headers=HEADERS)
    if response.status_code == 200:
        documents = response.json()["data"]["documents"]
        if documents:
            doc_ids = [doc["id"] for doc in documents[:2]]  # 取前两个文档
            
            # 批量更新状态
            data = {
                "action": "updateStatus",
                "documentIds": doc_ids,
                "data": {"status": 1}  # 改为草稿状态
            }
            response = requests.post(f"{BASE_URL}/api/documents/batch", headers=HEADERS, json=data)
            print_response("⚡ 批量更新文档状态", response)
    
    # 获取更新后的文档列表
    response = requests.get(f"{BASE_URL}/api/documents", headers=HEADERS)
    print_response("📝 批量操作后的文档列表", response)


def main():
    """主演示函数"""
    print("🎯 AI写作工具后端API完整演示")
    print("=" * 60)
    
    # 检查服务状态
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code != 200:
        print("❌ 服务未启动，请先运行: python main.py")
        return
    
    print("✅ 服务运行正常，开始演示...")
    time.sleep(1)
    
    # 演示知识库管理
    project_folder_id = demo_knowledge_base()
    
    # 演示文档管理
    doc_id = demo_document_management(project_folder_id)
    
    # 演示批量操作
    demo_batch_operations()
    
    # 最终展示
    print("\n" + "🎉 演示完成！".center(60))
    print("=" * 60)
    print("📋 已实现的功能:")
    print("  ✅ 知识库树形结构管理")
    print("  ✅ 文件夹CRUD操作")
    print("  ✅ 文档CRUD操作")
    print("  ✅ 自动保存功能")
    print("  ✅ 全文搜索和筛选")
    print("  ✅ 批量操作")
    print("  ✅ 统计功能")
    print("  ✅ 权限控制")
    print("\n🌐 访问API文档: http://localhost:8000/docs")
    print("📖 查看ReDoc文档: http://localhost:8000/redoc")


if __name__ == "__main__":
    main()
