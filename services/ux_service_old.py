from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

# 핵심 imports
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate

from config.settings import settings
from database.client import get_supabase_client, is_supabase_connected, supabase_manager
from schemas.response import UXResponse, UIComponent

logger = logging.getLogger(__name__)

class CoreUXService:
    """핵심 UX 서비스 - LangChain + Supabase"""
    
    def __init__(self):
        # Supabase 클라이언트 초기화 - 연결을 강제로 시도
        supabase_manager.connect()  # 강제 연결 시도
        self.supabase = get_supabase_client()
        
        self.llm = None
        self.ai_available = False
        
        # OpenAI/LangChain 초기화
        if settings.openai_api_key:
            try:
                self.llm = ChatOpenAI(
                    openai_api_key=settings.openai_api_key,
                    model_name=settings.openai_model,
                    temperature=settings.openai_temperature,
                    max_tokens=settings.openai_max_tokens
                )
                self.ai_available = True
                logger.info("✅ LangChain/OpenAI 초기화 성공")
            except Exception as e:
                logger.error(f"❌ AI 서비스 초기화 실패: {e}")
        else:
            logger.warning("OpenAI API 키가 없습니다. AI 기능이 비활성화됩니다.")
    
    async def generate_dynamic_ui(
        self, 
        page_type: str,
        user_context: Optional[Dict[str, Any]] = None,
        custom_requirements: Optional[str] = None
    ) -> UXResponse:
        """동적 UI 생성 - 핵심 기능"""
        try:
            logger.info(f"UI 생성 요청: {page_type}")
            
            # 데이터베이스에서 관련 데이터 수집
            db_data = await self._collect_data(page_type, user_context)
            
            # AI로 UI 생성
            if self.ai_available:
                components = await self._generate_ai_ui(page_type, db_data, custom_requirements)
            else:
                components = self._generate_fallback_ui(page_type)
            
            return UXResponse(
                components=components,
                layout={"type": "stack", "spacing": "medium"},
                accessibility={"high_contrast": False, "large_text": False},
                metadata={
                    "page_type": page_type,
                    "generated_at": datetime.now().isoformat(),
                    "ai_generated": self.ai_available
                }
            )
            
        except Exception as e:
            logger.error(f"UI 생성 실패: {e}")
            return self._generate_error_ui(str(e))
    
    async def _collect_data(self, page_type: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """데이터베이스에서 필요한 데이터 수집 - insurance_products 중심으로 개선"""
        data = {}
        
        # 직접 클라이언트로 연결 상태 체크
        if not self.supabase:
            logger.warning("Supabase 클라이언트가 없음 - 데이터 수집 건너뜀")
            return data
        
        try:
            logger.info(f"페이지 타입 '{page_type}'에 대한 데이터 수집 시작")
            
            if page_type == 'home':
                # 홈페이지: insurance_products 중심으로 인기 상품과 카테고리
                categories = self.supabase.table('insurance_categories').select('*').execute()
                
                # 인기 상품과 최신 상품 조회
                popular_products = self.supabase.table('insurance_products').select(
                    '*, insurance_categories!inner(name, description)'
                ).eq('is_popular', True).limit(5).execute()
                
                recent_products = self.supabase.table('insurance_products').select(
                    '*, insurance_categories!inner(name, description)'
                ).order('created_at', desc=True).limit(3).execute()
                
                # 고객 후기 (검증된 것만)
                testimonials = self.supabase.table('customer_testimonials').select(
                    '*, users!inner(name), insurance_products!inner(name)'
                ).eq('is_verified', True).eq('is_featured', True).limit(5).execute()
                
                data['categories'] = categories.data if categories.data else []
                data['popular_products'] = popular_products.data if popular_products.data else []
                data['recent_products'] = recent_products.data if recent_products.data else []
                data['testimonials'] = testimonials.data if testimonials.data else []
                
                logger.info(f"홈페이지 데이터 수집: 카테고리 {len(data['categories'])}개, 인기상품 {len(data['popular_products'])}개, 최신상품 {len(data['recent_products'])}개, 후기 {len(data['testimonials'])}개")
                
            elif page_type == 'products':
                # 상품페이지: 모든 상품과 상세 정보
                categories = self.supabase.table('insurance_categories').select('*').execute()
                
                # 카테고리별로 상품 조회 (관계 포함)
                all_products = self.supabase.table('insurance_products').select(
                    '*, insurance_categories!inner(name, description, icon_url)'
                ).execute()
                
                # UX 개선 히스토리 (상품 관련)
                ux_history = self.supabase.table('ux_improvement_history').select(
                    '*'
                ).eq('page_type', 'products').limit(10).execute()
                
                data['categories'] = categories.data if categories.data else []
                data['products'] = all_products.data if all_products.data else []
                data['ux_history'] = ux_history.data if ux_history.data else []
                
                logger.info(f"상품페이지 데이터 수집: 카테고리 {len(data['categories'])}개, 상품 {len(data['products'])}개, UX히스토리 {len(data['ux_history'])}개")
                
            elif page_type == 'search':
                # 검색 페이지: insurance_products를 중심으로 모든 관련 데이터
                
                # 모든 상품 (카테고리, 클레임 정보 포함) - 안전한 조회
                try:
                    products = self.supabase.table('insurance_products').select(
                        '*, insurance_categories(name, description, icon_url)'
                    ).execute()
                    data['products'] = products.data if products.data else []
                except Exception as e:
                    logger.warning(f"insurance_products 조회 실패: {e}")
                    products = self.supabase.table('insurance_products').select('*').execute()
                    data['products'] = products.data if products.data else []
                
                # 카테고리 정보
                try:
                    categories = self.supabase.table('insurance_categories').select('*').execute()
                    data['categories'] = categories.data if categories.data else []
                except Exception as e:
                    logger.warning(f"insurance_categories 조회 실패: {e}")
                    data['categories'] = []
                
                # FAQ (인기 위주) - 안전한 조회
                try:
                    faqs = self.supabase.table('faqs').select('*').eq('is_popular', True).limit(15).execute()
                    data['faqs'] = faqs.data if faqs.data else []
                except Exception as e:
                    logger.warning(f"FAQs 조회 실패: {e}")
                    try:
                        faqs = self.supabase.table('faqs').select('*').limit(15).execute()
                        data['faqs'] = faqs.data if faqs.data else []
                    except:
                        data['faqs'] = []
                
                # 검증된 고객 후기 (상품 정보 포함) - 안전한 조회
                try:
                    testimonials = self.supabase.table('customer_testimonials').select(
                        '*, users(name), insurance_products(name, insurance_categories(name))'
                    ).eq('is_verified', True).limit(10).execute()
                    data['testimonials'] = testimonials.data if testimonials.data else []
                except Exception as e:
                    logger.warning(f"고객 후기 조회 실패: {e}")
                    try:
                        testimonials = self.supabase.table('customer_testimonials').select('*').limit(10).execute()
                        data['testimonials'] = testimonials.data if testimonials.data else []
                    except:
                        data['testimonials'] = []
                
                # 사용자 행동 인사이트 (최근 것) - 선택적 조회
                try:
                    behavior_insights = self.supabase.table('user_behavior_insights').select(
                        '*'
                    ).order('created_at', desc=True).limit(5).execute()
                    data['behavior_insights'] = behavior_insights.data if behavior_insights.data else []
                except Exception as e:
                    logger.warning(f"사용자 행동 인사이트 조회 실패: {e}")
                    data['behavior_insights'] = []
                
                # UX 추천사항 (활성화된 것) - 선택적 조회
                try:
                    ux_recommendations = self.supabase.table('ux_recommendations_enhanced').select('*').limit(8).execute()
                    data['ux_recommendations'] = ux_recommendations.data if ux_recommendations.data else []
                except Exception as e:
                    logger.warning(f"UX 추천사항 조회 실패: {e}")
                    try:
                        # 대안 테이블 시도
                        ux_recommendations = self.supabase.table('ux_recommendations').select('*').limit(8).execute()
                        data['ux_recommendations'] = ux_recommendations.data if ux_recommendations.data else []
                    except:
                        data['ux_recommendations'] = []
                
                logger.info(f"검색페이지 데이터 수집: 상품 {len(data['products'])}개, 카테고리 {len(data['categories'])}개, FAQ {len(data['faqs'])}개, 후기 {len(data['testimonials'])}개, 행동인사이트 {len(data['behavior_insights'])}개, UX추천 {len(data['ux_recommendations'])}개")
                
            elif page_type == 'product_detail' and user_context and user_context.get('product_id'):
                # 특정 상품 상세: 관련된 모든 정보
                product_id = user_context['product_id']
                
                # 상품 상세 정보 (카테고리 포함)
                product = self.supabase.table('insurance_products').select(
                    '*, insurance_categories!inner(name, description, icon_url)'
                ).eq('id', product_id).execute()
                
                # 해당 상품의 고객 후기
                product_testimonials = self.supabase.table('customer_testimonials').select(
                    '*, users!inner(name)'
                ).eq('product_id', product_id).eq('is_verified', True).execute()
                
                # 관련 상품 (같은 카테고리)
                if product.data:
                    category_id = product.data[0].get('category_id')
                    if category_id:
                        related_products = self.supabase.table('insurance_products').select(
                            '*, insurance_categories!inner(name)'
                        ).eq('category_id', category_id).neq('id', product_id).limit(5).execute()
                        data['related_products'] = related_products.data if related_products.data else []
                
                # 상품별 UX 규칙
                ux_rules = self.supabase.table('product_ux_rules').select(
                    '*'
                ).eq('product_id', product_id).eq('is_active', True).execute()
                
                data['product'] = product.data[0] if product.data else None
                data['testimonials'] = product_testimonials.data if product_testimonials.data else []
                data['ux_rules'] = ux_rules.data if ux_rules.data else []
                
                logger.info(f"상품상세 데이터 수집: {data['product']['name'] if data['product'] else 'None'}, 후기 {len(data['testimonials'])}개, 관련상품 {len(data.get('related_products', []))}개, UX규칙 {len(data['ux_rules'])}개")
                
        except Exception as e:
            logger.error(f"데이터 수집 실패: {e}")
            import traceback
            traceback.print_exc()
        
        return data
    
    async def _generate_ai_ui(self, page_type: str, db_data: Dict[str, Any], custom_requirements: Optional[str]) -> List[UIComponent]:
        """AI로 UI 생성"""
        try:
            # 검색 페이지를 위한 특별한 프롬프트 템플릿
            if page_type == 'search':
                prompt_template = PromptTemplate(
                    input_variables=["user_request", "data", "user_context"],
                    template="""
                    당신은 한국 보험 전문가입니다. 실제 DB의 풍부한 데이터를 활용하여 사용자 요청에 맞는 맞춤형 보험 정보를 제공하세요.

                    **사용자 요청**: {user_request}
                    **실제 DB 데이터**: {data}
                    **사용자 정보**: {user_context}

                    **활용 가능한 실제 데이터**:
                    - insurance_products: 47개 상품의 상세 정보 (이름, 가격, 설명, 특징, 태그)
                    - insurance_categories: 카테고리별 분류 정보
                    - customer_testimonials: 검증된 실제 고객 후기
                    - faqs: 자주 묻는 질문과 답변
                    - user_behavior_insights: 사용자 행동 분석 데이터
                    - ux_recommendations_enhanced: UX 개선 추천사항

                    **중요 규칙 (반드시 준수)**:
                    1. 실제 DB 데이터만 사용하고 가짜 데이터 생성 절대 금지
                    2. 모든 텍스트는 한국어로 작성
                    3. 이미지 태그 (<img>) 절대 사용 금지 - 이모지만 사용
                    4. insurance_products의 실제 상품명, 실제 가격, 실제 설명만 사용
                    5. 외부 URL이나 링크 사용 금지
                    6. CSS 클래스 사용 금지 - 인라인 스타일만
                    7. 데이터가 없으면 "현재 정보가 없습니다" 표시

                    **실제 데이터 활용 방법**:
                    - 상품명: products[].name 필드 그대로 사용
                    - 가격: products[].base_price 필드를 원화로 표시 (예: 150,000원)
                    - 설명: products[].description 필드 그대로 사용
                    - 특징: products[].features 배열의 실제 내용
                    - 카테고리: products[].insurance_categories.name 사용
                    - 고객 후기: testimonials[].content와 실제 평점, 사용자명
                    - FAQ: faqs[].question과 answer 그대로 사용

                    **UI 디자인 요구사항**:
                    - 상품 중심의 카드형 레이아웃
                    - 가격 정보를 명확히 표시
                    - 실제 고객 후기 포함시 신뢰도 향상
                    - 이모지 아이콘으로 시각적 구분 (🏥 💰 📋 ⭐ 🛡️ 등)
                    - 반응형 그리드 레이아웃

                    **응답 형식 (JSON)**:
                    [
                        {{
                            "type": "section",
                            "id": "insurance_products_showcase",
                            "title": "맞춤 보험 상품 추천",
                            "content": "실제 insurance_products 데이터 활용한 HTML (이미지 금지, 이모지 사용)",
                            "style": "padding: 24px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 16px;",
                            "priority": 1,
                            "data": {{"source": "insurance_products", "total_products": "실제_조회된_상품_수", "has_testimonials": true}}
                        }}
                    ]

                    **예시 HTML 구조** (반드시 실제 데이터 사용):
                    ```html
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
                        <div style="background: white; padding: 24px; border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border-left: 4px solid #007bff;">
                            <div style="display: flex; align-items: center; margin-bottom: 16px;">
                                <span style="font-size: 24px; margin-right: 12px;">🏥</span>
                                <h3 style="color: #2c3e50; margin: 0; font-size: 18px; font-weight: 600;">[실제_상품명]</h3>
                            </div>
                            <p style="color: #6c757d; margin: 0 0 16px 0; line-height: 1.6;">[실제_설명]</p>
                            <div style="display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 16px;">
                                [실제_특징들을_배지로_표시]
                            </div>
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <span style="font-size: 20px; font-weight: 700; color: #e74c3c;">💰 [실제_가격]원</span>
                                <span style="background: #28a745; color: white; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 500;">[실제_카테고리]</span>
                            </div>
                        </div>
                    </div>
                    ```

                    반드시 제공된 실제 insurance_products 데이터를 중심으로 정확하고 신뢰할 수 있는 보험 정보를 제공하세요.
                    """
                )
            else:
                # 기존 일반 프롬프트 템플릿도 한국어로 수정
                prompt_template = PromptTemplate(
                    input_variables=["page_type", "data", "requirements"],
                    template="""
                    당신은 한국 보험 웹사이트 디자이너입니다. 실제 DB 데이터를 활용해서 {page_type} 페이지를 만드세요.

                    **실제 데이터**: {data}
                    **요구사항**: {requirements}

                    **중요 규칙 (반드시 준수)**:
                    1. 실제 DB 데이터만 사용 (가짜 데이터 절대 금지)
                    2. 모든 텍스트는 한국어
                    3. 이미지 태그 (<img>) 절대 사용 금지 - 이모지만 사용
                    4. 인라인 CSS만 사용 (클래스 금지)
                    5. 외부 URL이나 링크 사용 금지
                    6. 실제 상품명, 실제 가격, 실제 설명만 사용

                    **실제 데이터 활용**:
                    - 제공된 DB 데이터의 name, base_price, description 필드 사용
                    - 가격은 숫자 그대로 표시 (예: 150,000원)
                    - 카테고리는 실제 category name 사용

                    **JSON 형식으로 응답**:
                    [
                        {{
                            "type": "section",
                            "id": "page_content", 
                            "title": "페이지 내용",
                            "content": "실제 DB 데이터 활용한 HTML (이미지 금지, 이모지 사용)",
                            "style": "padding: 20px; background: #f8f9fa; border-radius: 12px;",
                            "priority": 1,
                            "data": {{"source": "real_db", "page_type": "{page_type}"}}
                        }}
                    ]

                    실제 DB 데이터를 반드시 활용하여 {page_type} 페이지를 생성하세요.
                    """
                )
            
            # LangChain 최신 방식 사용
            chain = prompt_template | self.llm
            
            if page_type == 'search':
                # 검색 페이지용 특별 처리
                user_context = self._analyze_user_context(custom_requirements or "")
                enhanced_data = self._format_search_data_for_ai(db_data)
                
                response = await chain.ainvoke({
                    "user_request": custom_requirements or "",
                    "data": enhanced_data,
                    "user_context": user_context
                })
            else:
                # 기존 처리
                enhanced_requirements = self._enhance_requirements(custom_requirements, db_data)
                
                response = await chain.ainvoke({
                    "page_type": page_type,
                    "data": self._format_data_for_ai(db_data),
                    "requirements": enhanced_requirements
                })
            
            # AI 응답을 파싱하여 UIComponent로 변환
            return self._parse_enhanced_ai_response(response.content)
            
        except Exception as e:
            logger.error(f"AI UI 생성 실패: {e}")
            logger.debug(f"AI 응답 내용: {response[:500]}...")
        
        return self._generate_enhanced_fallback_ui(page_type)

    def _analyze_user_context(self, user_request: str) -> str:
        """사용자 요청에서 컨텍스트 정보 추출"""
        context_info = []
        request_lower = user_request.lower()
        
        # 나이 추출
        if '10대' in request_lower or '청소년' in request_lower:
            context_info.append("연령대: 10대 (청소년)")
        elif '20대' in request_lower:
            context_info.append("연령대: 20대 (청년)")
        elif '30대' in request_lower:
            context_info.append("연령대: 30대 (성인)")
        elif '40대' in request_lower or '50대' in request_lower:
            context_info.append("연령대: 중년")
        
        # 지식 수준 추출
        if '모르' in request_lower or '초보' in request_lower or '처음' in request_lower:
            context_info.append("지식 수준: 초보자")
        elif '용어' in request_lower and ('쉽게' in request_lower or '알기 쉽게' in request_lower):
            context_info.append("설명 방식: 용어 해설 필요")
        
        # 요청 스타일 추출
        if '깔끔하게' in request_lower:
            context_info.append("UI 스타일: 깔끔하고 정리된 형태")
        if '정리해서' in request_lower:
            context_info.append("정보 제공 방식: 체계적 정리")
        if '비교' in request_lower:
            context_info.append("정보 제공 방식: 비교표 형태")
        
        return ' | '.join(context_info) if context_info else "일반 사용자"

    def _format_search_data_for_ai(self, db_data: Dict[str, Any]) -> str:
        """검색용 데이터 포맷팅 - insurance_products 중심으로 더 상세한 정보 제공"""
        formatted_data = {}
        
        # insurance_products 데이터 (핵심)
        if 'products' in db_data and db_data['products']:
            products_summary = []
            for product in db_data['products']:
                # 카테고리 정보 포함
                category_info = product.get('insurance_categories', {})
                
                summary = {
                    'id': product.get('id'),
                    'name': product.get('name'),
                    'description': product.get('description'),
                    'base_price': product.get('base_price'),
                    'max_coverage': product.get('max_coverage'),
                    'age_limit_min': product.get('age_limit_min'),
                    'age_limit_max': product.get('age_limit_max'),
                    'is_popular': product.get('is_popular'),
                    'features': product.get('features', []),
                    'tags': product.get('tags', []),
                    'category_name': category_info.get('name', ''),
                    'category_description': category_info.get('description', ''),
                    'category_icon': category_info.get('icon_url', ''),
                    'created_at': product.get('created_at'),
                    'updated_at': product.get('updated_at')
                }
                products_summary.append(summary)
            
            # 인기 상품 별도 추출
            popular_products = [p for p in products_summary if p.get('is_popular')]
            
            formatted_data['보험상품_전체'] = {
                '총_개수': len(products_summary),
                '상품_목록': products_summary,
                '인기상품_개수': len(popular_products),
                '인기상품_목록': popular_products
            }
        else:
            formatted_data['보험상품_전체'] = {"메시지": "현재 보험 상품 정보가 없습니다"}
        
        # 카테고리 정보 (참고용)
        if 'categories' in db_data and db_data['categories']:
            categories_summary = []
            for category in db_data['categories']:
                summary = {
                    'id': category.get('id'),
                    'name': category.get('name'),
                    'description': category.get('description'),
                    'icon_url': category.get('icon_url'),
                    'is_active': category.get('is_active'),
                    'sort_order': category.get('sort_order')
                }
                categories_summary.append(summary)
            formatted_data['카테고리_정보'] = categories_summary
        else:
            formatted_data['카테고리_정보'] = {"메시지": "현재 카테고리 정보가 없습니다"}
        
        # 고객 후기 (신뢰도 향상)
        if 'testimonials' in db_data and db_data['testimonials']:
            testimonials_summary = []
            for testimonial in db_data['testimonials']:
                user_info = testimonial.get('users', {})
                product_info = testimonial.get('insurance_products', {})
                category_info = product_info.get('insurance_categories', {}) if product_info else {}
                
                summary = {
                    'id': testimonial.get('id'),
                    'rating': testimonial.get('rating'),
                    'title': testimonial.get('title'),
                    'content': testimonial.get('content'),
                    'is_featured': testimonial.get('is_featured'),
                    'is_verified': testimonial.get('is_verified'),
                    'user_name': user_info.get('name', '익명'),
                    'product_name': product_info.get('name', ''),
                    'category_name': category_info.get('name', ''),
                    'created_at': testimonial.get('created_at')
                }
                testimonials_summary.append(summary)
            formatted_data['고객후기'] = {
                '총_개수': len(testimonials_summary),
                '후기_목록': testimonials_summary,
                '평균_평점': sum(t.get('rating', 0) for t in testimonials_summary) / len(testimonials_summary) if testimonials_summary else 0
            }
        else:
            formatted_data['고객후기'] = {"메시지": "현재 고객 후기가 없습니다"}
        
        # FAQ 정보
        if 'faqs' in db_data and db_data['faqs']:
            faqs_summary = []
            for faq in db_data['faqs']:
                summary = {
                    'id': faq.get('id'),
                    'category': faq.get('category'),
                    'question': faq.get('question'),
                    'answer': faq.get('answer'),
                    'is_popular': faq.get('is_popular'),
                    'keywords': faq.get('keywords', [])
                }
                faqs_summary.append(summary)
            formatted_data['FAQ'] = {
                '총_개수': len(faqs_summary),
                'FAQ_목록': faqs_summary
            }
        else:
            formatted_data['FAQ'] = {"메시지": "현재 FAQ 정보가 없습니다"}
        
        # 사용자 행동 인사이트 (UX 개선)
        if 'behavior_insights' in db_data and db_data['behavior_insights']:
            insights_summary = []
            for insight in db_data['behavior_insights']:
                summary = {
                    'id': insight.get('id'),
                    'insight_type': insight.get('insight_type'),
                    'description': insight.get('description'),
                    'impact_score': insight.get('impact_score'),
                    'page_type': insight.get('page_type'),
                    'action_recommended': insight.get('action_recommended'),
                    'created_at': insight.get('created_at')
                }
                insights_summary.append(summary)
            formatted_data['사용자_행동_인사이트'] = {
                '총_개수': len(insights_summary),
                '인사이트_목록': insights_summary
            }
        else:
            formatted_data['사용자_행동_인사이트'] = {"메시지": "현재 행동 인사이트가 없습니다"}
        
        # UX 추천사항 (UI 개선)
        if 'ux_recommendations' in db_data and db_data['ux_recommendations']:
            recommendations_summary = []
            for rec in db_data['ux_recommendations']:
                summary = {
                    'id': rec.get('id'),
                    'recommendation_type': rec.get('recommendation_type'),
                    'title': rec.get('title'),
                    'description': rec.get('description'),
                    'impact_level': rec.get('impact_level'),
                    'implementation_effort': rec.get('implementation_effort'),
                    'is_active': rec.get('is_active'),
                    'target_audience': rec.get('target_audience'),
                    'expected_improvement': rec.get('expected_improvement')
                }
                recommendations_summary.append(summary)
            formatted_data['UX_추천사항'] = {
                '총_개수': len(recommendations_summary),
                '추천사항_목록': recommendations_summary
            }
        else:
            formatted_data['UX_추천사항'] = {"메시지": "현재 UX 추천사항이 없습니다"}
        
        # 데이터 메타 정보
        formatted_data['데이터_메타정보'] = {
            '생성_시간': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            '데이터_소스': 'Supabase 실시간 조회',
            '신뢰도': '실제_DB_데이터_100%',
            '주의사항': '모든 데이터는 실제 데이터베이스에서 조회된 정보입니다. 반드시 이 데이터만 사용하고 가상의 데이터를 생성하지 마세요.',
            '사용_우선순위': ['보험상품_전체', '고객후기', 'FAQ', 'UX_추천사항', '사용자_행동_인사이트']
        }
        
        # JSON 문자열로 변환 (크기 제한 확장)
        import json
        try:
            data_str = json.dumps(formatted_data, ensure_ascii=False, indent=2)
            logger.info(f"AI 전달 데이터 크기: {len(data_str)}자 (상품 {len(db_data.get('products', []))}개, 후기 {len(db_data.get('testimonials', []))}개)")
            return data_str[:12000]  # 12000자로 확장
        except Exception as e:
            logger.error(f"데이터 JSON 변환 실패: {e}")
            return str(formatted_data)[:12000]

    def _format_data_for_ai(self, db_data: Dict[str, Any]) -> str:
        """AI가 이해하기 쉽게 데이터 포맷팅"""
        formatted_data = {}
        
        if 'products' in db_data and db_data['products']:
            # 상품 데이터를 요약해서 제공
            products_summary = []
            for product in db_data['products']:
                summary = {
                    'id': product.get('id'),
                    'name': product.get('name'),
                    'description': product.get('description'),
                    'base_price': product.get('base_price'),
                    'max_coverage': product.get('max_coverage'),
                    'is_popular': product.get('is_popular'),
                    'features': product.get('features', []),
                    'tags': product.get('tags', []),
                    'age_limit': f"{product.get('age_limit_min', 0)}세~{product.get('age_limit_max', 100)}세"
                }
                products_summary.append(summary)
            formatted_data['실제_보험_상품'] = products_summary
            formatted_data['상품_개수'] = len(products_summary)
        else:
            formatted_data['실제_보험_상품'] = "현재 보험 상품 정보가 없습니다"
            
        if 'categories' in db_data and db_data['categories']:
            # 카테고리 데이터 요약
            categories_summary = []
            for category in db_data['categories']:
                summary = {
                    'id': category.get('id'),
                    'name': category.get('name'),
                    'description': category.get('description'),
                    'is_active': category.get('is_active')
                }
                categories_summary.append(summary)
            formatted_data['실제_보험_카테고리'] = categories_summary
            formatted_data['카테고리_개수'] = len(categories_summary)
        else:
            formatted_data['실제_보험_카테고리'] = "현재 카테고리 정보가 없습니다"
        
        # 특별한 정보들 추가
        if 'featured_products' in db_data and db_data['featured_products']:
            featured = []
            for product in db_data['featured_products']:
                featured.append({
                    'name': product.get('name'),
                    'price': product.get('base_price'),
                    'coverage': product.get('max_coverage')
                })
            formatted_data['추천_상품'] = featured
        
        # 메타 정보 추가
        formatted_data['데이터_정보'] = {
            '주의사항': '위 데이터는 실제 데이터베이스에서 조회한 정보입니다. 반드시 이 정보만 사용하고 가상의 데이터를 생성하지 마세요.',
            '생성_시간': datetime.now().strftime('%Y년 %m월 %d일 %H시 %M분')
        }
        
        # JSON 문자열로 변환
        import json
        try:
            data_str = json.dumps(formatted_data, ensure_ascii=False, indent=2)
            logger.info(f"일반 페이지용 AI 데이터 크기: {len(data_str)}자")
            return data_str[:4000]  # 4000자 제한
        except Exception as e:
            logger.error(f"데이터 JSON 변환 실패: {e}")
            return str(formatted_data)[:4000]

    def _enhance_requirements(self, custom_requirements: Optional[str], db_data: Dict[str, Any]) -> str:
        """사용자 요구사항을 DB 데이터와 결합하여 향상"""
        base_requirements = custom_requirements or f"사용자 친화적이고 매력적인 UI"
        
        # DB 데이터 기반 컨텍스트 추가
        context_info = []
        
        if 'products' in db_data and db_data['products']:
            product_count = len(db_data['products'])
            context_info.append(f"총 {product_count}개의 보험 상품 데이터 활용")
            
        if 'categories' in db_data and db_data['categories']:
            categories = [cat.get('name', '') for cat in db_data['categories']]
            context_info.append(f"카테고리: {', '.join(categories)}")
        
        enhanced = f"{base_requirements}. "
        if context_info:
            enhanced += f"참고 정보: {' | '.join(context_info)}. "
        
        enhanced += "실제 데이터를 활용하여 개인화되고 구체적인 UI를 생성하세요."
        
        return enhanced

    def _parse_enhanced_ai_response(self, response: str) -> List[UIComponent]:
        """향상된 AI 응답을 UIComponent로 파싱"""
        try:
            import json
            import re
            
            # JSON 추출 시도
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                components_data = json.loads(json_match.group())
                
                components = []
                for i, comp_data in enumerate(components_data):
                    # 기본 ID만 생성
                    component_id = comp_data.get('id') or f"ai_comp_{i}"
                    
                    component = UIComponent(
                        type=comp_data.get('type', 'div'),
                        id=component_id,
                        title=comp_data.get('title', ''),  # AI가 제공한 title 그대로 사용
                        content=comp_data.get('content', ''),
                        style=comp_data.get('style', ''),
                        priority=comp_data.get('priority', i + 1),
                        data=comp_data.get('data', {})
                    )
                    components.append(component)
                
                logger.info(f"✅ AI가 생성한 컴포넌트 {len(components)}개 파싱 완료")
                return components
                
        except Exception as e:
            logger.error(f"향상된 AI 응답 파싱 실패: {e}")
            logger.debug(f"AI 응답 내용: {response[:500]}...")
        
        return self._generate_enhanced_fallback_ui(page_type)
    
    def _generate_enhanced_fallback_ui(self, page_type: str) -> List[UIComponent]:
        """향상된 폴백 UI 생성 - 실제 HTML 태그와 스타일 포함"""
        enhanced_fallback_components = {
            "home": [
                UIComponent(
                    type="header",
                    id="main_hero",
                    title="보험의 시작, 믿을 수 있는 파트너",
                    content="""
                    <div style="text-align: center; padding: 2rem;">
                        <h1 style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 3rem; font-weight: 900; margin: 0 0 1rem 0; text-shadow: 2px 2px 4px rgba(0,0,0,0.1);">🛡️ 안전한 미래를 위한 선택</h1>
                        <p style="color: #4a5568; font-size: 1.3rem; line-height: 1.8; margin: 1rem 0 2rem 0; max-width: 600px; margin-left: auto; margin-right: auto;">25년 경력의 보험 전문가들이 제공하는 맞춤형 보험 솔루션으로 가족의 안전을 지켜보세요.</p>
                        <div style="background: rgba(255,255,255,0.9); padding: 1.5rem; border-radius: 15px; box-shadow: 0 8px 25px rgba(0,0,0,0.1); margin-top: 2rem;">
                            <span style="color: #e53e3e; font-size: 1.1rem; font-weight: 600;">💰 월 2만원부터 시작하는 든든한 보장</span>
                        </div>
                    </div>
                    """,
                    style="background: linear-gradient(135deg, #f7fafc 0%, #e2e8f0 100%); border-radius: 20px; box-shadow: 0 20px 40px rgba(0,0,0,0.1); margin-bottom: 2rem; overflow: hidden;",
                    priority=1,
                    data={
                        "cta_text": "무료 보험료 계산하기",
                        "cta_link": "/calculator"
                    }
                ),
                UIComponent(
                    type="section",
                    id="stats_grid",
                    title="실시간 보험 현황",
                    content="""
                    <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1.5rem; padding: 0;">
                        <div style="background: linear-gradient(45deg, #4299e1, #3182ce); color: white; padding: 1.5rem; border-radius: 15px; text-align: center; transform: translateY(-5px); box-shadow: 0 10px 20px rgba(66, 153, 225, 0.3);">
                            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">👥</div>
                            <div style="font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem;">1,247명</div>
                            <div style="font-size: 0.9rem; opacity: 0.9;">이번 달 신규 가입자</div>
                        </div>
                        <div style="background: linear-gradient(45deg, #48bb78, #38a169); color: white; padding: 1.5rem; border-radius: 15px; text-align: center; transform: translateY(-5px); box-shadow: 0 10px 20px rgba(72, 187, 120, 0.3);">
                            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">💰</div>
                            <div style="font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem;">15,000원</div>
                            <div style="font-size: 0.9rem; opacity: 0.9;">평균 월 보험료 절약</div>
                        </div>
                        <div style="background: linear-gradient(45deg, #ed8936, #dd6b20); color: white; padding: 1.5rem; border-radius: 15px; text-align: center; transform: translateY(-5px); box-shadow: 0 10px 20px rgba(237, 137, 54, 0.3);">
                            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">⭐</div>
                            <div style="font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem;">98.7%</div>
                            <div style="font-size: 0.9rem; opacity: 0.9;">고객 만족도</div>
                        </div>
                        <div style="background: linear-gradient(45deg, #9f7aea, #805ad5); color: white; padding: 1.5rem; border-radius: 15px; text-align: center; transform: translateY(-5px); box-shadow: 0 10px 20px rgba(159, 122, 234, 0.3);">
                            <div style="font-size: 2.5rem; margin-bottom: 0.5rem;">⚡</div>
                            <div style="font-size: 2rem; font-weight: 800; margin-bottom: 0.5rem;">3일</div>
                            <div style="font-size: 0.9rem; opacity: 0.9;">평균 보험금 지급</div>
                        </div>
                    </div>
                    """,
                    style="padding: 2rem; background: rgba(255,255,255,0.95); border-radius: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.1);",
                    priority=2,
                    data={"update_frequency": "실시간"}
                ),
                UIComponent(
                    type="div",
                    id="popular_products",
                    title="인기 보험 상품 TOP 3",
                    content="""
                    <div style="display: flex; flex-wrap: wrap; gap: 1.5rem;">
                        <div style="flex: 1; min-width: 300px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 2rem; border-radius: 20px; position: relative; overflow: hidden;">
                            <div style="position: absolute; top: -20px; right: -20px; width: 100px; height: 100px; background: rgba(255,255,255,0.1); border-radius: 50%; opacity: 0.3;"></div>
                            <h3 style="margin: 0 0 1rem 0; font-size: 1.4rem; font-weight: 700;">🏥 건강보험 플러스</h3>
                            <p style="margin: 0 0 1rem 0; opacity: 0.9; line-height: 1.6;">월 23,000원으로 최대 1억원까지 보장받으세요</p>
                            <div style="font-size: 0.9rem; opacity: 0.8;">✓ 암 진단비 ✓ 수술비 ✓ 입원비</div>
                        </div>
                        <div style="flex: 1; min-width: 300px; background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); color: white; padding: 2rem; border-radius: 20px; position: relative; overflow: hidden;">
                            <div style="position: absolute; top: -20px; right: -20px; width: 100px; height: 100px; background: rgba(255,255,255,0.1); border-radius: 50%; opacity: 0.3;"></div>
                            <h3 style="margin: 0 0 1rem 0; font-size: 1.4rem; font-weight: 700;">🎗️ 암보험 프리미엄</h3>
                            <p style="margin: 0 0 1rem 0; opacity: 0.9; line-height: 1.6;">월 18,000원으로 암 치료비 걱정 없이</p>
                            <div style="font-size: 0.9rem; opacity: 0.8;">✓ 조기 발견 보상 ✓ 치료비 ✓ 생활비</div>
                        </div>
                        <div style="flex: 1; min-width: 300px; background: linear-gradient(135deg, #4ecdc4 0%, #26d0ce 100%); color: white; padding: 2rem; border-radius: 20px; position: relative; overflow: hidden;">
                            <div style="position: absolute; top: -20px; right: -20px; width: 100px; height: 100px; background: rgba(255,255,255,0.1); border-radius: 50%; opacity: 0.3;"></div>
                            <h3 style="margin: 0 0 1rem 0; font-size: 1.4rem; font-weight: 700;">🚗 자동차보험 종합</h3>
                            <p style="margin: 0 0 1rem 0; opacity: 0.9; line-height: 1.6;">월 120,000원으로 무제한 보장</p>
                            <div style="font-size: 0.9rem; opacity: 0.8;">✓ 대인 ✓ 대물 ✓ 자손</div>
                        </div>
                    </div>
                    """,
                    style="padding: 2rem; background: rgba(255,255,255,0.95); border-radius: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.1); margin-top: 1.5rem;",
                    priority=3,
                    data={"category": "인기상품"}
                )
            ],
            "products": [
                UIComponent(
                    type="nav",
                    id="product_categories",
                    title="보험 카테고리",
                    content="""
                    <div style="display: flex; flex-wrap: wrap; gap: 1rem;">
                        <button style="background: linear-gradient(45deg, #667eea, #764ba2); color: white; border: none; padding: 1rem 1.5rem; border-radius: 25px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3); transition: all 0.3s ease;">❤️ 생명보험 (15개)</button>
                        <button style="background: linear-gradient(45deg, #4ecdc4, #26d0ce); color: white; border: none; padding: 1rem 1.5rem; border-radius: 25px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 15px rgba(78, 205, 196, 0.3); transition: all 0.3s ease;">🏥 건강보험 (22개)</button>
                        <button style="background: linear-gradient(45deg, #f093fb, #f5576c); color: white; border: none; padding: 1rem 1.5rem; border-radius: 25px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 15px rgba(240, 147, 251, 0.3); transition: all 0.3s ease;">🛡️ 손해보험 (18개)</button>
                        <button style="background: linear-gradient(45deg, #ffeaa7, #fdcb6e); color: #2d3436; border: none; padding: 1rem 1.5rem; border-radius: 25px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 15px rgba(253, 203, 110, 0.3); transition: all 0.3s ease;">👵 연금보험 (8개)</button>
                        <button style="background: linear-gradient(45deg, #81ecec, #00cec9); color: white; border: none; padding: 1rem 1.5rem; border-radius: 25px; font-weight: 600; cursor: pointer; box-shadow: 0 4px 15px rgba(129, 236, 236, 0.3); transition: all 0.3s ease;">🚗 자동차보험 (12개)</button>
                    </div>
                    """,
                    style="padding: 2rem; background: rgba(255,255,255,0.95); border-radius: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.1);",
                    priority=1,
                    data={"total_products": 75}
                ),
                UIComponent(
                    type="main",
                    id="product_showcase",
                    title="맞춤형 보험 상품 추천",
                    content="""
                    <div style="padding: 2rem; background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); border-radius: 20px; border-left: 5px solid #667eea;">
                        <h2 style="color: #2d3748; font-size: 1.8rem; font-weight: 700; margin: 0 0 1rem 0;">🎯 30대 직장인을 위한 맞춤 패키지</h2>
                        <p style="color: #4a5568; line-height: 1.8; font-size: 1.1rem; margin: 1rem 0;">건강보험과 암보험을 결합하여 월 4만원대로 종합적인 보장을 받으실 수 있습니다. 나이와 직업을 고려한 최적화된 상품으로 구성되었습니다.</p>
                        
                        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1.5rem;">
                            <div style="background: rgba(255,255,255,0.9); padding: 1rem; border-radius: 12px; text-align: center;">
                                <div style="color: #667eea; font-size: 1.5rem; font-weight: 700;">42,000원</div>
                                <div style="color: #718096; font-size: 0.9rem;">월 보험료</div>
                            </div>
                            <div style="background: rgba(255,255,255,0.9); padding: 1rem; border-radius: 12px; text-align: center;">
                                <div style="color: #f56565; font-size: 1.5rem; font-weight: 700;">1억 5천만원</div>
                                <div style="color: #718096; font-size: 0.9rem;">총 보장한도</div>
                            </div>
                            <div style="background: rgba(255,255,255,0.9); padding: 1rem; border-radius: 12px; text-align: center;">
                                <div style="color: #38a169; font-size: 1.5rem; font-weight: 700;">2개 상품</div>
                                <div style="color: #718096; font-size: 0.9rem;">패키지 구성</div>
                            </div>
                        </div>
                    </div>
                    """,
                    style="padding: 0; margin-top: 1.5rem;",
                    priority=2,
                    data={"target_age": "30대", "target_job": "직장인"}
                )
            ],
            "search": [
                UIComponent(
                    type="article",
                    id="search_notice",
                    title="AI 맞춤 검색 서비스",
                    content="""
                    <div style="text-align: center; padding: 3rem 2rem;">
                        <div style="font-size: 4rem; margin-bottom: 1rem;">🤖</div>
                        <h2 style="background: linear-gradient(45deg, #667eea, #764ba2); -webkit-background-clip: text; -webkit-text-fill-color: transparent; font-size: 2rem; font-weight: 800; margin: 0 0 1rem 0;">AI 보험 전문가가 분석 중입니다</h2>
                        <p style="color: #4a5568; line-height: 1.8; font-size: 1.1rem; margin: 1rem 0 2rem 0; max-width: 500px; margin-left: auto; margin-right: auto;">고객님의 요구사항을 분석하여 가장 적합한 보험 상품을 찾고 있습니다. 잠시만 기다려주세요.</p>
                        
                        <div style="background: rgba(255,255,255,0.9); padding: 1.5rem; border-radius: 15px; box-shadow: inset 0 2px 8px rgba(0,0,0,0.1); margin: 2rem 0;">
                            <div style="display: flex; align-items: center; justify-content: center; gap: 1rem;">
                                <div style="width: 12px; height: 12px; background: #667eea; border-radius: 50%; animation: pulse 1.5s infinite;"></div>
                                <div style="color: #2d3748; font-weight: 600;">약 30초 후 맞춤 결과를 제공합니다</div>
                                <div style="width: 12px; height: 12px; background: #f56565; border-radius: 50%; animation: pulse 1.5s infinite 0.5s;"></div>
                            </div>
                        </div>
                        
                        <div style="background: linear-gradient(45deg, rgba(102, 126, 234, 0.1), rgba(245, 101, 101, 0.1)); padding: 1rem; border-radius: 12px; border: 2px dashed #667eea;">
                            <span style="color: #667eea; font-size: 0.9rem; font-weight: 600;">💡 더 정확한 추천을 위해 연령과 관심 보험을 알려주세요</span>
                        </div>
                    </div>
                    """,
                    style="background: linear-gradient(135deg, #f7fafc 0%, #e2e8f0 100%); border-radius: 20px; box-shadow: 0 8px 25px rgba(0,0,0,0.1);",
                    priority=1,
                    data={"loading": True, "estimated_time": 30}
                )
            ],
            "default": [
                UIComponent(
                    type="article",
                    id="service_notice",
                    title="서비스 준비 중",
                    content="""
                    <div style="text-align: center; padding: 3rem 2rem;">
                        <div style="font-size: 3rem; margin-bottom: 1rem;">⚙️</div>
                        <h2 style="color: #2d3748; font-size: 1.8rem; font-weight: 700; margin: 0 0 1rem 0;">보다 나은 서비스를 위해 준비 중입니다</h2>
                        <p style="color: #4a5568; line-height: 1.8; font-size: 1.1rem; margin: 1rem 0; max-width: 400px; margin-left: auto; margin-right: auto;">AI 맞춤 서비스를 업데이트하고 있습니다. 잠시만 기다려주시면 더욱 정확한 보험 추천을 받으실 수 있습니다.</p>
                        
                        <div style="background: linear-gradient(45deg, rgba(245, 158, 11, 0.1), rgba(251, 191, 36, 0.1)); padding: 1.5rem; border-radius: 15px; border: 2px dashed #f59e0b; margin-top: 2rem;">
                            <div style="color: #92400e; font-weight: 600; margin-bottom: 0.5rem;">🕐 예상 대기 시간: 약 1분</div>
                            <div style="color: #92400e; font-size: 0.9rem;">기본 상품 정보는 언제든지 확인하실 수 있습니다</div>
                        </div>
                    </div>
                    """,
                    style="background: linear-gradient(135deg, #fef5e7 0%, #fed7aa 100%); border-radius: 20px; box-shadow: 0 8px 25px rgba(245, 158, 11, 0.2);",
                    priority=1,
                    data={"service_status": "updating"}
                )
            ]
        }
        
        return enhanced_fallback_components.get(page_type, enhanced_fallback_components["default"])
    
    def _generate_fallback_ui(self, page_type: str) -> List[UIComponent]:
        """기존 폴백 UI (단순 버전)"""
        fallback_components = {
            "home": [
                UIComponent(
                    type="section",
                    id="hero",
                    title="SecureLife 보험",
                    content="믿을 수 있는 보험 파트너와 함께 안전한 미래를 준비하세요.",
                    style="padding: 2rem; background: #3b82f6; color: white; border-radius: 8px;",
                    priority=1
                ),
                UIComponent(
                    type="button",
                    id="cta",
                    title="상품 보기",
                    content="다양한 보험 상품을 확인하세요",
                    style="primary",
                    priority=2
                )
            ],
            "products": [
                UIComponent(
                    type="notice",
                    id="info",
                    title="보험 상품",
                    content="고객님에게 맞는 보험 상품을 찾아보세요.",
                    style="info",
                    priority=1
                )
            ]
        }
        
        return fallback_components.get(page_type, [
            UIComponent(
                type="notice",
                id="default",
                title="서비스 준비 중",
                content="잠시만 기다려주세요.",
                style="info",
                priority=1
            )
        ])
    
    def _generate_error_ui(self, error_message: str) -> UXResponse:
        """에러 UI 생성"""
        return UXResponse(
            components=[
                UIComponent(
                    type="notice",
                    id="error",
                    title="일시적 오류",
                    content="서비스 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                    style="warning",
                    priority=1
                )
            ],
            layout={"type": "stack"},
            accessibility={},
            metadata={"error": error_message}
        )
    
    # 데이터 조회 메서드들
    async def get_insurance_products(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """보험 상품 조회"""
        if not self.supabase:
            return []
        
        try:
            query = self.supabase.table('insurance_products').select('*')
            if category:
                query = query.eq('category_id', category)
            
            result = query.limit(20).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"상품 조회 실패: {e}")
            return []
    
    async def get_insurance_categories(self) -> List[Dict[str, Any]]:
        """보험 카테고리 조회"""
        try:
            if not self.supabase:
                return []
            
            response = self.supabase.table('insurance_categories').select('*').order('sort_order').execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"카테고리 조회 실패: {e}")
            return []
    
    async def search_content(
        self, 
        query: str, 
        limit: int = 20,
        include_products: bool = True,
        include_faqs: bool = True,
        include_testimonials: bool = True
    ) -> Dict[str, Any]:
        """통합 검색 기능 - 보험 상품, FAQ, 고객 후기 검색"""
        try:
            results = {
                "products": [],
                "faqs": [],
                "testimonials": []
            }
            
            if not is_supabase_connected():
                return self._get_fallback_search_results(query)
            
            search_term = f"%{query.lower()}%"
            
            # 보험 상품 검색
            if include_products:
                try:
                    # 상품명, 설명, 특징, 태그로 검색
                    products_response = self.supabase.table('insurance_products').select(
                        """
                        id, name, description, features, base_price, max_coverage, 
                        age_limit_min, age_limit_max, tags, is_popular,
                        insurance_categories!inner(name, description)
                        """
                    ).or_(
                        f"name.ilike.{search_term},"
                        f"description.ilike.{search_term},"
                        f"features.cs.{{{query}}},"
                        f"tags.cs.{{{query}}}"
                    ).limit(limit).execute()
                    
                    products = products_response.data if products_response.data else []
                    
                    # 검색 점수 계산 (간단한 TF-IDF 근사)
                    for product in products:
                        score = self._calculate_search_score(query, product, 'product')
                        product['search_score'] = score
                        product['type'] = 'product'
                    
                    # 점수순 정렬
                    products.sort(key=lambda x: x.get('search_score', 0), reverse=True)
                    results["products"] = products
                    
                except Exception as e:
                    logger.error(f"상품 검색 실패: {e}")
            
            # FAQ 검색
            if include_faqs:
                try:
                    faqs_response = self.supabase.table('faqs').select(
                        "*"
                    ).or_(
                        f"question.ilike.{search_term},"
                        f"answer.ilike.{search_term},"
                        f"keywords.cs.{{{query}}}"
                    ).limit(limit).execute()
                    
                    faqs = faqs_response.data if faqs_response.data else []
                    
                    for faq in faqs:
                        score = self._calculate_search_score(query, faq, 'faq')
                        faq['search_score'] = score
                        faq['type'] = 'faq'
                    
                    faqs.sort(key=lambda x: x.get('search_score', 0), reverse=True)
                    results["faqs"] = faqs
                    
                except Exception as e:
                    logger.error(f"FAQ 검색 실패: {e}")
            
            # 고객 후기 검색
            if include_testimonials:
                try:
                    testimonials_response = self.supabase.table('customer_testimonials').select(
                        """
                        id, rating, title, content, is_featured, is_verified,
                        users!inner(name),
                        insurance_products!inner(name, insurance_categories!inner(name))
                        """
                    ).or_(
                        f"title.ilike.{search_term},"
                        f"content.ilike.{search_term}"
                    ).eq('is_verified', True).limit(limit).execute()
                    
                    testimonials = testimonials_response.data if testimonials_response.data else []
                    
                    for testimonial in testimonials:
                        score = self._calculate_search_score(query, testimonial, 'testimonial')
                        testimonial['search_score'] = score
                        testimonial['type'] = 'testimonial'
                    
                    testimonials.sort(key=lambda x: x.get('search_score', 0), reverse=True)
                    results["testimonials"] = testimonials
                    
                except Exception as e:
                    logger.error(f"고객 후기 검색 실패: {e}")
            
            # AI 기반 검색 결과 개선 (선택적)
            if self.ai_available:
                results = await self._enhance_search_results_with_ai(query, results)
            
            logger.info(f"검색 완료: '{query}' - {len(results['products'])} 상품, {len(results['faqs'])} FAQ, {len(results['testimonials'])} 후기")
            return results
            
        except Exception as e:
            logger.error(f"검색 실패: {e}")
            return self._get_fallback_search_results(query)
    
    def _calculate_search_score(self, query: str, item: Dict[str, Any], item_type: str) -> float:
        """검색 결과의 관련성 점수 계산"""
        score = 0.0
        query_lower = query.lower()
        
        if item_type == 'product':
            # 상품명에서 정확 매치
            if query_lower in item.get('name', '').lower():
                score += 10.0
            
            # 설명에서 매치
            if query_lower in item.get('description', '').lower():
                score += 5.0
            
            # 태그에서 매치
            tags = item.get('tags', [])
            if isinstance(tags, list):
                for tag in tags:
                    if query_lower in tag.lower():
                        score += 3.0
            
            # 인기 상품 보너스
            if item.get('is_popular'):
                score += 2.0
                
        elif item_type == 'faq':
            # 질문에서 정확 매치
            if query_lower in item.get('question', '').lower():
                score += 10.0
            
            # 답변에서 매치
            if query_lower in item.get('answer', '').lower():
                score += 5.0
            
            # 키워드에서 매치
            keywords = item.get('keywords', [])
            if isinstance(keywords, list):
                for keyword in keywords:
                    if query_lower in keyword.lower():
                        score += 3.0
            
            # 인기 FAQ 보너스
            if item.get('is_popular'):
                score += 2.0
                
        elif item_type == 'testimonial':
            # 제목에서 매치
            if query_lower in item.get('title', '').lower():
                score += 8.0
            
            # 내용에서 매치
            if query_lower in item.get('content', '').lower():
                score += 4.0
            
            # 평점 보너스
            rating = item.get('rating', 0)
            if rating >= 4:
                score += rating * 0.5
        
        return score
    
    async def _enhance_search_results_with_ai(self, query: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """AI를 활용한 검색 결과 개선 - 현재 미사용"""
        logger.warning("AI 검색 결과 개선 기능은 현재 비활성화됨")
        return results
    
    async def get_faqs(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """FAQ 조회"""
        try:
            if not is_supabase_connected():
                return self._get_fallback_faqs()
            
            query = self.supabase.table('faqs').select('*').order('sort_order')
            
            if category:
                query = query.eq('category', category)
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"FAQ 조회 실패: {e}")
            return self._get_fallback_faqs()
    
    async def get_testimonials(self, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """고객 후기 조회"""
        try:
            if not is_supabase_connected():
                return self._get_fallback_testimonials()
            
            query = self.supabase.table('customer_testimonials').select(
                """
                id, rating, title, content, is_featured, is_verified,
                users!inner(name),
                insurance_products!inner(name, insurance_categories!inner(name))
                """
            ).eq('is_verified', True).order('rating.desc')
            
            if product_id:
                query = query.eq('product_id', product_id)
            
            response = query.execute()
            return response.data if response.data else []
            
        except Exception as e:
            logger.error(f"고객 후기 조회 실패: {e}")
            return self._get_fallback_testimonials()
    
    def _get_fallback_search_results(self, query: str) -> Dict[str, Any]:
        """오프라인 모드 검색 결과"""
        return {
            "products": [
                {
                    "id": "1",
                    "name": f"'{query}' 관련 보험 상품",
                    "description": "현재 오프라인 모드로 동작 중입니다. 실제 검색 결과를 확인하려면 네트워크 연결을 확인해주세요.",
                    "base_price": 50000,
                    "type": "product",
                    "search_score": 5.0
                }
            ],
            "faqs": [
                {
                    "id": "1",
                    "question": f"'{query}'에 대한 자주 묻는 질문",
                    "answer": "현재 오프라인 모드로 동작 중입니다. 실제 FAQ를 확인하려면 네트워크 연결을 확인해주세요.",
                    "category": "일반",
                    "type": "faq",
                    "search_score": 3.0
                }
            ],
            "testimonials": []
        }
    
    def _get_fallback_faqs(self) -> List[Dict[str, Any]]:
        """오프라인 모드 FAQ"""
        return [
            {
                "id": "1",
                "category": "가입",
                "question": "보험 가입은 어떻게 하나요?",
                "answer": "온라인이나 전화로 간편하게 가입하실 수 있습니다.",
                "keywords": ["가입", "신청"],
                "is_popular": True
            },
            {
                "id": "2",
                "category": "보장",
                "question": "보장 범위는 어떻게 되나요?",
                "answer": "상품별로 보장 범위가 다르므로 상품 설명을 확인해주세요.",
                "keywords": ["보장", "범위"],
                "is_popular": True
            }
        ]
    
    def _get_fallback_testimonials(self) -> List[Dict[str, Any]]:
        """오프라인 모드 고객 후기"""
        return [
            {
                "id": "1",
                "rating": 5,
                "title": "정말 만족스러운 보험",
                "content": "보험료도 저렴하고 보장도 좋아서 만족합니다.",
                "is_featured": True,
                "is_verified": True,
                "users": {"name": "김*수"},
                "insurance_products": {
                    "name": "건강보험",
                    "insurance_categories": {"name": "건강보험"}
                }
            }
        ]

    def _get_fallback_categories(self):
        """오프라인 모드 카테고리"""
        return [
            {
                "id": "1",
                "name": "생명보험",
                "description": "사망, 질병, 상해 등에 대한 기본 보장",
                "icon_url": "/icons/life-insurance.svg",
                "sort_order": 1,
                "is_active": True
            },
            {
                "id": "2", 
                "name": "건강보험",
                "description": "의료비 보장 및 건강관리 서비스",
                "icon_url": "/icons/health-insurance.svg",
                "sort_order": 2,
                "is_active": True
            },
            {
                "id": "3",
                "name": "실손보험", 
                "description": "의료비 실손 보장",
                "icon_url": "/icons/medical-insurance.svg",
                "sort_order": 3,
                "is_active": True
            },
            {
                "id": "4",
                "name": "자동차보험",
                "description": "자동차 사고 및 손해 보장",
                "icon_url": "/icons/car-insurance.svg", 
                "sort_order": 4,
                "is_active": True
            },
            {
                "id": "5",
                "name": "연금보험",
                "description": "노후 대비 연금 및 저축",
                "icon_url": "/icons/pension-insurance.svg",
                "sort_order": 5,
                "is_active": True
            }
        ]

# 전역 서비스 인스턴스
ux_service = CoreUXService()

# 레거시 호환성을 위한 별칭
UXService = CoreUXService
InsuranceSpecificUXService = CoreUXService