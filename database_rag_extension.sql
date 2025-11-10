-- ================================================================
-- RAG向量数据库扩展（基于现有表结构）
-- MVP版本 - 极简设计：每个用户的所有文档就是他的知识库
-- ================================================================

-- 1. 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- ================================================================
-- 文档向量化相关表（核心表）
-- ================================================================

-- 文档分块表（存储文档切分后的chunks和向量）
CREATE TABLE public.document_chunks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL,                    -- 关联到现有documents表
    content TEXT NOT NULL,                          -- 分块内容
    embedding vector(1024),                         -- 向量（qwen3-embedding-0.6b: 1024维）
    chunk_index INT NOT NULL,                       -- 分块序号
    token_count INT,                                -- token数量
    metadata JSONB DEFAULT '{}',                    -- 扩展元数据
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_document FOREIGN KEY (document_id) 
        REFERENCES public.documents(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_chunks_document ON public.document_chunks(document_id);
CREATE INDEX idx_chunks_created ON public.document_chunks(created_at);

-- 向量相似度索引（IVFFlat，适合中等规模）
CREATE INDEX idx_chunks_embedding ON public.document_chunks 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

COMMENT ON TABLE public.document_chunks IS '文档分块及向量存储 - 每个用户的所有文档向量即为其知识库';

-- ================================================================
-- Agent智能体相关表
-- ================================================================

-- Agent会话表（支持多智能体对话）
CREATE TABLE public.agent_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,        -- 会话唯一标识
    user_id BIGINT NOT NULL,
    agent_type VARCHAR(50) NOT NULL,                -- 智能体类型：writing/research/qa/custom
    title VARCHAR(255),                             -- 会话标题
    
    status VARCHAR(20) DEFAULT 'active',            -- active/completed/archived
    
    -- 配置信息
    config JSONB DEFAULT '{}',                      -- Agent配置
    metadata JSONB DEFAULT '{}',                    -- 扩展元数据
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_agent_user FOREIGN KEY (user_id) 
        REFERENCES public.user(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_agent_session ON public.agent_sessions(session_id);
CREATE INDEX idx_agent_user ON public.agent_sessions(user_id);
CREATE INDEX idx_agent_type ON public.agent_sessions(agent_type);
CREATE INDEX idx_agent_status ON public.agent_sessions(status);

COMMENT ON TABLE public.agent_sessions IS 'Agent智能体会话';

-- Agent消息历史表
CREATE TABLE public.agent_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,                      -- user/assistant/system/tool
    content TEXT NOT NULL,
    
    -- 工具调用信息
    tool_calls JSONB,                               -- 工具调用记录
    tool_results JSONB,                             -- 工具返回结果
    
    -- 引用信息（RAG场景）
    references JSONB,                               -- 引用的文档chunks
    
    -- 扩展信息
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_agent_session FOREIGN KEY (session_id) 
        REFERENCES public.agent_sessions(session_id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_agent_msg_session ON public.agent_messages(session_id);
CREATE INDEX idx_agent_msg_role ON public.agent_messages(role);
CREATE INDEX idx_agent_msg_created ON public.agent_messages(created_at);

COMMENT ON TABLE public.agent_messages IS 'Agent消息历史';

-- ================================================================
-- 文档处理任务表（异步任务管理）
-- ================================================================

-- 文档向量化任务表（异步任务管理）
CREATE TABLE public.document_vectorization_tasks (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL,
    
    status VARCHAR(20) DEFAULT 'pending',           -- pending/processing/completed/failed
    progress INT DEFAULT 0,                         -- 进度 0-100
    
    -- 任务信息
    total_chunks INT DEFAULT 0,
    processed_chunks INT DEFAULT 0,
    
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_task_document FOREIGN KEY (document_id) 
        REFERENCES public.documents(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_vec_task_doc ON public.document_vectorization_tasks(document_id);
CREATE INDEX idx_vec_task_status ON public.document_vectorization_tasks(status);

COMMENT ON TABLE public.document_vectorization_tasks IS '文档向量化任务';

-- ================================================================
-- 触发器：自动更新时间戳
-- ================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为相关表添加自动更新触发器
CREATE TRIGGER update_agent_sessions_updated_at 
    BEFORE UPDATE ON public.agent_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_vec_task_updated_at 
    BEFORE UPDATE ON public.document_vectorization_tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ================================================================
-- 辅助函数：向量检索
-- ================================================================

-- 1. 搜索用户知识库（即该用户的所有文档）
CREATE OR REPLACE FUNCTION search_user_knowledge_base(
    user_id_param BIGINT,
    query_embedding vector(1024),
    limit_count INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    chunk_id BIGINT,
    document_id BIGINT,
    document_title VARCHAR(255),
    content TEXT,
    similarity FLOAT,
    chunk_metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.document_id,
        d.title,
        dc.content,
        1 - (dc.embedding <=> query_embedding) as similarity,
        dc.metadata
    FROM public.document_chunks dc
    JOIN public.documents d ON dc.document_id = d.id
    WHERE 
        d.author_id = user_id_param
        AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_user_knowledge_base IS '搜索用户知识库（该用户的所有文档）';

-- 2. 搜索全站公开文档
CREATE OR REPLACE FUNCTION search_public_documents(
    query_embedding vector(1024),
    limit_count INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    chunk_id BIGINT,
    document_id BIGINT,
    document_title VARCHAR(255),
    author_id BIGINT,
    author_name VARCHAR(64),
    content TEXT,
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.document_id,
        d.title,
        d.author_id,
        u.username,
        dc.content,
        1 - (dc.embedding <=> query_embedding) as similarity
    FROM public.document_chunks dc
    JOIN public.documents d ON dc.document_id = d.id
    JOIN public.user u ON d.author_id = u.id
    WHERE 
        d.is_public = true
        AND d.status = 1
        AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_public_documents IS '搜索全站公开文档';

-- 3. 通用向量搜索（支持文档ID限定）
CREATE OR REPLACE FUNCTION search_documents_by_ids(
    query_embedding vector(1024),
    document_ids BIGINT[],
    limit_count INT DEFAULT 10,
    similarity_threshold FLOAT DEFAULT 0.7
)
RETURNS TABLE (
    chunk_id BIGINT,
    document_id BIGINT,
    content TEXT,
    similarity FLOAT,
    metadata JSONB
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id,
        dc.document_id,
        dc.content,
        1 - (dc.embedding <=> query_embedding) as similarity,
        dc.metadata
    FROM public.document_chunks dc
    WHERE 
        dc.document_id = ANY(document_ids)
        AND (1 - (dc.embedding <=> query_embedding)) >= similarity_threshold
    ORDER BY dc.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION search_documents_by_ids IS '通用向量搜索（按文档ID限定范围）';

-- ================================================================
-- 视图：便捷查询
-- ================================================================

-- 用户知识库统计视图（每个用户的文档向量统计）
CREATE OR REPLACE VIEW user_knowledge_base_stats AS
SELECT 
    u.id as user_id,
    u.username,
    COUNT(DISTINCT d.id) as doc_count,
    COUNT(DISTINCT CASE WHEN d.is_public = true THEN d.id END) as public_doc_count,
    COUNT(dc.id) as chunk_count,
    SUM(dc.token_count) as total_tokens,
    MAX(dc.created_at) as last_vectorized_at
FROM public.user u
LEFT JOIN public.documents d ON u.id = d.author_id
LEFT JOIN public.document_chunks dc ON d.id = dc.document_id
WHERE u.is_deleted = false
GROUP BY u.id, u.username;

COMMENT ON VIEW user_knowledge_base_stats IS '用户知识库统计（每个用户的所有文档向量）';

-- ================================================================
-- 初始数据（可选）
-- ================================================================

-- 示例：为文档状态添加注释
COMMENT ON COLUMN public.documents.status IS '状态：0=草稿 1=已发布 2=已归档';

-- 示例：为现有用户创建默认知识库（如需要）
-- INSERT INTO public.knowledge_bases (name, description, owner_id)
-- SELECT '我的知识库', '个人默认知识库', id 
-- FROM public.user 
-- WHERE id = 1;

-- ================================================================
-- 使用示例
-- ================================================================

/*
-- 1. 查看用户知识库统计
SELECT * FROM user_knowledge_base_stats WHERE user_id = 1;

-- 2. 搜索用户知识库（该用户的所有文档）
SELECT * FROM search_user_knowledge_base(
    1,                                              -- 用户ID
    '[0.1, 0.2, ...]'::vector(1536),              -- 查询向量
    10,                                             -- 返回数量
    0.7                                             -- 相似度阈值
);

-- 3. 搜索全站公开文档
SELECT * FROM search_public_documents(
    '[0.1, 0.2, ...]'::vector(1536),
    10,
    0.7
);

-- 4. 搜索指定文档范围
SELECT * FROM search_documents_by_ids(
    '[0.1, 0.2, ...]'::vector(1536),
    ARRAY[1, 2, 3],                                 -- 文档ID数组
    10,
    0.7
);

-- 5. 创建Agent会话
INSERT INTO public.agent_sessions (session_id, user_id, agent_type, title)
VALUES ('session_123', 1, 'writing', '写作助手对话');

-- 6. 记录Agent消息
INSERT INTO public.agent_messages (session_id, role, content)
VALUES ('session_123', 'user', '帮我写一篇关于AI的文章');

-- 7. 查询会话历史
SELECT * FROM public.agent_messages 
WHERE session_id = 'session_123' 
ORDER BY created_at;

-- 8. 创建文档向量化任务
INSERT INTO public.document_vectorization_tasks (document_id, status)
VALUES (1, 'pending');

-- 9. 查看用户所有文档的向量化状态
SELECT 
    d.id,
    d.title,
    d.created_at,
    COALESCE(COUNT(dc.id), 0) as chunk_count,
    t.status as vectorization_status
FROM public.documents d
LEFT JOIN public.document_chunks dc ON d.id = dc.document_id
LEFT JOIN public.document_vectorization_tasks t ON d.id = t.document_id
WHERE d.author_id = 1
GROUP BY d.id, d.title, d.created_at, t.status
ORDER BY d.created_at DESC;
*/

