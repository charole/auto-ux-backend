from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

# 핵심 imports
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from langchain.tools import BaseTool
from langchain.schema import BaseMessage
from langchain.agents import AgentExecutor, create_openai_functions_agent
from pydantic import BaseModel, Field

from config.settings import settings
from database.client import get_supabase_client, supabase_manager
from schemas.response import SimpleUXResponse, UIComponent

logger = logging.getLogger(__name__)

# DB 쿼리 도구들 정의
class InsuranceProductSearchTool(BaseTool):
    """보험 상품 검색 도구"""
    name = "search_insurance_products"
    description = "사용자의 연령, 관심사에 맞는 보험 상품을 DB에서 검색합니다. 연령 필터링이 자동으로 적용됩니다."
    
    def __init__(self):
        super().__init__()
        supabase_manager.connect()
        self.supabase = get_supabase_client()
    
    class SearchInput(BaseModel):
        age: Optional[int] = Field(description="사용자 나이 (연령 필터링용)")
        keywords: List[str] = Field(description="검색할 키워드들 (ex: ['어린이', '치아', '건강'])")
        max_results: int = Field(default=5, description="최대 결과 개수")
    
    args_schema = SearchInput
    
    def _run(self, age: Optional[int] = None, keywords: List[str] = [], max_results: int = 5) -> List[Dict]:
        """보험 상품 검색 실행"""
        try:
            # 기본 쿼리
            query = self.supabase.table('insurance_products').select(
                'id, name, description, base_price, max_coverage, age_limit_min, age_limit_max, tags, features'
            )
            
            # 연령 필터링 (가장 중요!)
            if age is not None:
                query = query.lte('age_limit_min', age).gte('age_limit_max', age)
            
            # 키워드 필터링
            if keywords:
                for keyword in keywords:
                    # 상품명, 설명, 태그에서 키워드 검색
                    query = query.or_(f'name.ilike.%{keyword}%,description.ilike.%{keyword}%,tags.cs.{[keyword]}')
            
            # 실행
            result = query.limit(max_results).execute()
            
            logger.info(f"🔍 DB 쿼리 결과: {len(result.data)}개 상품 발견 (연령: {age}, 키워드: {keywords})")
            return result.data
            
        except Exception as e:
            logger.error(f"DB 쿼리 실패: {e}")
            return []
    
    async def _arun(self, *args, **kwargs):
        return self._run(*args, **kwargs)

class UserRequestAnalyzerTool(BaseTool):
    """사용자 요청 분석 도구"""
    name = "analyze_user_request"
    description = "사용자의 요청을 분석하여 연령, 스타일 선호도, 관심 보험 종류를 추출합니다."
    
    class AnalysisInput(BaseModel):
        user_request: str = Field(description="분석할 사용자 요청")
    
    args_schema = AnalysisInput
    
    def _run(self, user_request: str) -> Dict[str, Any]:
        """사용자 요청 분석"""
        analysis = {
            "age": None,
            "age_group": "전연령",
            "style_preferences": [],
            "insurance_interests": [],
            "ui_requirements": []
        }
        
        request_lower = user_request.lower()
        
        # 연령 추출
        if "5살" in user_request or "5세" in user_request:
            analysis["age"] = 5
            analysis["age_group"] = "어린이"
        elif any(word in request_lower for word in ["어린이", "아이", "아기"]):
            analysis["age"] = 7  # 평균 어린이 나이
            analysis["age_group"] = "어린이"
        elif any(word in request_lower for word in ["10대", "청소년"]):
            analysis["age"] = 15
            analysis["age_group"] = "청소년"
        elif "20대" in request_lower:
            analysis["age"] = 25
            analysis["age_group"] = "20대"
        
        # 스타일 선호도
        if any(word in request_lower for word in ["귀엽게", "예쁘게", "이쁘게"]):
            analysis["style_preferences"].append("귀여운_디자인")
        if any(word in request_lower for word in ["크게", "큰글씨"]):
            analysis["style_preferences"].append("큰_폰트")
        if any(word in request_lower for word in ["간단하게", "요약"]):
            analysis["style_preferences"].append("간단한_레이아웃")
        
        # 보험 관심사
        if any(word in request_lower for word in ["치아", "이빨"]):
            analysis["insurance_interests"].append("치아")
        if any(word in request_lower for word in ["건강", "의료"]):
            analysis["insurance_interests"].append("건강")
        if "암" in request_lower:
            analysis["insurance_interests"].append("암")
        
        logger.info(f"🧠 사용자 요청 분석 완료: {analysis}")
        return analysis
    
    async def _arun(self, *args, **kwargs):
        return self._run(*args, **kwargs)

