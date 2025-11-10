# 基于 LangChain / LangGraph 的 AI 写作智能体技术方案

## 1. 背景与目标
- **现状**：项目已具备文档管理、知识库、AI 写作/对话等 API，主要以 FastAPI + PostgreSQL + LangChain（部分模块）实现。
- **目标**：引入 LangChain / LangGraph 架构，构建可扩展、可插拔的智能体（Agent）工作流，实现写作辅助、任务管理、风格记忆等高级功能。
- **设计原则**：模块化、可观测、可扩展、与现有接口兼容。

## 2. 总体架构
```
┌─────────────────────────────┐
│        Web / 前端 (Vue)       │
└──────────────┬──────────────┘
               │ REST / WebSocket
┌──────────────▼──────────────┐
│        FastAPI 后端           │
│  - 现有业务 API               │
│  - 智能体 API (新增)          │
├─────────────────────────────┤
│ LangGraph Agent Engine      │
│  - 工作流编排                │
│  - 状态管理 / 记忆存储        │
│  - 节点：规划、执行、检查      │
├─────────────────────────────┤
│ LangChain 模块               │
│  - LLM 接口 (OpenAI/自建)     │
│  - 工具调用封装 (搜索/写作等) │
│  - Prompt / Chain 配置        │
├─────────────────────────────┤
│ 数据层                       │
│  - PostgreSQL (用户/文档/记忆) │
│  - 向量库 (pgvector)          │
│  - Redis (可选: 事件队列/缓存) │
└─────────────────────────────┘
```

## 3. 模块设计

### 3.1 智能体能力划分
根据图片草图与现状，拆分为以下能力节点：
| 节点 | 职责 | 对应 LangGraph 功能 |
|------|------|----------------------|
| 意图识别 Intent Parser | 分析用户需求、复杂度评估 | 输入处理节点（LLM + 模板）|
| 规划 Planner | 生成任务列表、选择工具 | LangGraph 节点调用 LangChain Agent |
| 定制化工作流 | 复杂任务定制路线 | LangGraph 中的条件分支 / 子图 |
| 执行 Executor | 调用子工具（改写、检索、创作） | LangChain 工具 + 调度器 |
| 收集信息 Gatherer | 知识库检索、网络搜索 | Retrieval QA Chain、SerpAPI 工具 |
| 实施改动 Modifier | 对文档进行增删改 | 文档编辑工具（数据库操作）|
| 检查优化 Checker | 评审输出、风格一致性 | 质量评估链（LLM Critic）|
| 记忆 Memory | 用户写作风格、任务进度 | LangChain Memory + PostgreSQL |

### 3.2 LangGraph 工作流
- 使用 LangGraph 定义智能体状态机，核心节点：
  1. **InputNode**：接收用户指令、上下文（文档 ID、目标写作类型）。
  2. **IntentNode**：调用 LLM + prompt 识别任务类型、复杂度 -> 输出 {任务类型, 推荐工具, 是否需要规划}。
  3. **PlannerNode**：若需规划，调用 `ConversationAgentExecutor` 制定任务列表（保存到 Postgres `agent_tasks` 表）。
  4. **ExecutorNode**：遍历任务，调用具体工具（LangChain Tools）。
  5. **ReviewerNode**：调用 LLM 对结果进行自检，若不满意则触发 `Refine` 子流程。
  6. **MemoryNode**：更新用户风格、任务历史。
  7. **OutputNode**：整合结果，通过 API 返回。

- LangGraph 提供并行/条件分支：
  - 当任务复杂度高时，调用自定义工作流子图（如“长文规划 + 多轮写作”）。
  - 对临时任务保持轻量模式（跳过规划直接执行）。

### 3.3 LangChain 工具 & Chains
| 工具/Chain | 作用 | 实现说明 |
|-----------|------|----------|
| `DocumentEditTool` | 对指定段落改写/插入 | 调用现有文档 API（/api/documents） + LLM 改写 |
| `KnowledgeSearchTool` | 检索知识库内容 | 复用 pgvector 检索 + LangChain RetrievalQA |
| `WebSearchTool` | 网络检索 | 使用 SerpAPI 或自建搜索接口 |
| `StyleMemoryTool` | 读取/写入风格记忆 | Postgres 存储 + LangChain Memory 接口 |
| `TaskTrackerTool` | 任务清单、状态同步 | 新增 `agent_tasks` 表 + CRUD |
| `CriticChain` | 结果检查、优化建议 | Prompt 模板 + LLM 调用 |
| `RewriteChain` | 指定段落局部改写 | Retrieval + Prompt + Temperature 设置 |

### 3.4 数据库扩展
- 新增数据表：
  ```sql
  CREATE TABLE public.agent_tasks (
      id BIGSERIAL PRIMARY KEY,
      user_id BIGINT NOT NULL,
      session_id VARCHAR(64),
      task_description TEXT,
      status VARCHAR(20) DEFAULT 'pending',
      priority INT DEFAULT 0,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ DEFAULT NOW()
  );

  CREATE TABLE public.writer_memory (
      id BIGSERIAL PRIMARY KEY,
      user_id BIGINT NOT NULL,
      key VARCHAR(100) NOT NULL,
      value JSONB,
      expire_at TIMESTAMPTZ,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      updated_at TIMESTAMPTZ DEFAULT NOW()
  );
  ```
- `writer_memory` 用于存储用户写作风格、偏好，LangChain Memory 层读取/写入。
- `agent_tasks` 维护任务执行状态，便于前端展示进度。

