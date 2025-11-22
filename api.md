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

#### 5.1 调用写作智能体（统一段落编辑模式）
```
POST /api/agent/writer/execute
Authorization: Bearer {token}
Content-Type: application/json

Request Body:
{
  "userPrompt": "撰写一篇500字的科技新闻稿",
  "documentId": 123,                // 可选，待编辑的文档ID
  "sessionId": "c0e9d404-...",     // 可选，复用会话记忆
  "selectedDocumentIds": [123, 456], // 可选，相关文档ID列表
  "targetSelection": {               // 可选，用户在编辑器中的选中文本信息
    "text": "用户选中的文本内容",
    "startOffset": 100,             // 选中文本在文档中的起始位置
    "endOffset": 500                // 选中文本在文档中的结束位置
  }
}

Response:
{
  "sessionId": "c0e9d404-...",
  "status": "accepted",
  "message": "Agent execution started"
}
```

说明:
- 统一使用段落级别编辑模式，所有文档操作都通过段落编辑指令实现
- `sessionId` 可选；复用旧session可保持上下文记忆；响应中返回的 `sessionId` 即后续订阅 WebSocket 的连接参数
- **工作流程**：
  - 如果提供了 `documentId`，智能体会自动读取完整文档内容
  - 根据用户意图（`userPrompt`）和选中文本（`targetSelection`），智能分析文档结构
  - 自主识别需要修改的段落范围（可能是选中段落，也可能扩展到上下文段落）
  - 逐段生成编辑指令推送到前端，**不直接修改数据库**
  - 前端接收指令后在本地预览，用户确认后通过 `PUT /api/documents/{id}` 保存最终结果
- **无文档场景**：
  - 如果没有 `documentId`，智能体可以使用知识检索工具获取信息，创建新内容
  - 或根据 `selectedSnippets` 中的参考内容进行写作
  - 如果提供了 `selectedDocumentIds`，知识检索工具会优先在这些文档中搜索
- 详细过程（任务状态、编辑指令、意图总结等）会以 WebSocket 事件推送，无需额外 REST 查询
- 若用户未配置 LLM API Key，会返回 400/500 错误

#### 5.2 订阅智能体事件（WebSocket）
```
GET ws://{host}/api/agent/ws/{sessionId}
```

事件类型说明:

**1. agent_status - 智能体状态变更**
```json
{
  "type": "agent_status",
  "data": {
    "stage": "initializing|intent_analysis|running|complete|error"
  }
}
```

**2. intent_summary - 意图分析结果**
```json
{
  "type": "intent_summary",
  "data": {
    "intent": "段落改写",
    "summary": "用户希望将第2、3段改写为更专业的语气",
    "keyPoints": ["专业语气", "保持原意"],
    "suggestedActions": ["分析目标段落", "逐段改写"],
    "toneStyle": "professional"
  }
}
```

**3. paragraph_edit_instruction - 段落编辑指令 🆕**
```json
{
  "type": "paragraph_edit_instruction",
  "data": {
    "paragraphId": "p_abc123",              // 智能体自动生成的段落ID
    "operation": "replace|delete|insert_before|insert_after",
    "newContent": "改写后的段落内容...",
    "originalContent": "原始段落内容...",    // 原始内容，方便前端对比
    "reasoning": "调整为更专业的技术描述，增强逻辑性",
    "metadata": {
      "startOffset": 100,                   // 段落在文档中的起始位置
      "endOffset": 250,                     // 段落在文档中的结束位置
      "originalLength": 150,
      "newLength": 180,
      "confidence": 0.95
    },
    "timestamp": "2024-01-01T10:30:00Z",
    "progress": {
      "current": 1,
      "total": 3
    }
  }
}
```

