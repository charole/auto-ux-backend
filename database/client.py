from supabase import create_client, Client
from typing import Optional
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class SupabaseManager:
    """Supabase 연결 관리자"""
    
    def __init__(self):
        self._client: Optional[Client] = None
        self._is_connected = False
    
    def connect(self) -> bool:
        """Supabase 연결 시도"""
        try:
            if not settings.supabase_url:
                logger.warning("Supabase 설정이 없습니다. 오프라인 모드로 실행됩니다.")
                return False
            
            # anon_key 우선 사용, 없으면 service_role_key 사용
            supabase_key = settings.supabase_anon_key or settings.supabase_service_role_key
            
            if not supabase_key:
                logger.warning("Supabase 키가 없습니다. 오프라인 모드로 실행됩니다.")
                return False
            
            self._client = create_client(
                settings.supabase_url,
                supabase_key
            )
            
            # 연결 테스트
            response = self._client.table('insurance_categories').select('id').limit(1).execute()
            self._is_connected = True
            logger.info("✅ Supabase 연결 성공")
            return True
            
        except Exception as e:
            logger.error(f"❌ Supabase 연결 실패: {e}")
            self._is_connected = False
            return False
    
    @property
    def client(self) -> Optional[Client]:
        """클라이언트 반환"""
        if not self._is_connected:
            self.connect()
        return self._client
    
    @property
    def is_connected(self) -> bool:
        """연결 상태 확인"""
        return self._is_connected

# 전역 Supabase 매니저
supabase_manager = SupabaseManager()

def get_supabase_client() -> Optional[Client]:
    """Supabase 클라이언트 반환"""
    return supabase_manager.client

def is_supabase_connected() -> bool:
    """Supabase 연결 상태 확인"""
    return supabase_manager.is_connected

async def test_supabase_connection() -> bool:
    """Supabase 연결 테스트"""
    try:
        client = get_supabase_client()
        if client is None:
            return False
        
        # 간단한 테스트 쿼리
        response = client.table('insurance_categories').select('id').limit(1).execute()
        return True
    except Exception as e:
        logger.error(f"Supabase 연결 테스트 실패: {e}")
        return False 