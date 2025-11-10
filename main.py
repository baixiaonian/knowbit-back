"""
AI写作工具 - FastAPI应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import folders, documents, ai_help, ai_text, vectorization, ai_chat, wechat_auth, agent

# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI写作工具后端API",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"]
)

# 注册路由
app.include_router(folders.router)
app.include_router(documents.router)
app.include_router(ai_help.router)
app.include_router(ai_text.router)
app.include_router(vectorization.router)
app.include_router(ai_chat.router)
app.include_router(wechat_auth.router)
app.include_router(agent.router)


@app.get("/")
async def root():
    """根路径"""
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "message": "AI写作工具后端API正在运行"
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG
    )
