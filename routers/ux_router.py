from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
import logging

from schemas.response import SimpleUXResponse
from services.ux_service_agent import ux_service, smart_ux_service
from database.client import is_supabase_connected

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/ux", tags=["UX Service"])

# =====================================
# 🚀 통합된 UI 생성 엔드포인트
# =====================================

@router.get("/generate-ui", response_model=SimpleUXResponse)
async def generate_ui(
    page_type: str = Query(..., description="페이지 타입 (home, search, products)"),
    user_query: Optional[str] = Query(None, description="사용자 검색 쿼리 (search 페이지용)")
):
    """🚀 스마트 AI Agent 기반 UI 생성 (완전 자동화)"""
    try:
        # 🤖 AI Agent 방식으로 통합
        if user_query and page_type == 'search':
            # 사용자 쿼리가 있으면 AI Agent 사용
            response = await smart_ux_service.generate_smart_ui(user_query)
        else:
            # 일반 페이지는 기존 방식 유지 (하지만 개선됨)
            response = await ux_service.generate_dynamic_ui(
                page_type=page_type,
                user_context=None,
                custom_requirements=user_query
            )
        
        return response
        
    except Exception as e:
        logger.error(f"❌ 스마트 UI 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"UI 생성 실패: {str(e)}")

@router.get("/generate-ui-smart", response_model=SimpleUXResponse)
async def generate_smart_ui(
    query: str = Query(..., description="사용자 요청 (예: '20대에게 추천하는 보험')")
):
    """
    🤖 AI Agent 기반 스마트 UI 생성
    
    - AI가 사용자 요청을 분석
    - 적절한 Tool을 사용해 DB에서 맞는 데이터만 검색  
    - 검색 결과로 맞춤형 UI 생성
    """
    try:
        # AI Agent로 UI 생성
        response = await smart_ux_service.generate_smart_ui(query)
        
        return response
        
    except Exception as e:
        logger.error(f"❌ 스마트 AI UI 생성 실패: {e}")
        import traceback
        logger.error(f"❌ 라우터 스택 트레이스: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"스마트 AI UI 생성 실패: {str(e)}")

@router.post("/generate-ui", response_model=SimpleUXResponse)
async def generate_dynamic_ui_post(
    page_type: str,
    user_id: Optional[str] = None,
    product_id: Optional[str] = None,
    custom_requirements: Optional[str] = None
):
    """동적 UI 생성 - POST 방식 (레거시 호환)"""
    try:
        user_context = {}
        if user_id:
            user_context['user_id'] = user_id
        if product_id:
            user_context['product_id'] = product_id
            
        result = await ux_service.generate_dynamic_ui(
            page_type=page_type,
            user_context=user_context,
            custom_requirements=custom_requirements
        )
        
        return result
        
    except Exception as e:
        logger.error(f"UI 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"UI 생성 중 오류: {str(e)}")

# =====================================
# 🔍 검색 및 데이터 조회 엔드포인트
# =====================================

@router.get("/search")
async def search_insurance_content(
    q: str = Query(..., description="검색 키워드"),
    limit: int = Query(20, ge=1, le=100, description="결과 개수 제한"),
    include_products: bool = Query(True, description="보험 상품 포함 여부"),
    include_faqs: bool = Query(True, description="FAQ 포함 여부"),
    include_testimonials: bool = Query(True, description="고객 후기 포함 여부")
):
    """통합 검색 API - 보험 상품, FAQ, 고객 후기 등을 검색"""
    try:
        if not q.strip():
            raise HTTPException(status_code=400, detail="검색어를 입력해주세요.")
        
        search_results = await ux_service.search_content(
            query=q,
            limit=limit,
            include_products=include_products,
            include_faqs=include_faqs,
            include_testimonials=include_testimonials
        )
        
        return {
            "success": True,
            "query": q,
            "data": search_results,
            "total_results": sum([
                len(search_results.get('products', [])),
                len(search_results.get('faqs', [])),
                len(search_results.get('testimonials', []))
            ])
        }
        
    except Exception as e:
        logger.error(f"검색 실패: {e}")
        raise HTTPException(status_code=500, detail=f"검색 중 오류: {str(e)}")

@router.get("/products")
async def get_insurance_products(
    category: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """보험 상품 조회"""
    try:
        products = await ux_service.get_insurance_products(category)
        return {
            "success": True,
            "data": products[:limit],
            "total": len(products)
        }
    except Exception as e:
        logger.error(f"상품 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/categories")
async def get_insurance_categories():
    """보험 카테고리 조회"""
    try:
        categories = await ux_service.get_insurance_categories()
        return {
            "success": True,
            "data": categories
        }
    except Exception as e:
        logger.error(f"카테고리 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/faqs")
async def get_faqs(
    category: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """FAQ 조회"""
    try:
        faqs = await ux_service.get_faqs(category)
        return {
            "success": True,
            "data": faqs[:limit],
            "total": len(faqs)
        }
    except Exception as e:
        logger.error(f"FAQ 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/testimonials")
async def get_testimonials(
    product_id: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100)
):
    """고객 후기 조회"""
    try:
        testimonials = await ux_service.get_testimonials(product_id)
        return {
            "success": True,
            "data": testimonials[:limit],
            "total": len(testimonials)
        }
    except Exception as e:
        logger.error(f"고객 후기 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# =====================================
# 🔧 시스템 관리 엔드포인트
# =====================================

@router.get("/health")
async def health_check():
    """서비스 상태 확인"""
    try:
        return {
            "status": "healthy",
            "service": "Auto UX Backend",
            "database_connected": is_supabase_connected(),
            "ai_available": ux_service.ai_available,
            "endpoints": [
                "/generate-ui",
                "/generate-ui-smart",
                "/search",
                "/products", 
                "/categories",
                "/faqs",
                "/testimonials",
                "/health"
            ]
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        } 