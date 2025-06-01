from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Optional, Dict, Any
import logging

from services.ux_service import ux_service
from services.ux_service_agent import smart_ux_service
from schemas.response import SimpleUXResponse

router = APIRouter(prefix="/api/v1/ux", tags=["UX"])
logger = logging.getLogger(__name__)

@router.get("/generate-ui", response_model=SimpleUXResponse)
async def generate_ui(
    page_type: str = Query(..., description="페이지 타입 (home, search, products)"),
    user_query: Optional[str] = Query(None, description="사용자 검색 쿼리 (search 페이지용)")
):
    """🚀 스마트 AI Agent 기반 UI 생성 (완전 자동화)"""
    try:
        logger.info(f"🚀 스마트 UI 생성: {page_type}, 쿼리: {user_query}")
        
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
        
        logger.info(f"✅ 스마트 UI 생성 완료: {len(response.components)}개 컴포넌트")
        return response
        
    except Exception as e:
        logger.error(f"❌ 스마트 UI 생성 실패: {e}")
        raise HTTPException(status_code=500, detail=f"UI 생성 실패: {str(e)}")

@router.get("/generate-ui-smart", response_model=SimpleUXResponse)
async def generate_smart_ui(
    query: str = Query(..., description="사용자 요청 (예: '5살 어린이에게 맞는 보험')")
):
    """
    🤖 AI Agent 기반 스마트 UI 생성
    
    - AI가 사용자 요청을 분석
    - 적절한 Tool을 사용해 DB에서 맞는 데이터만 검색  
    - 검색 결과로 맞춤형 UI 생성
    """
    try:
        logger.info(f"🤖 스마트 AI 요청: {query}")
        logger.info(f"🔍 smart_ux_service.ai_available: {smart_ux_service.ai_available}")
        
        # AI Agent로 UI 생성
        response = await smart_ux_service.generate_smart_ui(query)
        
        logger.info(f"✅ 스마트 AI 응답 생성 완료: {len(response.components)}개 컴포넌트, ai_generated={response.ai_generated}")
        return response
        
    except Exception as e:
        logger.error(f"❌ 스마트 AI UI 생성 실패: {e}")
        import traceback
        logger.error(f"❌ 라우터 스택 트레이스: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"스마트 AI UI 생성 실패: {str(e)}")

@router.get("/products")
async def get_products(category: Optional[str] = Query(None)):
    """보험 상품 목록 조회"""
    try:
        products = await ux_service.get_insurance_products(category)
        return {"products": products}
    except Exception as e:
        logger.error(f"상품 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"상품 조회 실패: {str(e)}")

@router.get("/categories")
async def get_categories():
    """보험 카테고리 목록 조회"""
    try:
        categories = await ux_service.get_insurance_categories()
        return {"categories": categories}
    except Exception as e:
        logger.error(f"카테고리 조회 실패: {e}")
        raise HTTPException(status_code=500, detail=f"카테고리 조회 실패: {str(e)}") 