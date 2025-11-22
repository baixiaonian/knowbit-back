-- ================================================================
-- 修复后的 Agent 消息历史表创建脚本
-- ================================================================
-- 说明：修复了 references 关键字冲突问题

-- 1. 如果函数已存在，先删除（避免冲突）
DROP FUNCTION IF EXISTS update_updated_at_column() CASCADE;

-- 2. 创建函数（确保完整定义）
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 3. Agent会话表（如果不存在）
CREATE TABLE IF NOT EXISTS public.agent_sessions (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE NOT NULL,
    user_id BIGINT NOT NULL,
    agent_type VARCHAR(50) NOT NULL DEFAULT 'writing',
    title VARCHAR(255),
    status VARCHAR(20) DEFAULT 'active',
    config JSONB DEFAULT '{}',
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_agent_user FOREIGN KEY (user_id) 
        REFERENCES public.user(id) ON DELETE CASCADE
);

-- 4. Agent消息历史表（修复：references 改为 message_references）
CREATE TABLE IF NOT EXISTS public.agent_messages (
    id BIGSERIAL PRIMARY KEY,
    session_id VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    tool_name VARCHAR(100),
    tool_calls JSONB,
    tool_results JSONB,
    message_references JSONB,  -- 修复：避免使用保留关键字 references
    metadata JSONB DEFAULT '{}',
    message_order INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT fk_agent_session FOREIGN KEY (session_id) 
        REFERENCES public.agent_sessions(session_id) ON DELETE CASCADE,
    CONSTRAINT chk_role CHECK (role IN ('user', 'assistant', 'system', 'tool'))
);

-- 5. 创建索引
CREATE INDEX IF NOT EXISTS idx_agent_session ON public.agent_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_user ON public.agent_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_agent_type ON public.agent_sessions(agent_type);
CREATE INDEX IF NOT EXISTS idx_agent_status ON public.agent_sessions(status);
CREATE INDEX IF NOT EXISTS idx_agent_user_status ON public.agent_sessions(user_id, status);

CREATE INDEX IF NOT EXISTS idx_agent_msg_session ON public.agent_messages(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_msg_role ON public.agent_messages(role);
CREATE INDEX IF NOT EXISTS idx_agent_msg_created ON public.agent_messages(created_at);
CREATE INDEX IF NOT EXISTS idx_agent_msg_session_order ON public.agent_messages(session_id, message_order);
CREATE INDEX IF NOT EXISTS idx_agent_msg_session_role ON public.agent_messages(session_id, role);

-- 6. 创建触发器
DROP TRIGGER IF EXISTS update_agent_sessions_updated_at ON public.agent_sessions;
CREATE TRIGGER update_agent_sessions_updated_at 
    BEFORE UPDATE ON public.agent_sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 7. 添加注释
COMMENT ON TABLE public.agent_sessions IS 'Agent智能体会话表 - 存储会话元信息';
COMMENT ON TABLE public.agent_messages IS 'Agent消息历史表 - 存储会话中的所有消息，支持对话记忆';

COMMENT ON COLUMN public.agent_sessions.session_id IS '会话唯一标识（UUID格式）';
COMMENT ON COLUMN public.agent_sessions.agent_type IS '智能体类型：writing（写作）/research（研究）/qa（问答）/custom（自定义）';
COMMENT ON COLUMN public.agent_sessions.status IS '会话状态：active（活跃）/completed（已完成）/archived（已归档）';
COMMENT ON COLUMN public.agent_sessions.config IS 'Agent配置信息（JSON格式）';
COMMENT ON COLUMN public.agent_sessions.metadata IS '扩展元数据（JSON格式），可存储文档ID、任务上下文等';

COMMENT ON COLUMN public.agent_messages.role IS '消息角色：user（用户）/assistant（助手）/system（系统）/tool（工具）';
COMMENT ON COLUMN public.agent_messages.content IS '消息内容（文本）';
COMMENT ON COLUMN public.agent_messages.tool_name IS '工具名称（当消息是工具调用时）';
COMMENT ON COLUMN public.agent_messages.tool_calls IS '工具调用记录（JSON格式）';
COMMENT ON COLUMN public.agent_messages.tool_results IS '工具返回结果（JSON格式）';
COMMENT ON COLUMN public.agent_messages.message_references IS '引用信息（JSON格式），如文档chunks、知识库片段等';
COMMENT ON COLUMN public.agent_messages.message_order IS '消息在会话中的顺序（从0开始递增）';

