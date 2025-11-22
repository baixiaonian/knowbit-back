CREATE TABLE public.user (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(64),
    email VARCHAR(255),
    phone VARCHAR(20),
    phone_verified BOOLEAN NOT NULL DEFAULT false,
    avatar_url TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active BOOLEAN NOT NULL DEFAULT true,
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    -- 添加索引
    CONSTRAINT username_unique UNIQUE (username),
    CONSTRAINT email_unique UNIQUE (email),
    CONSTRAINT phone_unique UNIQUE (phone)
);

-- 创建其他索引
CREATE INDEX idx_user_created_at ON public.user (created_at);
CREATE INDEX idx_user_is_active ON public.user (is_active);
CREATE INDEX idx_user_is_deleted ON public.user (is_deleted);




-- 创建分类表
CREATE TABLE public.categories (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    parent_id BIGINT,
    slug VARCHAR(120),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- 保留字段
    reserved_field1 TEXT,
    reserved_field2 TEXT,
    reserved_field3 TEXT,
    -- 外键约束
    CONSTRAINT fk_parent_category FOREIGN KEY (parent_id) REFERENCES public.categories(id),
    -- 唯一约束
    CONSTRAINT slug_unique UNIQUE (slug)
);

-- 创建索引
CREATE INDEX idx_categories_parent_id ON public.categories (parent_id);

-- 创建文档表
CREATE TABLE public.documents (
    id BIGSERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    author_id BIGINT NOT NULL,
    folder_id BIGINT,
    is_public BOOLEAN NOT NULL DEFAULT false,
    status SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    excerpt TEXT,
    category_id BIGINT,
    tags TEXT[],
    -- 保留字段
    reserved_field1 TEXT,
    reserved_field2 TEXT,
    reserved_field3 TEXT,
    -- 外键约束
    CONSTRAINT fk_author FOREIGN KEY (author_id) REFERENCES public.user(id),
    CONSTRAINT fk_category FOREIGN KEY (category_id) REFERENCES public.categories(id)
    -- 注意：这里假设folders表已存在，如果不存在需要先创建
);

-- 创建文档表索引
CREATE INDEX idx_documents_author_id ON public.documents (author_id);
CREATE INDEX idx_documents_is_public_status ON public.documents (is_public, status);
CREATE INDEX idx_documents_created_at ON public.documents (created_at);
CREATE INDEX idx_documents_updated_at ON public.documents (updated_at);
CREATE INDEX idx_documents_category_id ON public.documents (category_id);
CREATE INDEX idx_documents_tags ON public.documents USING GIN (tags);

-- 创建统计表
CREATE TABLE public.document_stats (
    document_id BIGINT PRIMARY KEY,
    view_count BIGINT NOT NULL DEFAULT 0,
    like_count BIGINT NOT NULL DEFAULT 0,
    share_count BIGINT NOT NULL DEFAULT 0,
    comment_count BIGINT NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- 外键约束
    CONSTRAINT fk_document FOREIGN KEY (document_id) REFERENCES public.documents(id)
);

-- 创建评论表
CREATE TABLE public.comments (
    id BIGSERIAL PRIMARY KEY,
    document_id BIGINT NOT NULL,
    author_id BIGINT NOT NULL,
    parent_id BIGINT,
    content TEXT NOT NULL,
    status SMALLINT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- 保留字段
    reserved_field1 TEXT,
    reserved_field2 TEXT,
    reserved_field3 TEXT,
    -- 外键约束
    CONSTRAINT fk_document FOREIGN KEY (document_id) REFERENCES public.documents(id),
    CONSTRAINT fk_author FOREIGN KEY (author_id) REFERENCES public.user(id),
    CONSTRAINT fk_parent_comment FOREIGN KEY (parent_id) REFERENCES public.comments(id)
);

-- 创建评论表索引
CREATE INDEX idx_comments_document_id_status ON public.comments (document_id, status);
CREATE INDEX idx_comments_parent_id ON public.comments (parent_id);
CREATE INDEX idx_comments_created_at ON public.comments (created_at);

-- 创建文件夹表（支持多级目录）
CREATE TABLE public.folders (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    parent_id BIGINT,
    owner_id BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_deleted BOOLEAN NOT NULL DEFAULT false,
    -- 保留字段
    reserved_field1 TEXT,
    reserved_field2 TEXT,
    reserved_field3 TEXT,
    -- 外键约束
    CONSTRAINT fk_parent_folder FOREIGN KEY (parent_id) REFERENCES public.folders(id),
    CONSTRAINT fk_owner FOREIGN KEY (owner_id) REFERENCES public.user(id)
);

-- 创建索引
CREATE INDEX idx_folders_parent_id ON public.folders (parent_id);
CREATE INDEX idx_folders_owner_id ON public.folders (owner_id);
CREATE INDEX idx_folders_is_deleted ON public.folders (is_deleted);

-- 修改文档表，添加文件夹外键约束
ALTER TABLE public.documents 
ADD CONSTRAINT fk_folder 
FOREIGN KEY (folder_id) REFERENCES public.folders(id);


-- 用户大模型配置表（单条记录约束）
CREATE TABLE public.user_llm_config (
    user_id BIGINT PRIMARY KEY,  -- 与用户表一对一关系
    provider VARCHAR(20) NOT NULL DEFAULT 'OpenAI',
    api_key VARCHAR(255) NOT NULL,  -- 应用层需加密存储
    model_name VARCHAR(50) DEFAULT 'gpt-4',
    api_base VARCHAR(255) DEFAULT 'https://api.openai.com/v1',
    max_tokens INT DEFAULT 2000,
    temperature DECIMAL(3,2) DEFAULT 0.7,
    is_active BOOLEAN DEFAULT true,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES public.user(id)
);


DROP TABLE IF EXISTS public.document_chunks CASCADE;
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
    embedding vector(1024),                         -- 向量
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

-- 用户表添加微信openid字段
ALTER TABLE public.user ADD COLUMN wechat_openid VARCHAR(64) UNIQUE;
CREATE INDEX idx_user_openid ON public.user(wechat_openid);



-- 登录验证码表

DROP TABLE IF EXISTS public.login_code CASCADE;
CREATE TABLE public.login_code (
    id BIGSERIAL PRIMARY KEY,
    openid VARCHAR(64) NOT NULL,
    verification_code VARCHAR(6) NOT NULL,
    expire_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    user_id BIGINT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES public.user(id)
);

-- 方案1：在openid上创建唯一索引（推荐）
-- 确保同一openid在同一时间只有一个有效验证码
-- 应用层需要先删除/失效旧验证码，再创建新的
CREATE UNIQUE INDEX idx_code_openid_unique ON public.login_code(openid) 
WHERE used = FALSE;

-- 查询索引（用于验证码验证时快速查询）
CREATE INDEX idx_code_verify ON public.login_code(verification_code, used, expire_at);

-- 清理过期数据的索引
CREATE INDEX idx_code_expire ON public.login_code(expire_at) WHERE used = FALSE;

-- 智能体任务表（已改为内存存储，不再需要数据库表）
-- 任务管理现在使用内存存储（app/agents/tools/task_storage.py）
-- 任务数据只在会话期间存在，通过 WebSocket 实时推送到前端
-- 如果需要持久化任务历史，可以重新启用此表
/*
CREATE TABLE IF NOT EXISTS public.agent_task (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    session_id VARCHAR(64) NOT NULL,
    description TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    priority INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_task_session ON public.agent_task(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_task_user ON public.agent_task(user_id);
*/