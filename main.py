from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging

from config.settings import settings, setup_logging, validate_core_settings
from routers.ux_router import router as ux_router
from database.client import supabase_manager

# 로깅 설정
setup_logging()
logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="AI 기반 동적 UX 생성 서비스 - LangChain + Supabase"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(ux_router)

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "service": settings.app_name,
        "version": settings.version,
        "status": "running",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """전역 헬스 체크"""
    return {
        "status": "healthy",
        "service": settings.app_name,
        "database": supabase_manager.is_connected,
        "config_valid": validate_core_settings()
    }

@app.on_event("startup")
async def startup_event():
    """서버 시작 시 실행"""
    logger.info(f"🚀 {settings.app_name} v{settings.version} 시작")
    
    # 설정 검증
    validate_core_settings()
    
    # Supabase 연결 시도
    if supabase_manager.connect():
        logger.info("✅ 모든 서비스 초기화 완료")
    else:
        logger.warning("⚠️ 일부 서비스가 제한된 모드로 실행됩니다")

@app.on_event("shutdown")
async def shutdown_event():
    """서버 종료 시 실행"""
    logger.info("🛑 서버 종료")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug
    )
