from fastapi import FastAPI 
from fastapi.middleware.cors import CORSMiddleware 
from app.config import settings 
 
app = FastAPI( 
    title=settings.APP_NAME, 
    description="越南本地生活平台 - Vinow后端API", 
    version=settings.APP_VERSION, 
    docs_url="/docs", 
    redoc_url="/redoc" 
) 
 
# CORS中间件 
app.add_middleware( 
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"], 
) 
 
@app.get("/") 
async def root(): 
    return { 
        "message": f"{settings.APP_NAME} API服务运行正常", 
        "version": settings.APP_VERSION, 
        "status": "active" 
    } 
 
@app.get("/health") 
async def health_check(): 
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"} 
 
if __name__ == "__main__": 
    import uvicorn 
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=True) 