### 3.5 配置与部署
- 新增配置项（`.env`）：
  ```env
  LLM_PROVIDER=openai
  OPENAI_API_KEY=xxx
  LANGCHAIN_TRACING_V2=true
  LANGCHAIN_ENDPOINT=https://api.langchain.plus
  SERPAPI_API_KEY=xxx  # 如需网络搜索
  ```
- 引入依赖：
  ```bash
  pip install langchain langgraph langchain-openai langchain-community langchain-experimental
  pip install typer rich  # CLI 与调试
  ```
- 结构调整：
  ```
  app/
    agents/
      __init__.py
      writer_agent.py        # LangGraph 定义
      tools/
        __init__.py
        document_tools.py
        knowledge_tools.py
        web_tools.py
      prompts/
        intent_prompt.yaml
        planner_prompt.yaml
        reviewer_prompt.yaml
      memory/
        writer_memory.py
    api/
      agent.py               # 新增 REST/WebSocket 接口
  ```

## 4. API 设计
- **POST /api/agent/writer/plan**：创建写作任务，返回任务清单。
- **POST /api/agent/writer/execute**：输入任务 ID / 指令，触发 LangGraph 执行；支持 WebSocket 推送进度。
- **GET /api/agent/tasks**：查询任务状态。
- **WS /ws/agent/{session_id}**：实时返回阶段性结果（计划、执行、优化结果）。

请求示例：
```json
POST /api/agent/writer/execute
{
  "userId": 1,
  "documentId": 123,
  "goal": "写一篇科技新闻稿",
  "requirements": {
    "length": "800-1000字",
    "tone": "正式",
    "points": ["新品发布", "市场反馈"]
  }
}
```
响应（简化）：
```json
{
  "sessionId": "sess_20251108",
  "status": "running",
  "tasks": [
    {"id": 1, "description": "收集背景信息", "status": "in_progress"},
    {"id": 2, "description": "撰写初稿", "status": "pending"}
  ]
}
```
WebSocket 推送：
```json
{
  "taskId": 1,
  "event": "partial_result",
  "content": "收集到以下背景信息..."
}
```

## 5. 工作流细节

### 5.1 意图识别
- Prompt 包含：用户指令、当前文档类型、历史任务。
- 输出 JSON：`{"intent": "rewrite", "complexity": "medium", "requires_plan": true}`。
- 决策逻辑：
  - 简单改写 → 直接调用 `RewriteChain`。
  - 新创作/多段写作 → 进入规划节点。

### 5.2 规划节点
- 使用 `StructuredPlanner`（LangChain）生成任务列表。
- 持久化到 `agent_tasks`。
- 返回任务摘要给前端。

### 5.3 执行节点
- 遍历任务：
  - `gather_info` → 调用知识库/网络搜索工具。
  - `draft` → 使用 `LangChain` 的 `LLMChain` + 文档上下文生成文稿。
  - `edit` → 读取文档片段，调用改写工具。
- 支持任务依赖：LangGraph 通过 `state` 存储中间结果。

### 5.4 检查优化
- 由 `ReviewerNode` 执行：
  - Prompt 约束：检查事实错误、风格一致性、段落结构。
  - 若不满足标准，写入任务队列 `Refine`，继续循环（最多 N 次）。

### 5.5 记忆更新
- 写作完成后，将本次任务总结、风格偏好写入 `writer_memory`。
- Memory 模块为下次写作提供默认参数（如常用语气、常见提纲）。

## 6. 前端改造建议
- 登录后，进入“智能体模式”面板：展示任务清单、当前进度。
- 支持用户在执行过程中插入反馈（WebSocket/REST）。
- 在文档编辑器中实时更新结果。
- 提供“风格设置”管理界面，调用 Memory API。

## 7. 运维与监控
- 开启 LangChain Tracing（LCEL），通过 LangSmith 或 LangFuse 记录 LLM 调用。
- 在 FastAPI 中加入日志中间件，记录每次 Agent 调用、耗时、错误。
- 关键指标：任务成功率、平均响应时间、LLM 费用、用户满意度。

## 8. 开发计划（建议）
1. **第一阶段**：
   - 整合 LangChain/LangGraph，完成基础工作流（意图识别 → 执行 → 输出）。
   - 实现核心工具：文档改写、知识库检索。
   - 提供 REST API + 简单进度查询。
2. **第二阶段**：
   - 引入任务规划器、任务存储。
   - 集成 WebSocket，实时输出。
   - 实现 Memory（风格记忆、任务历史）。
3. **第三阶段**：
   - 引入高级工具（网络检索、风格迁移）。
   - 完善质量评估、异常恢复机制。
   - 结合前端实现可视化流程与任务管理。

## 9. 风险与对策
| 风险 | 影响 | 应对策略 |
|------|------|----------|
| LLM 成本过高 | 运营费用增加 | 控制调用次数、缓存中间结果、使用小模型优先 |
| LangGraph 学习曲线 | 开发进度延迟 | 先从简版图开始，逐步扩展；编写单元测试 |
| 工具调用失败 | 影响用户体验 | 实现重试机制、错误兜底回复 |
| 数据安全 | 用户文档泄露风险 | 加强权限校验、所有输出记录审计 |
| 状态一致性 | 多任务同时执行冲突 | 设计会话 ID、任务锁机制，必要时使用队列 |

## 10. 结论
通过引入 LangChain 和 LangGraph，可以把 AI 写作能力组织成可解释、可扩展的智能体工作流，实现从意图识别、任务规划、工具调用到结果审核的全流程自动化，配合集成的记忆与任务跟踪，为企业级写作工具提供更强大的智能体验。