class CoreUXService:
    """핵심 UX 서비스 - LangChain + Supabase (정리된 버전)"""
    
    def __init__(self):
        # Supabase 클라이언트 초기화
        supabase_manager.connect()
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
    ) -> SimpleUXResponse:
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
            
            # 간소화된 응답 반환
            return SimpleUXResponse(
                components=components,
                total_products=len(db_data.get('products', [])) if db_data.get('products') else None,
                generated_at=datetime.now().isoformat(),
                ai_generated=self.ai_available
            )
            
        except Exception as e:
            logger.error(f"UI 생성 실패: {e}")
            return self._generate_error_ui(str(e))
    
    async def _collect_data(self, page_type: str, user_context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """데이터베이스에서 필요한 데이터 수집"""
        data = {}
        
        if not self.supabase:
            logger.warning("Supabase 클라이언트가 없음")
            return data
        
        try:
            logger.info(f"페이지 타입 '{page_type}'에 대한 데이터 수집 시작")
            
            if page_type == 'home':
                # 홈페이지: 인기 상품과 카테고리
                categories = self.supabase.table('insurance_categories').select('*').execute()
                popular_products = self.supabase.table('insurance_products').select(
                    '*, insurance_categories(name, description)'
                ).eq('is_popular', True).limit(5).execute()
                
                data['categories'] = categories.data if categories.data else []
                data['popular_products'] = popular_products.data if popular_products.data else []
                
            elif page_type == 'products':
                # 상품페이지: 모든 상품과 카테고리
                categories = self.supabase.table('insurance_categories').select('*').execute()
                products = self.supabase.table('insurance_products').select(
                    '*, insurance_categories(name, description, icon_url)'
                ).execute()
                
                data['categories'] = categories.data if categories.data else []
                data['products'] = products.data if products.data else []
                
            elif page_type == 'search':
                # 검색 페이지: insurance_products 중심으로 모든 관련 데이터
                products = self.supabase.table('insurance_products').select(
                    '*, insurance_categories(name, description, icon_url)'
                ).execute()
                categories = self.supabase.table('insurance_categories').select('*').execute()
                faqs = self.supabase.table('faqs').select('*').limit(15).execute()
                testimonials = self.supabase.table('customer_testimonials').select(
                    '*, users(name), insurance_products(name)'
                ).eq('is_verified', True).limit(10).execute()
                
                data['products'] = products.data if products.data else []
                data['categories'] = categories.data if categories.data else []
                data['faqs'] = faqs.data if faqs.data else []
                data['testimonials'] = testimonials.data if testimonials.data else []
                
            elif page_type == 'product_detail' and user_context and user_context.get('product_id'):
                # 특정 상품 상세
                product_id = user_context['product_id']
                product = self.supabase.table('insurance_products').select(
                    '*, insurance_categories(name, description)'
                ).eq('id', product_id).execute()
                
                data['product'] = product.data[0] if product.data else None
                
            logger.info(f"데이터 수집 완료: {list(data.keys())}")
                
        except Exception as e:
            logger.error(f"데이터 수집 실패: {e}")
        
        return data
    
    async def _generate_ai_ui(self, page_type: str, db_data: Dict[str, Any], custom_requirements: Optional[str]) -> List[UIComponent]:
        """AI로 UI 생성"""
        try:
            # 검색 페이지를 위한 특별한 프롬프트
            if page_type == 'search':
                prompt_template = PromptTemplate(
                    input_variables=["user_request", "data", "user_context"],
                    template="""
                    당신은 창의적인 웹 UI/UX 디자이너이자 보험 전문가입니다. 사용자의 요청을 정확히 분석하여 그들이 원하는 스타일과 형태로 동적 UI를 생성하되, 반드시 실제 DB 데이터를 활용하세요.

                    **사용자 요청**: {user_request}
                    **실제 DB 데이터**: {data}
                    **사용자 정보**: {user_context}

                    **중요**: 사용자 요청을 세밀하게 분석하여 그들이 원하는 대로 UI를 생성하세요:

                    🎯 **연령별 상품 필터링 (매우 중요)**:
                    - "5살", "어린이", "아이" → 0~18세 가입 가능 상품만 (우리아이 종합보험, 태아보험, 어린이 치아보험, 실손의료보험 등)
                    - "10대", "청소년" → 13~19세 가입 가능 상품만 (청소년보험, 학교안전보험 등)
                    - "20대" → 20~29세 최적 상품
                    - "30대" → 30~39세 최적 상품
                    - "40대 이상" → 해당 연령 상품
                    - 반드시 age_limit_min과 age_limit_max를 확인하여 해당 연령이 가입 가능한 상품만 추천

                    📏 **크기 요청 분석**:
                    - "크게", "큰 글씨", "보기 좋게" → 큰 폰트(font-size: 1.5rem 이상), 넓은 패딩(padding: 2rem 이상)
                    - "작게", "간단하게", "요약해서" → 작은 폰트(font-size: 0.9rem), 컴팩트한 레이아웃
                    - "한눈에", "간략히" → 테이블이나 리스트 형태

                    🎨 **스타일 요청 분석**:
                    - "귀엽게", "5살", "어린이" → 밝은 색상(#ff6b6b, #4ecdc4, #45b7d1), 큰 이모지(🎈🎨🌈), 둥근 모서리(border-radius: 20px), 재미있는 폰트
                    - "가독성", "읽기 좋게" → 명확한 구분선, 여백, 대비
                    - "예쁘게", "이쁘게" → 그라디언트, 둥근 모서리, 그림자
                    - "심플하게", "깔끔하게" → 미니멀 디자인, 단순한 색상

                    🎭 **애니메이션 요청**:
                    - "움직이게", "애니메이션" → CSS transform과 transition 추가
                    - "부드럽게" → transition: all 0.3s ease

                    **절대 규칙**:
                    1. 실제 DB 데이터만 사용 (insurance_products의 실제 name, base_price, max_coverage, description 사용)
                    2. 한국어로 작성
                    3. <img> 태그 금지 (이모지 사용)
                    4. 인라인 CSS만 사용
                    5. content 필드에 반드시 실제 HTML 콘텐츠 포함
                    6. 사용자가 요청한 스타일/크기/형태로 반드시 생성

                    **응답 형식 (JSON)**: 반드시 이 형식으로 응답하고, content에 실제 HTML을 포함하세요:

                    [
                        {{
                            "type": "header",
                            "id": "search_header",
                            "title": "'{user_request}'에 대한 검색 결과",
                            "content": "<div style='text-align: center; padding: 2rem; background: linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%); color: white; border-radius: 20px; margin-bottom: 2rem;'><h1 style='margin: 0; font-size: 2rem; font-weight: 700;'>🎈 {user_request}</h1><p style='margin: 1rem 0 0 0; font-size: 1.1rem;'>맞춤 보험 정보를 찾았어요!</p></div>",
                            "style": "",
                            "priority": 1,
                            "data": {{"query": "{user_request}"}}
                        }},
                        {{
                            "type": "section",
                            "id": "products_showcase",
                            "title": "추천 보험 상품",
                            "content": "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem;'><div style='background: white; padding: 1.5rem; border-radius: 20px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); border: 3px solid #ff6b6b;'><h3 style='margin: 0 0 1rem 0; color: #333; font-size: 1.4rem;'>🎨 [실제상품명]</h3><div style='margin-bottom: 1rem;'><span style='background: #ff6b6b; color: white; padding: 0.7rem 1.2rem; border-radius: 25px; font-size: 1.2rem; font-weight: 600;'>[실제월보험료]원/월</span></div><p style='color: #666; margin-bottom: 1rem; line-height: 1.6; font-size: 1rem;'>[실제상품설명]</p><div style='background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 1.2rem; border-radius: 15px;'><strong style='color: #333; font-size: 1.1rem;'>🌈 최대 보장: [실제보장금액]원</strong></div></div></div>",
                            "style": "padding: 2rem; background: linear-gradient(135deg, #f8f9fa 0%, #fff5f5 100%); border-radius: 20px;",
                            "priority": 2,
                            "data": {{"source": "insurance_products", "age_filtered": true}}
                        }}
                    ]

                    **필수 예시 - 5살 어린이 요청시**:
                    - 우리아이 종합보험 (0세~30세) ✅ 추천
                    - 태아보험 (0세~35세) ✅ 추천 
                    - 어린이 치아보험 (3세~18세) ✅ 추천
                    - 실손의료보험 4세대 (0세~100세) ✅ 추천
                    - 안심생명보험 (20세~65세) ❌ 절대 추천 금지
                    
                    반드시 age_limit_min ≤ 사용자나이 ≤ age_limit_max 조건을 만족하는 상품만 선택하세요!
                    """
                )
            else:
                # 일반 페이지용 프롬프트
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

                    **JSON 형식으로 응답**:
                    [
                        {{
                            "type": "section",
                            "id": "page_content", 
                            "title": "페이지 내용",
                            "content": "실제 DB 데이터 활용한 HTML",
                            "style": "padding: 20px; background: #f8f9fa; border-radius: 12px;",
                            "priority": 1,
                            "data": {{"source": "real_db", "page_type": "{page_type}"}}
                        }}
                    ]
                    """
                )
            
            # LangChain 최신 방식 사용
            chain = prompt_template | self.llm
            
            if page_type == 'search':
                user_context = self._analyze_user_context(custom_requirements or "")
                enhanced_data = self._format_search_data_for_ai(db_data)
                
                response = await chain.ainvoke({
                    "user_request": custom_requirements or "",
                    "data": enhanced_data,
                    "user_context": user_context
                })
            else:
                enhanced_requirements = custom_requirements or f"사용자 친화적이고 매력적인 {page_type} UI"
                
                response = await chain.ainvoke({
                    "page_type": page_type,
                    "data": self._format_data_for_ai(db_data),
                    "requirements": enhanced_requirements
                })
            
            # AI 응답을 파싱하여 UIComponent로 변환
            return self._parse_ai_response(response.content)
            
        except Exception as e:
            logger.error(f"AI UI 생성 실패: {e}")
            return self._generate_fallback_ui(page_type)

    def _analyze_user_context(self, user_request: str) -> str:
        """사용자 요청에서 컨텍스트 정보 추출 (UI 중심 개선)"""
        context_info = []
        request_lower = user_request.lower()
        
        # UI 크기 요구사항 분석
        size_requirements = []
        if any(word in request_lower for word in ['크게', '큰글씨', '큰 글씨', '보기좋게', '보기 좋게']):
            size_requirements.append("큰 크기 UI")
        elif any(word in request_lower for word in ['작게', '간단하게', '간단히', '요약해서', '짧게']):
            size_requirements.append("컴팩트한 UI")
        elif any(word in request_lower for word in ['한눈에', '간략히', '한번에']):
            size_requirements.append("요약형 UI")
        
        if size_requirements:
            context_info.append(f"크기 요구: {', '.join(size_requirements)}")
        
        # UI 스타일 요구사항 분석
        style_requirements = []
        if any(word in request_lower for word in ['가독성', '읽기좋게', '읽기 좋게', '보기편하게', '보기 편하게']):
            style_requirements.append("가독성 중심")
        elif any(word in request_lower for word in ['예쁘게', '이쁘게', '아름답게', '멋있게', '멋지게']):
            style_requirements.append("시각적 매력")
        elif any(word in request_lower for word in ['심플하게', '깔끔하게', '단순하게', '미니멀']):
            style_requirements.append("미니멀 디자인")
        elif any(word in request_lower for word in ['화려하게', '특별하게', '독특하게']):
            style_requirements.append("화려한 디자인")
        
        if style_requirements:
            context_info.append(f"스타일 요구: {', '.join(style_requirements)}")
        
        # 애니메이션 요구사항 분석
        animation_requirements = []
        if any(word in request_lower for word in ['움직이게', '애니메이션', '동적으로', '생동감']):
            animation_requirements.append("애니메이션 효과")
        elif any(word in request_lower for word in ['부드럽게', '자연스럽게', 'smooth']):
            animation_requirements.append("부드러운 전환")
        elif any(word in request_lower for word in ['튀어나오게', '팝업', '팝업처럼']):
            animation_requirements.append("팝업 효과")
        
        if animation_requirements:
            context_info.append(f"애니메이션: {', '.join(animation_requirements)}")
        
        # 레이아웃 요구사항 분석
        layout_requirements = []
        if any(word in request_lower for word in ['비교해서', '나란히', '비교', '대비']):
            layout_requirements.append("비교 레이아웃")
        elif any(word in request_lower for word in ['카드형태', '카드로', '카드형']):
            layout_requirements.append("카드 레이아웃")
        elif any(word in request_lower for word in ['리스트로', '목록으로', '목록형']):
            layout_requirements.append("리스트 레이아웃")
        elif any(word in request_lower for word in ['테이블로', '표로', '표형태']):
            layout_requirements.append("테이블 레이아웃")
        elif any(word in request_lower for word in ['그래프로', '차트로', '시각적으로']):
            layout_requirements.append("차트/그래프")
        
        if layout_requirements:
            context_info.append(f"레이아웃: {', '.join(layout_requirements)}")
        
        # 연령대 분석
        if any(age in request_lower for age in ['10대', '20대', '30대', '40대', '50대', '60대']):
            for age in ['10대', '20대', '30대', '40대', '50대', '60대']:
                if age in request_lower:
                    context_info.append(f"연령대: {age}")
                    break
        
        # 보험 종류 분석
        insurance_types = []
        if '암보험' in request_lower or '암' in request_lower:
            insurance_types.append("암보험")
        if '건강보험' in request_lower or '의료보험' in request_lower:
            insurance_types.append("건강보험")
        if '생명보험' in request_lower:
            insurance_types.append("생명보험")
        if '자동차보험' in request_lower or '자동차' in request_lower:
            insurance_types.append("자동차보험")
        if '실손보험' in request_lower or '실손' in request_lower:
            insurance_types.append("실손보험")
        if '치아보험' in request_lower or '치아' in request_lower:
            insurance_types.append("치아보험")
        if '여행보험' in request_lower or '여행자보험' in request_lower:
            insurance_types.append("여행보험")
        
        if insurance_types:
            context_info.append(f"관심 보험: {', '.join(insurance_types)}")
        
        # 가격 선호도 분석
        if '저렴' in request_lower or '싼' in request_lower or '가성비' in request_lower:
            context_info.append("가격 선호: 저렴한 상품 선호")
        elif '프리미엄' in request_lower or '고급' in request_lower:
            context_info.append("가격 선호: 프리미엄 상품 선호")
        
        # 정보 제공 방식 분석
        if '상세' in request_lower or '자세' in request_lower:
            context_info.append("정보 제공: 상세한 설명 필요")
        elif '핵심만' in request_lower or '중요한것만' in request_lower:
            context_info.append("정보 제공: 핵심 정보만")
        
        return ' | '.join(context_info) if context_info else "일반 사용자"

    def _format_search_data_for_ai(self, db_data: Dict[str, Any]) -> str:
        """검색용 데이터 포맷팅 (개선)"""
        formatted_data = {}
        
        # insurance_products 데이터 (핵심)
        if 'products' in db_data and db_data['products']:
            products_summary = []
            for product in db_data['products']:
                category_info = product.get('insurance_categories', {})
                
                # 상품 정보를 더 상세하게 포맷팅
                summary = {
                    'id': product.get('id'),
                    'name': product.get('name'),
                    'description': product.get('description'),
                    'base_price': product.get('base_price'),
                    'max_coverage': product.get('max_coverage'),
                    'features': product.get('features', []),
                    'tags': product.get('tags', []),
                    'category_name': category_info.get('name', ''),
                    'category_description': category_info.get('description', ''),
                    'is_popular': product.get('is_popular'),
                    'is_new': product.get('is_new'),
                    'age_limit_min': product.get('age_limit_min'),
                    'age_limit_max': product.get('age_limit_max'),
                    
                    # AI가 쉽게 이해할 수 있도록 추가 정보
                    'formatted_price': f"{product.get('base_price', 0):,}원/월" if product.get('base_price') else "가격 문의",
                    'formatted_coverage': f"{product.get('max_coverage', 0):,}원" if product.get('max_coverage') else "보장 한도 문의",
                    'target_age_group': self._determine_age_group(product.get('age_limit_min', 0), product.get('age_limit_max', 100)),
                    'product_highlights': self._extract_product_highlights(product)
                }
                products_summary.append(summary)
            
            # 상품 개수에 따라 우선순위 설정
            formatted_data['보험상품_전체'] = {
                '총_개수': len(products_summary),
                '상품_목록': products_summary,
                '데이터_상태': '실제_DB_데이터',
                '업데이트_시간': '실시간'
            }
        
        # 카테고리 정보 (참고용)
        if 'categories' in db_data and db_data['categories']:
            categories_formatted = []
            for cat in db_data['categories']:
                categories_formatted.append({
                    'id': cat.get('id'),
                    'name': cat.get('name'),
                    'description': cat.get('description'),
                    'icon_url': cat.get('icon_url'),
                    'sort_order': cat.get('sort_order')
                })
            formatted_data['보험카테고리'] = categories_formatted
        
        # FAQ 정보 (사용자 질문과 관련된 내용 제공용)
        if 'faqs' in db_data and db_data['faqs']:
            faqs_formatted = []
            for faq in db_data['faqs'][:10]:  # 상위 10개만
                faqs_formatted.append({
                    'question': faq.get('question'),
                    'answer': faq.get('answer'),
                    'category': faq.get('category'),
                    'keywords': faq.get('keywords', [])
                })
            formatted_data['자주묻는질문'] = faqs_formatted
        
        # 고객 후기 (신뢰성 제공용)
        if 'testimonials' in db_data and db_data['testimonials']:
            testimonials_formatted = []
            for testimonial in db_data['testimonials'][:5]:  # 상위 5개만
                testimonials_formatted.append({
                    'title': testimonial.get('title'),
                    'content': testimonial.get('content'),
                    'rating': testimonial.get('rating'),
                    'customer_name': testimonial.get('users', {}).get('name', '고객'),
                    'product_name': testimonial.get('insurance_products', {}).get('name', ''),
                    'is_verified': testimonial.get('is_verified')
                })
            formatted_data['고객후기'] = testimonials_formatted
        
        # JSON 문자열로 변환 (더 큰 용량 허용)
        import json
        try:
            data_str = json.dumps(formatted_data, ensure_ascii=False, indent=2)
            return data_str[:15000]  # 15KB 제한으로 증가
        except Exception as e:
            logger.error(f"데이터 JSON 변환 실패: {e}")
            return str(formatted_data)[:15000]
    
    def _determine_age_group(self, min_age: int, max_age: int) -> str:
        """연령 제한으로 타겟 연령대 결정"""
        if min_age <= 20 and max_age >= 29:
            return "20대 적합"
        elif min_age <= 30 and max_age >= 39:
            return "30대 적합"
        elif min_age <= 40 and max_age >= 49:
            return "40대 적합"
        elif min_age <= 19:
            return "10대-20대 초반 적합"
        elif max_age >= 60:
            return "중장년층 적합"
        else:
            return f"{min_age}세-{max_age}세 가입 가능"
    
    def _extract_product_highlights(self, product: Dict[str, Any]) -> List[str]:
        """상품의 주요 특징 추출"""
        highlights = []
        
        if product.get('is_popular'):
            highlights.append("인기 상품")
        if product.get('is_new'):
            highlights.append("신상품")
        
        # 가격대 분석
        price = product.get('base_price', 0)
        if price > 0:
            if price < 30000:
                highlights.append("저렴한 보험료")
            elif price > 100000:
                highlights.append("프리미엄 상품")
        
        # 보장 금액 분석
        coverage = product.get('max_coverage', 0)
        if coverage > 0:
            if coverage >= 100000000:  # 1억 이상
                highlights.append("고액 보장")
            elif coverage >= 50000000:  # 5천만 이상
                highlights.append("충분한 보장")
        
        # 특징에서 키워드 추출
        features = product.get('features', [])
        if features:
            for feature in features[:2]:  # 상위 2개 특징만
                if len(feature) < 20:  # 너무 긴 설명 제외
                    highlights.append(feature)
        
        return highlights[:4]  # 최대 4개까지만

    def _format_data_for_ai(self, db_data: Dict[str, Any]) -> str:
        """일반 데이터 포맷팅"""
        import json
        try:
            data_str = json.dumps(db_data, ensure_ascii=False, indent=2)
            return data_str[:5000]  # 5KB 제한
        except Exception as e:
            logger.error(f"데이터 JSON 변환 실패: {e}")
            return str(db_data)[:5000]

    def _parse_ai_response(self, response: str) -> List[UIComponent]:
        """AI 응답을 UIComponent로 파싱"""
        try:
            import json
            import re
            
            logger.info(f"🔍 AI 응답 파싱 시작. 응답 길이: {len(response)}자")
            logger.info(f"📝 AI 응답 내용 (처음 500자): {response[:500]}")
            
            # JSON 추출 시도
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                logger.info(f"✅ JSON 패턴 매칭 성공. JSON 길이: {len(json_str)}자")
                logger.info(f"📋 추출된 JSON: {json_str[:300]}...")
                
                try:
                    components_data = json.loads(json_str)
                    logger.info(f"✅ JSON 파싱 성공. 컴포넌트 개수: {len(components_data)}")
                    
                    components = []
                    for i, comp_data in enumerate(components_data):
                        component_id = comp_data.get('id') or f"ai_comp_{i}"
                        
                        component = UIComponent(
                            type=comp_data.get('type', 'div'),
                            id=component_id,
                            title=comp_data.get('title', ''),
                            content=comp_data.get('content', ''),
                            style=comp_data.get('style', ''),
                            priority=comp_data.get('priority', i + 1),
                            data=comp_data.get('data', {})
                        )
                        components.append(component)
                        logger.info(f"✅ 컴포넌트 {i+1} 생성: {component.type} - {component.title[:50]}")
                    
                    logger.info(f"🎉 AI 컴포넌트 {len(components)}개 파싱 완료")
                    return components
                
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON 디코딩 실패: {e}")
                    logger.error(f"❌ 문제가 된 JSON: {json_str}")
            else:
                logger.warning("⚠️ JSON 패턴을 찾을 수 없음")
                logger.info(f"📝 전체 AI 응답: {response}")
                
        except Exception as e:
            logger.error(f"❌ AI 응답 파싱 중 오류 발생: {e}")
            logger.error(f"📝 오류 발생한 응답: {response}")
        
        logger.warning("🔄 폴백 UI로 전환")
        return self._generate_fallback_ui("default")
    
    def _generate_fallback_ui(self, page_type: str) -> List[UIComponent]:
        """폴백 UI 생성"""
        fallback_components = {
            "home": [
                UIComponent(
                    type="section",
                    id="hero",
                    title="보험의 시작, 믿을 수 있는 파트너",
                    content="""
                    <div style="text-align: center; padding: 3rem 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 20px;">
                        <h1 style="font-size: 2.5rem; font-weight: 900; margin: 0 0 1rem 0;">🛡️ 안전한 미래를 위한 선택</h1>
                        <p style="font-size: 1.2rem; line-height: 1.8; margin: 1rem 0;">신뢰할 수 있는 보험 서비스로 가족의 안전을 지켜보세요.</p>
                        <div style="margin-top: 2rem;">
                            <span style="background: rgba(255,255,255,0.2); padding: 1rem 2rem; border-radius: 50px; font-size: 1.1rem;">💰 월 2만원부터 시작하는 든든한 보장</span>
                        </div>
                    </div>
                    """,
                    style="margin-bottom: 2rem;",
                    priority=1
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
                        <h2 style="color: #2d3748; font-size: 2rem; font-weight: 700; margin: 0 0 1rem 0;">AI 보험 전문가가 분석 중입니다</h2>
                        <p style="color: #4a5568; line-height: 1.8; font-size: 1.1rem;">고객님의 요구사항을 분석하여 가장 적합한 보험 상품을 찾고 있습니다.</p>
                    </div>
                    """,
                    style="background: linear-gradient(135deg, #f7fafc 0%, #e2e8f0 100%); border-radius: 20px;",
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
                style="padding: 2rem; text-align: center;",
                priority=1
            )
        ])
    
    def _generate_error_ui(self, error_message: str) -> SimpleUXResponse:
        """에러 UI 생성"""
        return SimpleUXResponse(
            components=[
                UIComponent(
                    type="notice",
                    id="error",
                    title="일시적 오류",
                    content="서비스 처리 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                    style="padding: 2rem; background: #fff3cd; border: 1px solid #ffeaa7; border-radius: 8px;",
                    priority=1
                )
            ],
            total_products=None,
            generated_at=datetime.now().isoformat(),
            ai_generated=False
        )
    
    # 간단한 조회 메서드들
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

# 전역 서비스 인스턴스
ux_service = CoreUXService()

# 레거시 호환성을 위한 별칭
UXService = CoreUXService
InsuranceSpecificUXService = CoreUXService 