**4. agent_complete - 任务完成**
```json
{
  "type": "agent_complete",
  "data": {
    "result": {
      "output": "已完成3个段落的编辑指令生成",
      "affectedParagraphs": ["p_abc123", "p_def456", "p_ghi789"],
      "totalInstructions": 3,
      "summary": "根据用户需求分析了文档结构，识别出3个需要修改的段落"
    }
  }
}
```

**5. agent_error - 错误事件**
```json
{
  "type": "agent_error",
  "data": {
    "message": "段落ID不存在: p_xyz",
    "code": "PARAGRAPH_NOT_FOUND"
  }
}
```

**6. task_created - 任务创建 🆕**
```json
{
  "type": "task_created",
  "data": {
    "id": 1,
    "sessionId": "c0e9d404-...",
    "description": "分析文档结构",
    "status": "pending",
    "priority": 1,
    "createdAt": "2024-01-01T00:00:00Z"
  }
}
```

**7. task_updated - 任务状态更新 🆕**
```json
{
  "type": "task_updated",
  "data": {
    "id": 1,
    "sessionId": "c0e9d404-...",
    "description": "分析文档结构",
    "status": "in_progress",
    "old_status": "pending",
    "priority": 1,
    "updatedAt": "2024-01-01T00:01:00Z"
  }
}
```

**8. knowledge_search_start - 知识搜索开始 🆕**
```json
{
  "type": "knowledge_search_start",
  "data": {
    "query": "人工智能发展历史",
    "top_k": 3,
    "selected_document_ids": [123, 456],
    "search_type": "document"
  }
}
```

**9. knowledge_search_result - 知识搜索结果 🆕**
```json
{
  "type": "knowledge_search_result",
  "data": {
    "query": "人工智能发展历史",
    "success": true,
    "results_count": 3,
    "search_type": "document",
    "selected_document_ids": [123, 456]
  }
}
```

搜索失败时：
```json
{
  "type": "knowledge_search_result",
  "data": {
    "query": "人工智能发展历史",
    "success": false,
    "error": "No relevant content found",
    "search_type": "document"
  }
}
```

**10. session_closed - 会话关闭**
```json
{
  "type": "session_closed",
  "data": {}
}
```

说明:
- 建议在发送写作请求后按需建立 WebSocket 连接；任务结束收到 `session_closed` 后可主动断开，下次继续使用同 `sessionId` 时再连接。
- **段落编辑模式工作流程**：
  1. 前端发送请求时指定 `editMode: "paragraph"` 和 `documentId`
  2. 智能体自动读取文档内容，分析文档结构（按换行符、段落语义等切分）
  3. 根据用户意图和选中文本，智能识别需要修改的段落范围
  4. 逐段落生成编辑指令，每完成一个立即发送 `paragraph_edit_instruction` 事件
  5. 前端接收事件后在UI上实时预览修改效果（**仅本地状态，不保存到服务器**）
  6. 用户确认后，前端合并所有修改，调用 `PUT /api/documents/{id}` 保存完整文档内容
- **段落定位机制**：
  - 智能体会为每个识别出的段落生成唯一ID（如 `p_1`, `p_2`）
  - 同时提供段落的起止位置（`startOffset`, `endOffset`），方便前端精确定位
  - 如果用户提供了 `targetSelection`，优先以选中范围为中心进行分析
- 智能体会通过事件推送任务列表、状态变更、意图总结、知识搜索结果等信息，无需额外 REST 查询。
- **工具功能说明**：
  - **文档分析工具** (`document_analyzer`): 分析文档结构，返回段落列表和位置信息
  - **段落编辑工具** (`paragraph_editor`): 生成段落级别的编辑指令，实时推送到前端
  - **文档知识搜索** (`document_knowledge_search`): 从用户文档库中检索相关内容，支持指定文档ID重点搜索
  - **网络搜索** (`web_research_tool`): 使用DuckDuckGo搜索互联网公开资料
  - **任务管理工具** (`task_create`, `task_update`, `task_list`): 创建、更新和查询任务，用于跟踪智能体执行进度