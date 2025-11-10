# 写作智能体使用说明

## 1. 依赖安装
```
pip install -r requirements.txt
```
新的依赖包括 `langchain`、`langchain-community`、`duckduckgo-search` 等，请确保安装完成后再启动服务。

## 2. 必要配置
- 在系统中为当前用户配置 `UserLLMConfig`（API Key、模型、Base URL）。
- `.env` 中保持数据库、OpenAI 等配置正确。

## 3. 启动服务
```
./bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 4. REST API
### 4.1 启动智能体
```
POST /api/agent/writer/execute
Content-Type: application/json
Authorization: Bearer <token>

{
  "userPrompt": "撰写一篇500字的科技新闻稿",
  "documentId": 123,
  "sessionId": "c0e9d404-...",           // 可选，复用会话
  "selectedSnippets": [
    {
      "documentId": 123,
      "content": "选中的背景段落",
      "source": "manual_selection"
    }
  ],
  "selectedDocumentIds": [123, 456]
}

响应示例：
{
  "sessionId": "c0e9d404-...",
  "status": "accepted",
  "message": "Agent execution started"
}

> 说明：无需传入补充需求，智能体的意图理解模块会根据用户输入及选中片段自动生成写作要点和建议。响应中的 `sessionId` 用于后续订阅 WebSocket，实时获取任务状态与文档更新。

### 4.2 订阅事件
```
WebSocket ws://host/api/agent/ws/{sessionId}
```
事件示例：
```json
{"type":"agent_status","data":{"stage":"running"}}
{"type":"document_update","data":{"documentId":123,"mode":"replace","summary":"改写引言","content":"..."}}
{"type":"agent_complete","data":{"result":{"output":"写作完成..."}}}
```

### 4.3 查看任务清单
```
GET /api/agent/tasks
Authorization: Bearer <token>
```
返回用户的所有智能体任务记录，便于在前端展示进度。

## 5. 工具说明
- **document_editor**：根据 agent 输出完成文档改写，支持 replace/append/prepend，并自动推送事件给前端。
- **document_reader**：读取原文档数据，便于总结分析。
- **document_knowledge_search**：使用向量检索查找文档片段。
- **web_research_tool**：调用 DuckDuckGo 搜索最新公开资料。
- **task_create/task_update**：持久化任务清单，便于进度管理。

## 6. 前端交互建议
1. 调用 `/api/agent/writer/execute` 获取 `sessionId`。
2. 打开 WebSocket `ws://.../api/agent/ws/{sessionId}` 监听过程中产生的事件，实时更新页面。
3. 监听WebSocket `/api/agent/ws/{sessionId}`，获取实时事件（状态、意图总结、文档更新、任务进度等）。
4. 会话结束收到 `session_closed` 后关闭连接；复用会话时再次按需连接。

> 智能体的任务清单和状态会通过 WebSocket 事件推送给前端，无需额外 REST 接口。

## 7. 错误排查
- 若接口返回 400，检查验证码或 LLM 配置是否正确。
- 若 WebSocket 无事件，确认 sessionId 是否正确以及服务是否运行。
- 若工具返回 `Error retrieving knowledge`，检查用户是否配置了 Embedding API Key。
