from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid

# 기존 호환성을 위한 레거시 스키마
class UIComponent(BaseModel):
    type: str
    id: str
    title: Optional[str] = None
    content: str
    style: Optional[str] = None
    priority: int = 1
    data: Optional[Dict[str, Any]] = {}

class SimpleUXResponse(BaseModel):
    """간소화된 UX 응답 - 프론트엔드 실사용 중심"""
    components: List[UIComponent]
    total_products: Optional[int] = None
    generated_at: Optional[str] = None
    ai_generated: bool = False

# 기존 UX 응답 (레거시)
class UXResponse(BaseModel):
    """기존 UX 응답 (레거시)"""
    components: List[UIComponent]
    layout: Dict[str, Any] = {"type": "stack", "spacing": "medium"}
    accessibility: Dict[str, Any] = {"high_contrast": False, "large_text": False}
    metadata: Dict[str, Any] = {}

# 보험 서비스 특화 응답 스키마들
class InsuranceUIComponent(BaseModel):
    """보험 서비스 특화 UI 컴포넌트"""
    type: str  # product_card, premium_calculator, claim_form, consultation_button, etc.
    position: Optional[str] = None
    content: Optional[str] = None
    style: Optional[str] = None
    priority: int = 3
    reasoning: Optional[str] = None
    insurance_specific: Optional[Dict[str, Any]] = None
    accessibility_features: Optional[List[str]] = None
    target_user_segment: Optional[str] = None
    compliance_notes: Optional[List[str]] = None

class InsuranceLayoutChange(BaseModel):
    """보험 서비스 레이아웃 변경사항"""
    element: str
    change: str
    reasoning: str
    impact_on_conversion: Optional[str] = None
    compliance_considerations: Optional[str] = None

class InsuranceBehaviorAnalysis(BaseModel):
    """보험 서비스 사용자 행동 분석"""
    behavior_insights: str
    pain_points: List[str]
    user_journey_bottlenecks: Optional[List[str]] = None
    insurance_specific_issues: Optional[List[str]] = None
    accessibility_concerns: Optional[List[str]] = None
    conversion_opportunities: Optional[List[str]] = None

class InsuranceUXRecommendations(BaseModel):
    """보험 서비스 UX 추천사항"""
    components: List[InsuranceUIComponent]
    layout_changes: List[InsuranceLayoutChange]
    accessibility_improvements: Optional[List[str]] = None
    conversion_optimizations: Optional[List[str]] = None
    compliance_notes: Optional[List[str]] = None
    personalization_suggestions: Optional[List[str]] = None

class InsuranceUXResponse(BaseModel):
    """보험 서비스 UX 추천 응답"""
    analysis: InsuranceBehaviorAnalysis
    recommendations: InsuranceUXRecommendations
    confidence_score: Optional[float] = None
    estimated_conversion_impact: Optional[str] = None
    implementation_priority: Optional[str] = None
    user_segment: Optional[str] = None
    recommendation_id: Optional[uuid.UUID] = None

class UserActivityResponse(BaseModel):
    """사용자 활동 로그 응답"""
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    activity_type: str
    description: Optional[str]
    page_url: str
    created_at: datetime
    success: bool = True

class UXPageGoalResponse(BaseModel):
    """UX 페이지 목표 응답"""
    id: uuid.UUID
    page_type: str
    page_url_pattern: str
    goal_description: str
    target_actions: List[str]
    success_criteria: Optional[str]
    user_segment: Optional[str]
    priority: int
    created_at: datetime

class UXMetricResponse(BaseModel):
    """UX 메트릭 응답"""
    id: uuid.UUID
    user_id: Optional[uuid.UUID]
    session_id: str
    page_type: str
    metric_type: str
    metric_value: float
    benchmark_value: Optional[float]
    improvement_percentage: Optional[float]
    recorded_at: datetime

class ProductUXRuleResponse(BaseModel):
    """상품별 UX 규칙 응답"""
    id: uuid.UUID
    product_id: Optional[uuid.UUID]
    category_id: Optional[uuid.UUID]
    rule_name: str
    rule_description: Optional[str]
    trigger_conditions: Dict[str, Any]
    recommended_actions: Dict[str, Any]
    target_audience: Optional[str]
    effectiveness_score: Optional[float]
    is_active: bool
    created_at: datetime

