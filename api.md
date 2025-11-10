### 1. 认证接口

#### 1.1 微信登录验证码验证
```
POST /api/auth/wechat/verify
Content-Type: application/json

Request Body:
{
  "code": "123456"  // 6位验证码
}

Response (成功):
{
  "code": 200,
  "message": "登录成功",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "id": 1,
      "username": null,
      "email": null,
      "phone": null,
      "avatar_url": null,
      "wechat_openid": "oXXXXXXXXXXXXX",
      "created_at": "2024-01-01T00:00:00"
    }
  }
}

Error Response (验证码无效或已过期):
HTTP 400
{
  "detail": "验证码无效或已过期"
}

说明:
- 用户在公众号内发送"666"后，会收到验证码
- 验证码有效期为1分钟
- 验证成功后会返回JWT token，用于后续API调用
- 如果用户不存在，系统会自动创建新用户
```

### 2. 知识库管理接口

#### 2.1 获取知识库结构
```
GET /api/knowledge-base
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": [
    {
      "id": "folder_id",
      "name": "工作文档",
      "type": "folder",
      "parentId": null,
      "ownerId": "user_id",
      "children": [
        {
          "id": "sub_folder_id",
          "name": "项目资料",
          "type": "folder",
          "parentId": "folder_id",
          "ownerId": "user_id",
          "children": [
            {
              "id": "doc_id",
              "name": "需求文档",
              "type": "document",
              "folderId": "sub_folder_id",
              "authorId": "user_id",
              "lastModified": "2024-01-01T00:00:00Z"
            }
          ],
          "createdAt": "2024-01-01T00:00:00Z",
          "updatedAt": "2024-01-01T00:00:00Z"
        }
      ],
      "createdAt": "2024-01-01T00:00:00Z",
      "updatedAt": "2024-01-01T00:00:00Z"
    }
  ]
}
```

#### 2.2 创建文件夹
```
POST /api/folders
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "name": "string",
  "parentId": "parent_folder_id" // 可选，为null表示根目录
}

Response:
{
  "code": 200,
  "message": "文件夹创建成功",
  "data": {
    "id": "new_folder_id",
    "name": "folder_name",
    "parentId": "parent_id",
    "ownerId": "user_id",
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

#### 2.3 重命名文件夹
```
PUT /api/folders/{id}/rename
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "name": "new_name"
}

Response:
{
  "code": 200,
  "message": "重命名成功",
  "data": {
    "id": "folder_id",
    "name": "new_name",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

#### 2.4 删除文件夹
```
DELETE /api/folders/{id}
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "删除成功"
}
```

#### 2.5 移动文件夹
```
PUT /api/folders/{id}/move
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "parentId": "new_parent_id" // 为null表示移动到根目录
}

Response:
{
  "code": 200,
  "message": "移动成功",
  "data": {
    "id": "folder_id",
    "parentId": "new_parent_id",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

### 3. 文档管理接口

#### 3.1 创建文档
```
POST /api/documents
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "title": "string",
  "content": "string",
  "folderId": "folder_id", // 可选，对应 folders.id
  "categoryId": "category_id", // 可选，对应 categories.id
  "tags": ["tag1", "tag2"], // 可选，标签数组
  "isPublic": false, // 可选，是否公开，默认false
  "status": 1, // 可选，文档状态：1=草稿，2=发布，3=归档，默认1
  "excerpt": "string" // 可选，文档摘要
}

Response:
{
  "code": 200,
  "message": "文档创建成功",
  "data": {
    "id": "doc_id",
    "title": "document_title",
    "content": "document_content",
    "authorId": "author_id",
    "folderId": "folder_id",
    "categoryId": "category_id",
    "isPublic": false,
    "status": 1,
    "tags": ["tag1", "tag2"],
    "excerpt": "document_excerpt",
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
    "stats": {
      "viewCount": 0,
      "likeCount": 0,
      "shareCount": 0,
      "commentCount": 0
    }
  }
}
```

#### 3.2 获取文档详情
```
GET /api/documents/{id}
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "id": "doc_id",
    "title": "document_title",
    "content": "document_content",
    "authorId": "author_id",
    "author": {
      "id": "author_id",
      "username": "author_name",
      "avatar": "avatar_url"
    },
    "folderId": "folder_id",
    "folder": {
      "id": "folder_id",
      "name": "folder_name",
      "path": "folder/path"
    },
    "categoryId": "category_id",
    "category": {
      "id": "category_id",
      "name": "category_name",
      "slug": "category_slug"
    },
    "isPublic": false,
    "status": 1,
    "tags": ["tag1", "tag2"],
    "excerpt": "document_excerpt",
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
    "stats": {
      "viewCount": 100,
      "likeCount": 10,
      "shareCount": 5,
      "commentCount": 3
    }
  }
}
```

#### 3.3 更新文档
```
PUT /api/documents/{id}
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "title": "string",
  "content": "string",
  "folderId": "folder_id", // 可选
  "categoryId": "category_id", // 可选
  "tags": ["tag1", "tag2"], // 可选
  "isPublic": false, // 可选
  "status": 2, // 可选
  "excerpt": "string" // 可选
}

