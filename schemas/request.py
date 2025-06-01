from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime, date
import uuid

# 기존 호환성을 위한 레거시 스키마
class UXRequest(BaseModel):
    """기존 UX 추천 요청 (레거시)"""
    user_id: Optional[str] = Field(None, description="사용자 ID")
    session_id: Optional[str] = Field(None, description="세션 ID")
    page_url: str = Field(..., description="현재 페이지 URL")
    user_actions: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="사용자 액션 로그")
    user_segment: Optional[str] = Field(None, description="사용자 세그먼트")
    device_info: Optional[Dict[str, Any]] = Field(default_factory=dict, description="디바이스 정보")
    custom_message: Optional[str] = Field(None, description="사용자 커스텀 메시지")

# 보험 서비스 특화 UX 요청 스키마들
class InsuranceUXRequest(BaseModel):
    """보험 서비스 UX 추천 요청"""
    user_id: Optional[uuid.UUID] = None
    session_id: str
    page_type: str  # product_list, product_detail, claim_form, consultation, mypage, onboarding
    page_url: str
    user_context: Optional[str] = None
    user_segment: Optional[str] = None  # new_user, existing_customer, considering_user, etc.
    device_type: Optional[str] = None  # desktop, mobile, tablet
    user_agent: Optional[str] = None

class UserActivityRequest(BaseModel):
    """사용자 활동 로그 요청 (기존 user_activity_logs 테이블 활용)"""
    user_id: Optional[uuid.UUID] = None
    activity_type: str  # product_view, claim_start, consultation_request, etc.
    description: Optional[str] = None
    page_url: str
    element_selector: Optional[str] = None
    element_text: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class InsurancePageGoalRequest(BaseModel):
    """보험 페이지 목표 설정 요청"""
    page_type: str
    page_url_pattern: str
    goal_description: str
    target_actions: List[str]
    success_criteria: Optional[str] = None
    conversion_metrics: Optional[Dict[str, Any]] = None
    user_segment: Optional[str] = None
    priority: int = 3

class UXMetricRequest(BaseModel):
    """UX 메트릭 기록 요청"""
    user_id: str = Field(..., description="사용자 ID")
    session_id: str = Field(..., description="세션 ID")
    page_type: str = Field(..., description="페이지 타입")
    metric_type: str = Field(..., description="메트릭 타입")
    metric_value: float = Field(..., description="메트릭 값")
    context_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="컨텍스트 데이터")

class ProductUXRuleRequest(BaseModel):
    """상품별 UX 규칙 생성 요청"""
    product_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    rule_name: str
    rule_description: Optional[str] = None
    trigger_conditions: Dict[str, Any]
    recommended_actions: Dict[str, Any]
    target_audience: Optional[str] = None

class UXFeedbackRequest(BaseModel):
    """UX 추천에 대한 피드백 요청"""
    recommendation_id: uuid.UUID
    feedback_score: float  # 1-5 점수
    feedback_comment: Optional[str] = None
    applied: bool = False
    conversion_impact: Optional[Dict[str, Any]] = None

class BehaviorAnalysisRequest(BaseModel):
    """사용자 행동 분석 요청"""
    user_id: uuid.UUID
    analysis_period_days: int = 30
    include_device_analysis: bool = True
    include_journey_analysis: bool = True

class ABTestRequest(BaseModel):
    """A/B 테스트 실험 생성 요청"""
    experiment_name: str
    description: Optional[str] = None
    page_type: str
    hypothesis: str
    control_version: Dict[str, Any]
    variant_versions: Dict[str, Any]
    traffic_allocation: Dict[str, Any]
    success_metrics: List[str]
    start_date: datetime
    end_date: Optional[datetime] = None

# 보험 도메인 특화 분석 요청들
class ProductRecommendationRequest(BaseModel):
    """보험 상품 추천을 위한 UX 분석 요청"""
    user_id: Optional[uuid.UUID] = None
    user_profile: Optional[Dict[str, Any]] = None
    current_page: str
    viewed_products: Optional[List[uuid.UUID]] = None
    user_behavior_data: Optional[Dict[str, Any]] = None

class ClaimFormOptimizationRequest(BaseModel):
    """보험금 청구 양식 최적화 요청"""
    user_id: Optional[uuid.UUID] = None
    claim_type: str
    user_difficulties: Optional[List[str]] = None
    form_completion_stage: Optional[str] = None
    device_type: Optional[str] = None

class ConsultationUXRequest(BaseModel):
    """상담 서비스 UX 개선 요청"""
    user_id: Optional[uuid.UUID] = None
    consultation_type: str
    user_preferences: Optional[Dict[str, Any]] = None
    previous_consultations: Optional[List[Dict[str, Any]]] = None
    urgency_level: Optional[str] = None

class AccessibilityAnalysisRequest(BaseModel):
    """접근성 분석 요청"""
    user_id: Optional[uuid.UUID] = None
    page_type: str
    accessibility_needs: Optional[List[str]] = None
    user_age: Optional[int] = None
    device_capabilities: Optional[Dict[str, Any]] = None

# 동적 UI 생성 요청 스키마들
class DynamicUIRequest(BaseModel):
    """동적 UI 생성 요청"""
    page_type: str = Field(..., description="페이지 타입 (home, products, claim, mypage, consultation, faq)")
    user_id: Optional[str] = Field(None, description="사용자 ID")
    product_id: Optional[str] = Field(None, description="상품 ID (상품 상세 페이지용)")
    user_context: Optional[Dict[str, Any]] = Field(default_factory=dict, description="사용자 컨텍스트 정보")
    custom_requirements: Optional[str] = Field(None, description="커스텀 요구사항")
    accessibility_preferences: Optional[Dict[str, Any]] = Field(default_factory=dict, description="접근성 설정")

class QuickUIRequest(BaseModel):
    """간편 UI 생성 요청"""
    user_id: Optional[uuid.UUID] = None
    preferences: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None

class UserInteractionLog(BaseModel):
    """사용자 상호작용 로그"""
    user_id: str = Field(..., description="사용자 ID")
    session_id: str = Field(..., description="세션 ID")
    page_url: str = Field(..., description="페이지 URL")
    action_type: str = Field(..., description="액션 타입 (click, scroll, hover, input 등)")
    element_selector: Optional[str] = Field(None, description="요소 셀렉터")
    element_text: Optional[str] = Field(None, description="요소 텍스트")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="추가 메타데이터")
    timestamp: datetime = Field(default_factory=datetime.now, description="타임스탬프")

class FeedbackRequest(BaseModel):
    """UX 추천에 대한 피드백"""
    recommendation_id: str = Field(..., description="추천 ID")
    user_id: str = Field(..., description="사용자 ID")
    feedback_score: float = Field(..., ge=1.0, le=5.0, description="피드백 점수 (1-5)")
    feedback_comment: Optional[str] = Field(None, description="피드백 코멘트")
    applied: bool = Field(False, description="추천 적용 여부")