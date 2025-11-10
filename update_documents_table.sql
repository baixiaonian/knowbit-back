-- ================================================================
-- 为documents表添加向量化状态字段
-- ================================================================

-- 添加向量化相关字段
ALTER TABLE public.documents 
ADD COLUMN IF NOT EXISTS vectorized_at TIMESTAMPTZ,              -- 最后向量化时间
ADD COLUMN IF NOT EXISTS vectorization_status VARCHAR(20) DEFAULT 'pending',  -- pending/processing/completed/failed
ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);               -- 内容哈希，用于检测是否真正改变

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_documents_vec_status ON public.documents(vectorization_status);
CREATE INDEX IF NOT EXISTS idx_documents_vectorized_at ON public.documents(vectorized_at);

-- 添加注释
COMMENT ON COLUMN public.documents.vectorized_at IS '最后向量化时间';
COMMENT ON COLUMN public.documents.vectorization_status IS '向量化状态：pending(待处理)/processing(处理中)/completed(已完成)/failed(失败)';
COMMENT ON COLUMN public.documents.content_hash IS '内容MD5哈希，用于检测内容变化';

-- 查看需要向量化的文档
-- SELECT id, title, vectorization_status, vectorized_at, updated_at
-- FROM public.documents
-- WHERE vectorization_status IN ('pending', 'failed')
-- OR (vectorized_at IS NULL)
-- OR (updated_at > vectorized_at);  -- 文档更新时间晚于向量化时间