class BehaviorInsightResponse(BaseModel):
    """사용자 행동 분석 결과 응답"""
    id: uuid.UUID
    user_id: uuid.UUID
    analysis_period_start: datetime
    analysis_period_end: datetime
    behavior_patterns: Dict[str, Any]
    pain_points: List[str]
    user_journey_stage: Optional[str]
    device_preferences: Optional[Dict[str, Any]]
    interaction_intensity: Optional[str]
    drop_off_points: Optional[List[str]]
    preferred_features: Optional[List[str]]
    accessibility_needs: Optional[List[str]]
    created_at: datetime

class ABTestResponse(BaseModel):
    """A/B 테스트 실험 응답"""
    id: uuid.UUID
    experiment_name: str
    description: Optional[str]
    page_type: str
    hypothesis: str
    status: str
    start_date: datetime
    end_date: Optional[datetime]
    results: Optional[Dict[str, Any]]
    statistical_significance: Optional[float]
    winner_variant: Optional[str]
    created_at: datetime

# 보험 도메인 특화 분석 응답들
class ProductRecommendationResponse(BaseModel):
    """보험 상품 추천 UX 분석 응답"""
    recommended_products: List[Dict[str, Any]]
    ui_optimizations: List[InsuranceUIComponent]
    personalization_data: Dict[str, Any]
    conversion_predictions: Optional[Dict[str, float]]

class ClaimFormOptimizationResponse(BaseModel):
    """보험금 청구 양식 최적화 응답"""
    form_improvements: List[InsuranceUIComponent]
    simplified_steps: List[str]
    accessibility_enhancements: List[str]
    estimated_completion_improvement: Optional[str]

class ConsultationUXResponse(BaseModel):
    """상담 서비스 UX 개선 응답"""
    consultation_flow_improvements: List[InsuranceLayoutChange]
    scheduling_optimizations: List[str]
    communication_preferences: Dict[str, Any]
    wait_time_optimizations: Optional[List[str]]

class AccessibilityAnalysisResponse(BaseModel):
    """접근성 분석 응답"""
    accessibility_score: float
    identified_barriers: List[str]
    recommended_improvements: List[str]
    compliance_status: Dict[str, str]
    priority_fixes: List[str]

# 통합 대시보드 응답
class UXDashboardResponse(BaseModel):
    """UX 대시보드 통합 응답"""
    overall_ux_score: float
    conversion_metrics: Dict[str, float]
    user_satisfaction_scores: Dict[str, float]
    top_recommendations: List[InsuranceUIComponent]
    critical_issues: List[str]
    improvement_trends: Dict[str, List[float]]
    page_performance: Dict[str, Dict[str, float]]

# 공통 응답들
class SuccessResponse(BaseModel):
    """일반적인 성공 응답"""
    success: bool = True
    message: str
    data: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    """에러 응답"""
    success: bool = False
    message: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class PaginatedResponse(BaseModel):
    """페이지네이션 응답"""
    items: List[Any]
    total: int
    page: int
    size: int
    has_next: bool
    has_prev: bool

# 동적 UI 생성 응답 스키마들
class DynamicUIComponent(BaseModel):
    """동적 생성된 UI 컴포넌트"""
    type: str  # InsuranceProductCard, ContractSummary, ClaimStatus 등
    props: Dict[str, Any]  # 컴포넌트 속성들
    style: Optional[Dict[str, Any]] = None  # 스타일 정보
    conditions: Optional[Dict[str, Any]] = None  # 표시 조건들

class LayoutInstructions(BaseModel):
    """레이아웃 구성 지침"""
    layout_type: str  # grid, flex, stack
    responsive_breakpoints: Dict[str, str]
    component_order: List[str]
    spacing: str
    accessibility: Dict[str, str]

class DynamicUIResponse(BaseModel):
    """동적 UI 생성 응답"""
    success: bool
    intent: Optional[Dict[str, Any]] = None  # 분석된 사용자 의도
    data: Optional[Dict[str, Any]] = None  # 조회된 데이터
    ui_components: List[DynamicUIComponent]
    layout_instructions: Optional[LayoutInstructions] = None
    error: Optional[str] = None
    fallback_ui: Optional[List[DynamicUIComponent]] = None