Response:
{
  "code": 200,
  "message": "更新成功",
  "data": {
    "id": "doc_id",
    "title": "updated_title",
    "content": "updated_content",
    "folderId": "folder_id",
    "categoryId": "category_id",
    "tags": ["tag1", "tag2"],
    "isPublic": false,
    "status": 2,
    "excerpt": "updated_excerpt",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

#### 3.4 自动保存文档
```
POST /api/documents/{id}/autosave
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "content": "string",
  "excerpt": "string" // 可选，自动生成的摘要
}

Response:
{
  "code": 200,
  "message": "自动保存成功",
  "data": {
    "id": "doc_id",
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

#### 3.5 删除文档
```
DELETE /api/documents/{id}
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "message": "删除成功"
}
```

#### 3.6 获取文档列表
```
GET /api/documents
Authorization: Bearer {token}
Query Parameters:
  page: 1,
  limit: 20,
  folderId: "folder_id", // 可选，按文件夹筛选
  categoryId: "category_id", // 可选，按分类筛选
  status: 1, // 可选，按状态筛选
  isPublic: false, // 可选，按公开状态筛选
  tags: "tag1,tag2", // 可选，按标签筛选
  sort: "createdAt|updatedAt|title", // 可选，排序字段
  order: "desc|asc", // 可选，排序方向
  search: "keyword" // 可选，搜索关键词

Response:
{
  "code": 200,
  "data": {
    "documents": [
      {
        "id": "doc_id",
        "title": "document_title",
        "content": "preview_content",
        "excerpt": "document_excerpt",
        "authorId": "author_id",
        "folderId": "folder_id",
        "categoryId": "category_id",
        "isPublic": false,
        "status": 1,
        "tags": ["tag1", "tag2"],
        "createdAt": "2024-01-01T00:00:00Z",
        "updatedAt": "2024-01-01T00:00:00Z",
        "stats": {
          "viewCount": 10,
          "likeCount": 1,
          "shareCount": 0,
          "commentCount": 0
        }
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 100,
      "totalPages": 5
    }
  }
}
```

#### 3.7 批量操作文档
```
POST /api/documents/batch
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "action": "delete|move|updateStatus|updateCategory",
  "documentIds": ["doc_id1", "doc_id2"],
  "data": {
    // 根据action类型提供相应数据
    // move: { folderId: "new_folder_id" }
    // updateStatus: { status: 2 }
    // updateCategory: { categoryId: "category_id" }
  }
}

Response:
{
  "code": 200,
  "message": "批量操作成功",
  "data": {
    "successCount": 2,
    "failedCount": 0,
    "results": [
      {
        "id": "doc_id1",
        "success": true,
        "message": "操作成功"
      }
    ]
  }
}
```

#### 3.8 文档统计信息
```
GET /api/documents/{id}/stats
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "documentId": "doc_id",
    "viewCount": 100,
    "likeCount": 10,
    "shareCount": 5,
    "commentCount": 3,
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

#### 3.9 增加文档查看次数
```
POST /api/documents/{id}/view
Authorization: Bearer {token}

Response:
{
  "code": 200,
  "data": {
    "documentId": "doc_id",
    "viewCount": 101,
    "updatedAt": "2024-01-01T00:00:00Z"
  }
}
```

### 4. AI功能接口

#### 4.1 AI帮写流式生成
```
POST /api/ai-help/stream
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "userId": "当前用户ID",
  "prompt": "用户输入的提示内容",
  "documentId": "当前文档ID（可选）",
  "context": "当前文档内容上下文（可选）"
}

Response: Server-Sent Events (SSE)
data: {"content": "AI生成的内容片段..."}
data: {"content": "继续生成的内容..."}
data: {"done": true, "usage": {"tokens": 150, "cost": 0.02}}

Error Response (SSE):
data: {"error": {"code": "RATE_LIMIT_EXCEEDED", "message": "请求频率过高"}}
```

#### 4.2 局部段落AI处理流式接口
```
POST /api/ai-text/process/stream
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "userId": "当前用户ID",
  "action": "expand|continue|abbreviate|correct|summarize|translate|format|custom",
  "originalText": "原始文本内容",
  "documentId": "当前文档ID（可选）",
  "context": "周围文本上下文（可选）",
  "userPrompt": "用户个性化需求提示词（可选）",
  "options": {
    "targetLanguage": "en",           // translate专用：目标语言代码
    "sourceLanguage": "zh",           // translate专用：源语言代码
    "summaryLength": "short|medium|long", // summarize专用：摘要长度
    "expandType": "detailed|brief",   // expand专用：扩写类型
    "targetLength": 200,             // abbreviate专用：目标长度
    "correctionType": "grammar|spelling|style" // correct专用：纠错类型
  }
}

Response: Server-Sent Events (SSE)
data: {"content": "AI处理后的内容片段..."}
data: {"content": "继续处理的内容..."}
data: {"done": true, "usage": {"tokens": 150, "cost": 0.02}}

Error Response (SSE):
data: {"error": {"code": "INVALID_ACTION", "message": "无效的action类型"}}
```

#### 4.3 AI问答对话流式接口
```
POST /api/ai-chat/stream
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "userId": "当前用户ID",
  "question": "用户输入的问题",
  "conversationId": "会话ID（可选）", // 用于多轮对话上下文
  "documentId": "当前文档ID（可选）", // 可选，指定在特定文档内搜索
  "searchScope": "all|current", // 可选，搜索范围：all=所有文档，current=当前文档，默认all
  "ragEnabled": true, // 可选，是否启用RAG检索，默认true
  "selectedDocumentIds": ["doc_id1", "doc_id2"], // 可选，用户手动添加到对话框的文档ID列表
  "selectedReferences": [ // 可选，用户手动添加的选中文本引用列表
    {
      "text": "选中的文本内容",
      "documentId": "doc_id", // 可选，来源文档ID
      "source": "editor_selection|document_content|clipboard" // 可选，来源类型
    }
  ]
}

Response: Server-Sent Events (SSE)
data: {"content": "AI回答的内容片段..."}
data: {"content": "继续回答的内容..."}
data: {"done": true, "usage": {"tokens": 200, "cost": 0.03}, "conversationId": "会话ID"}

Error Response (SSE):
data: {"error": {"code": "NO_RELEVANT_DOCUMENTS", "message": "未找到相关文档"}}
```

### 5. 智能体接口

#### 5.1 调用写作智能体
```
POST /api/agent/writer/execute
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "userPrompt": "撰写一篇500字的科技新闻稿",
  "documentId": 123,
  "sessionId": "c0e9d404-...",   // 可选，复用会话记忆
  "selectedSnippets": [
    {
      "documentId": 123,
      "content": "上一段用户选中的背景介绍",
      "source": "manual_selection"
    }
  ],
  "selectedDocumentIds": [123, 456]
}

Response:
{
  "sessionId": "c0e9d404-...",
  "status": "accepted",
  "message": "Agent execution started"
}
```

说明:
- 不需要在请求体中传补充需求；智能体会通过意图理解模块自动推断写作要点、语气等信息。
- `sessionId` 可选；复用旧session可保持上下文记忆；响应中返回的 `sessionId` 即后续订阅 WebSocket 的连接参数。
- 详细过程（任务状态、文档更新、意图总结等）会以 WebSocket 事件推送，无需额外 REST 查询。
- 若用户未配置 LLM API Key，会返回 400/500 错误。

#### 5.2 订阅智能体事件（WebSocket）
```
GET ws://{host}/api/agent/ws/{sessionId}
```
事件示例：
```json
{"type":"agent_status","data":{"stage":"initializing"}}
{"type":"document_update","data":{"documentId":123,"mode":"replace","summary":"改写引言","content":"..."}}
{"type":"agent_complete","data":{"result":{"output":"写作完成..."}}}
```

说明:
- 建议在发送写作请求后按需建立 WebSocket 连接；任务结束收到 `session_closed` 后可主动断开，下次继续使用同 `sessionId` 时再连接。
- 智能体会通过事件推送任务列表、状态变更、意图总结等信息，无需额外 REST 查询。