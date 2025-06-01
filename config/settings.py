from pydantic_settings import BaseSettings
from typing import Optional
import os
import logging

class Settings(BaseSettings):
    # 기본 설정
    app_name: str = "Auto UX Backend"
    debug: bool = False
    version: str = "1.0.0"
    
    # 서버 설정
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Supabase 설정 (핵심) - 실제 환경 변수명과 일치
    supabase_url: Optional[str] = None
    supabase_anon_key: Optional[str] = None
    supabase_service_role_key: Optional[str] = None
    
    # OpenAI API 설정 (핵심)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-3.5-turbo"
    openai_temperature: float = 0.7
    openai_max_tokens: int = 2000
    
    # 추가 설정
    database_url: Optional[str] = None
    log_level: str = "INFO"
    
    # CORS 설정
    allowed_origins: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://localhost:4173",  # Vite preview
        "*"  # 개발 시에만 임시로 모든 도메인 허용
    ]
    
    # JWT 설정 (미래 확장용)
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # 파일 업로드 설정
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    allowed_file_types: list = [".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx"]
    
    # UX 분석 설정
    ux_analysis_batch_size: int = 100
    ux_cache_expire_seconds: int = 3600  # 1시간
    
    # LangChain 설정
    langchain_verbose: bool = False
    langchain_cache: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # 추가 필드 무시

# 전역 설정 인스턴스
settings = Settings()

def setup_logging():
    """기본 로깅 설정"""
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

def validate_core_settings():
    """핵심 설정 검증"""
    warnings = []
    
    if not settings.supabase_url:
        warnings.append("SUPABASE_URL이 설정되지 않았습니다.")
    
    if not settings.supabase_anon_key and not settings.supabase_service_role_key:
        warnings.append("SUPABASE_ANON_KEY 또는 SUPABASE_SERVICE_ROLE_KEY가 설정되지 않았습니다.")
    
    if not settings.openai_api_key:
        warnings.append("OPENAI_API_KEY가 설정되지 않았습니다.")
    
    if warnings:
        print(f"⚠️  설정 경고: {', '.join(warnings)}")
        print("   일부 기능이 제한될 수 있습니다.")
    
    return len(warnings) == 0

# 환경별 설정 확인
def get_environment() -> str:
    """현재 실행 환경 반환"""
    return os.getenv("ENVIRONMENT", "development")

def is_development() -> bool:
    """개발 환경 여부 확인"""
    return get_environment() == "development"

def is_production() -> bool:
    """프로덕션 환경 여부 확인"""
    return get_environment() == "production"

# 설정 검증 (Optional로 변경)
def validate_settings():
    """필수 설정 값들이 올바르게 설정되었는지 확인"""
    warnings = []
    
    if not settings.supabase_url:
        warnings.append("SUPABASE_URL이 설정되지 않았습니다. 일부 기능이 제한됩니다.")
    
    if not settings.supabase_anon_key:
        warnings.append("SUPABASE_ANON_KEY가 설정되지 않았습니다. 일부 기능이 제한됩니다.")
    
    if not settings.openai_api_key:
        warnings.append("OPENAI_API_KEY가 설정되지 않았습니다. AI 기능이 제한됩니다.")
    
    if warnings:
        print(f"⚠️  설정 경고: {', '.join(warnings)}")
    
    return True 