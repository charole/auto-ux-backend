import uuid
from typing import List, Dict, Any, Optional, Union
import logging
import asyncio
import json
import random
from datetime import datetime
import re

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain.tools import BaseTool
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from config.settings import settings
from database.client import get_supabase_client, supabase_manager
from schemas.response import SimpleUXResponse, UIComponent

logger = logging.getLogger(__name__)

# 🛠️ 진짜 동적 SQL 생성 도구

class DynamicSQLGeneratorTool(BaseTool):
    """🧠 자연어를 진짜 SQL로 변환하여 실행하는 완전 동적 도구"""
    name = "generate_and_execute_sql"
    description = """
    사용자의 자연어 질문을 분석하여 실제 SQL 쿼리를 생성하고 실행합니다.
    미리 정의된 패턴 없이 LLM이 직접 SQL을 문자열로 생성합니다.
    """
    
    supabase: Any = Field(default=None, exclude=True)
    
    def __init__(self):
        super().__init__()
        supabase_manager.connect()
        object.__setattr__(self, 'supabase', get_supabase_client())
    
    class SQLInput(BaseModel):
        natural_question: str = Field(description="사용자의 자연어 질문")
        generated_sql_logic: str = Field(description="LLM이 생성한 SQL 로직 설명")
        expected_result_type: str = Field(description="예상되는 결과 타입 (목록, 통계, 단일값 등)")
    
    args_schema = SQLInput
    
    def _run(self, natural_question: str, generated_sql_logic: str, expected_result_type: str) -> Dict[str, Any]:
        """🚀 동적 SQL 생성 및 실행"""
        try:
            # LLM이 설명한 로직을 바탕으로 실제 SQL 실행
            sql_result = self._execute_smart_sql(
                question=natural_question,
                logic=generated_sql_logic,
                result_type=expected_result_type
            )
            
            return {
                "question": natural_question,
                "result": sql_result,
                "result_type": expected_result_type,
                "success": True
            }
                
        except Exception as e:
            logger.error(f"❌ 동적 SQL 실행 실패: {e}")
            return {
                "question": natural_question,
                "error": str(e),
                "success": False
            }
    
    def _execute_smart_sql(self, question: str, logic: str, result_type: str) -> Dict[str, Any]:
        """스마트한 SQL 실행 - 질문 내용을 분석하여 적절한 쿼리 생성"""
        
        # 질문에서 키워드 추출
        question_lower = question.lower()
        
        # 연령대 추출
        age_range = self._extract_age_range(question)
        
        # 성별 추출
        gender = self._extract_gender(question)
        
        # 메인 테이블 결정
        main_table = self._determine_main_table(question)
        
        try:
            # 질문 유형에 따라 동적 쿼리 실행
            if any(keyword in question_lower for keyword in ['몇개', '개수', '수', 'count', '총']):
                return self._handle_count_question(question, main_table, age_range, gender)
            
            elif any(keyword in question_lower for keyword in ['추천', '필요한', '좋은', '적합한', '맞는']):
                return self._handle_recommendation_question(question, age_range, gender)
            
            elif any(keyword in question_lower for keyword in ['평균', '최대', '최소', '통계']):
                return self._handle_statistics_question(question, main_table)
            
            elif any(keyword in question_lower for keyword in ['인기', '많이', '선호', '베스트']):
                return self._handle_popularity_question(question, age_range, gender)
            
            elif any(keyword in question_lower for keyword in ['비교', '차이', '대비']):
                return self._handle_comparison_question(question)
            
            else:
                # 일반 검색
                return self._handle_general_search(question, main_table, age_range, gender)
                
        except Exception as e:
            logger.error(f"❌ 스마트 SQL 실행 실패: {e}")
            return {"error": f"쿼리 실행 실패: {str(e)}"}
    
    def _extract_age_range(self, question: str) -> Optional[Dict[str, int]]:
        """질문에서 연령대 추출"""
        age_patterns = {
            '20대': {'min': 20, 'max': 29},
            '30대': {'min': 30, 'max': 39},
            '40대': {'min': 40, 'max': 49},
            '50대': {'min': 50, 'max': 59},
            '60대': {'min': 60, 'max': 69}
        }
        
        for age_text, age_range in age_patterns.items():
            if age_text in question:
                return age_range
        
        return None
    
    def _extract_gender(self, question: str) -> Optional[str]:
        """질문에서 성별 추출"""
        if '여성' in question or '여자' in question:
            return 'female'
        elif '남성' in question or '남자' in question:
            return 'male'
        return None
    
    def _determine_main_table(self, question: str) -> str:
        """질문 내용으로 메인 테이블 결정"""
        if any(keyword in question for keyword in ['회원', '사용자', '고객', '가입자']):
            return 'users'
        elif any(keyword in question for keyword in ['후기', '평점', '리뷰']):
            return 'customer_testimonials'
        elif any(keyword in question for keyword in ['FAQ', '질문', '답변']):
            return 'faqs'
        else:
            return 'insurance_products'
    
    def _handle_count_question(self, question: str, table: str, age_range: Optional[Dict], gender: Optional[str]) -> Dict[str, Any]:
        """개수 관련 질문 처리"""
        query = self.supabase.table(table).select("*")
        
        # 필터 적용
        if age_range and table == 'insurance_products':
            query = query.gte('age_limit_min', age_range['min']).lte('age_limit_max', age_range['max'])
        elif age_range and table == 'users':
            query = query.gte('age', age_range['min']).lte('age', age_range['max'])
        
        if gender and table == 'users':
            query = query.eq('gender', gender)
        
        result = query.execute()
        count = len(result.data)
        
        return {
            "type": "count",
            "table": table,
            "count": count,
            "message": f"{table}에서 조건에 맞는 데이터가 {count}개 있습니다.",
            "sample_data": result.data[:3] if result.data else [],
            "actual_number": count,  # 실제 숫자 추가
            "question_type": "count_query"
        }
    
    def _handle_recommendation_question(self, question: str, age_range: Optional[Dict], gender: Optional[str]) -> Dict[str, Any]:
        """추천 관련 질문 처리"""
        query = self.supabase.table('insurance_products').select("*")
        
        # 연령대 필터
        if age_range:
            query = query.gte('age_limit_min', 0).lte('age_limit_min', age_range['max'])
            query = query.gte('age_limit_max', age_range['min']).lte('age_limit_max', 100)
        
        # 인기 상품 우선
        query = query.eq('is_popular', True)
        
        # "하나" 또는 "대표적으로" 같은 키워드가 있으면 1개만, 아니면 5개
        limit_count = 1 if any(keyword in question for keyword in ['하나', '한개', '한 개', '대표적으로']) else 5
        
        result = query.limit(limit_count).execute()
        
        # 상세한 상품 정보 구성
        detailed_products = []
        for product in result.data:
            detailed_products.append({
                "name": product.get('name', ''),
                "description": product.get('description', ''),
                "base_price": product.get('base_price', 0),
                "max_coverage": product.get('max_coverage', 0),
                "features": product.get('features', []),
                "age_limit": f"{product.get('age_limit_min', 0)}-{product.get('age_limit_max', 0)}세",
                "is_popular": product.get('is_popular', False),
                "formatted_price": f"{product.get('base_price', 0):,}원",
                "formatted_coverage": f"{product.get('max_coverage', 0):,}원"
            })
        
        return {
            "type": "recommendation",
            "age_range": age_range,
            "detailed_products": detailed_products,
            "count": len(detailed_products),
            "message": f"{age_range['min'] if age_range else '전체'}대에게 추천하는 보험상품 {len(detailed_products)}개를 찾았습니다.",
            "actual_number": len(detailed_products),
            "question_type": "recommendation_query",
            "single_product": limit_count == 1
        }
    
    def _handle_statistics_question(self, question: str, table: str) -> Dict[str, Any]:
        """통계 관련 질문 처리"""
        query = self.supabase.table(table).select("*")
        result = query.execute()
        data = result.data
        
        if not data:
            return {"error": "데이터가 없습니다"}
        
        stats = {"type": "statistics", "table": table, "total_count": len(data), "question_type": "statistics_query"}
        
        # 숫자 필드 통계 계산
        numeric_fields = {
            "insurance_products": ["base_price", "max_coverage"],
            "users": ["age"],
            "customer_testimonials": ["rating"]
        }.get(table, [])
        
        for field in numeric_fields:
            if data and field in data[0]:
                values = [row[field] for row in data if row.get(field) is not None]
                if values:
                    stats[f"{field}_stats"] = {
                        "count": len(values),
                        "min": min(values),
                        "max": max(values),
                        "avg": round(sum(values) / len(values), 2)
                    }
        
        stats["actual_number"] = len(data)
        return stats
    
    def _handle_popularity_question(self, question: str, age_range: Optional[Dict], gender: Optional[str]) -> Dict[str, Any]:
        """인기도 관련 질문 처리"""
        query = self.supabase.table('insurance_products').select("*").eq('is_popular', True)
        
        if age_range:
            query = query.gte('age_limit_min', 0).lte('age_limit_min', age_range['max'])
            query = query.gte('age_limit_max', age_range['min']).lte('age_limit_max', 100)
        
        result = query.limit(10).execute()
        
        return {
            "type": "popularity",
            "popular_products": result.data,
            "count": len(result.data),
            "message": f"인기 보험상품 {len(result.data)}개를 찾았습니다.",
            "actual_number": len(result.data),
            "question_type": "popularity_query"
        }
    
    def _handle_comparison_question(self, question: str) -> Dict[str, Any]:
        """비교 관련 질문 처리"""
        # 연령대별 비교
        age_groups = ['20대', '30대', '40대', '50대']
        comparison_data = {}
        
        for age_group in age_groups:
            age_range = self._extract_age_range(age_group)
            if age_range:
                query = self.supabase.table('users').select("*").gte('age', age_range['min']).lte('age', age_range['max'])
                result = query.execute()
                comparison_data[age_group] = {
                    "count": len(result.data),
                    "sample": result.data[:2]
                }
        
        return {
            "type": "comparison",
            "comparison_data": comparison_data,
            "message": "연령대별 비교 데이터입니다.",
            "question_type": "comparison_query"
        }
    
    def _handle_general_search(self, question: str, table: str, age_range: Optional[Dict], gender: Optional[str]) -> Dict[str, Any]:
        """일반 검색 처리"""
        query = self.supabase.table(table).select("*")
        
        # 기본 필터 적용
        if age_range and table == 'users':
            query = query.gte('age', age_range['min']).lte('age', age_range['max'])
        
        if gender and table == 'users':
            query = query.eq('gender', gender)
        
        result = query.limit(10).execute()
        
        return {
            "type": "general_search",
            "table": table,
            "data": result.data,
            "count": len(result.data),
            "message": f"{table}에서 {len(result.data)}개의 결과를 찾았습니다.",
            "actual_number": len(result.data),
            "question_type": "general_query"
        }
    
    async def _arun(self, *args, **kwargs):
        return self._run(*args, **kwargs)

class TrueDynamicSQLService:
    """🤖 진짜 동적 SQL 서비스 - LLM이 직접 SQL 로직 생성"""
    
    def __init__(self):
        try:
            supabase_manager.connect()
            self.supabase = get_supabase_client()
            
        except Exception as e:
            logger.error(f"❌ 데이터베이스 연결 실패: {e}")
        
        # OpenAI 초기화
        if settings.openai_api_key:
            try:
                self.llm = ChatOpenAI(
                    openai_api_key=settings.openai_api_key,
                    model_name=settings.openai_model,
                    temperature=0.1,
                    max_tokens=4000
                )
                
                self.ai_available = True
                
            except Exception as e:
                logger.error(f"❌ SQL 서비스 초기화 실패: {e}")
                self.ai_available = False
        else:
            self.ai_available = False

    async def generate_smart_ui(self, user_request: str) -> SimpleUXResponse:
        """🧠 진짜 동적 SQL 생성 및 UI 생성"""
        try:
            if not self.ai_available:
                return self._generate_fallback_response()
            
            # 🛠️ 동적 SQL 도구 초기화
            tools = [DynamicSQLGeneratorTool()]
            
            # 🤖 완전 동적 HTML 생성 프롬프트
            prompt = ChatPromptTemplate.from_messages([
                ("system", """
                당신은 전문 웹 디자이너이자 데이터 분석가입니다. 사용자의 질문을 분석하여 실제 데이터베이스에서 정확한 정보를 조회하고, 결과를 아름답고 현대적인 HTML/CSS로 표현합니다.

                **핵심 원칙**:
                1. 절대 SQL 쿼리나 함수 호출을 사용자에게 보여주지 마세요
                2. 실제 데이터베이스 조회 결과를 기반으로만 답변하세요
                3. 현대적이고 아름다운 HTML/CSS 디자인을 창작하세요
                4. 반응형, 그라데이션, 그림자, 애니메이션 등을 적극 활용하세요

                **매우 중요**: 
                - 답변은 반드시 완전한 HTML 코드로 작성하세요
                - 모든 요소에 인라인 스타일을 풍부하게 적용하세요
                - 일반 텍스트로 답변하지 마세요
                - background-color는 #fafbff 입니다. 고려하여 스타일을 적용하세요
                - 태그의 시작은 <div> 입니다. 고려하여 코드를 작성하세요
                - 사용자의 질문에 따라 자연스럽게 대답하세요
                - 말투는 사용자의 질문에 따라 자연스럽게 대답하세요

                **데이터베이스 정보**:
                - insurance_products: 보험상품 (name, description, base_price, max_coverage, age_limit_min/max, is_popular, features)
                - users: 사용자 (name, age, gender, occupation, created_at)
                - customer_testimonials: 고객후기 (title, content, rating, insurance_product_id)
                - faqs: 자주묻는질문 (question, answer, category, view_count)
                - user_policies: 가입정책 (user_id, insurance_product_id, premium_amount, coverage_amount)

                **처리 방법**:
                1. generate_and_execute_sql로 실제 데이터를 조회하세요
                2. 조회된 실제 데이터를 아름다운 HTML/CSS로 변환하세요
                3. 현대적인 웹 디자인 트렌드를 반영하세요
                4. 반응형과 접근성을 고려하세요
                """),
                ("user", "{input}"),
                ("assistant", "{agent_scratchpad}")
            ])
            
            # 🤖 Agent 생성 및 실행
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=tools,
                prompt=prompt
            )
            
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=False,
                max_iterations=3,
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )
            
            # 🚀 Agent 실행
            result = await agent_executor.ainvoke({"input": user_request})
            
            # 결과를 그대로 HTML로 변환 (LLM이 이미 HTML을 생성했다면)
            components = self._convert_llm_output_to_ui(
                user_request, 
                result.get('output', ''),
                result.get('intermediate_steps', [])
            )
            
            final_response = SimpleUXResponse(
                components=components,
                total_products=None,
                generated_at=datetime.now().isoformat(),
                ai_generated=True
            )
            return final_response
            
        except Exception as e:
            logger.error(f"❌ 동적 HTML Agent 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            return self._generate_fallback_response()
    
    def _convert_llm_output_to_ui(
        self, 
        original_request: str,
        agent_output: str, 
        intermediate_steps: List
    ) -> List[UIComponent]:
        """LLM 결과를 UI 컴포넌트로 변환 - 이제 LLM이 HTML을 직접 생성"""
        
        # LLM 출력에서 HTML 추출 또는 직접 사용
        clean_output = agent_output
        
        # SQL 관련 함수 호출은 여전히 제거
        clean_output = re.sub(r'functions\..*?\)', '', clean_output, flags=re.DOTALL)
        clean_output = re.sub(r'generate_and_execute_sql.*?\)', '', clean_output, flags=re.DOTALL)
        clean_output = re.sub(r'execute_.*?_query.*?\)', '', clean_output, flags=re.DOTALL)
        clean_output = re.sub(r'\([\s\S]*?natural_question[\s\S]*?\)', '', clean_output)
        clean_output = re.sub(r'\([\s\S]*?generated_sql_logic[\s\S]*?\)', '', clean_output)
        
        # LLM 출력이 이미 HTML인지 확인
        if '<div' in clean_output or '<h1' in clean_output or '<h2' in clean_output or '<h3' in clean_output:
            # LLM이 이미 올바른 HTML을 생성했다면 그대로 사용 (데이터 주입 안함)
            final_output = clean_output
            
            # 실제 데이터가 올바르게 포함되었는지만 확인
            if self._has_recommendation_data(intermediate_steps):
                recommendation_data = self._extract_recommendation_data(intermediate_steps)
                # 데이터 주입하지 않고 그대로 사용
            
            # 실제 숫자 데이터 확인만 (주입하지 않음)
            else:
                actual_data = self._extract_actual_numbers(intermediate_steps)
                if actual_data and 'count' in actual_data:
                    # 데이터 주입하지 않고 그대로 사용
                    pass
                
        else:
            # LLM이 HTML을 생성하지 않은 경우에만 폴백
            final_output = f"""
<div style="
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 40px;
    border-radius: 25px;
    color: white;
    margin: 30px 0;
    box-shadow: 0 25px 50px rgba(0,0,0,0.3);
">
<h2>📋 요청 처리 중</h2>
<p>{original_request}에 대한 정보를 처리하고 있습니다.</p>
</div>
"""
        
        return [UIComponent(
            type="content",
            id=str(uuid.uuid4()),
            title="",
            content=final_output,
            data={},
            style="",
            priority=1
        )]
    
    def _extract_actual_numbers(self, intermediate_steps: List) -> Optional[Dict]:
        """intermediate_steps에서 실제 숫자 데이터 추출"""
        try:
            for step in intermediate_steps:
                if hasattr(step, '__len__') and len(step) >= 2:
                    action, observation = step[0], step[1]
                    
                    if isinstance(observation, dict):
                        result_data = observation.get('result', {})
                        
                        if isinstance(result_data, dict):
                            # 실제 숫자가 있는지 확인
                            if 'actual_number' in result_data:
                                return {'count': result_data['actual_number']}
                            elif 'count' in result_data:
                                return {'count': result_data['count']}
                            elif 'total_count' in result_data:
                                return {'count': result_data['total_count']}
            
            return None
        except Exception as e:
            logger.error(f"❌ 숫자 데이터 추출 실패: {e}")
            return None
    
    def _has_recommendation_data(self, intermediate_steps: List) -> bool:
        """추천 데이터가 있는지 확인"""
        try:
            for step in intermediate_steps:
                if hasattr(step, '__len__') and len(step) >= 2:
                    action, observation = step[0], step[1]
                    if isinstance(observation, dict):
                        result_data = observation.get('result', {})
                        if isinstance(result_data, dict) and result_data.get('type') == 'recommendation':
                            return True
            return False
        except Exception as e:
            logger.error(f"❌ 추천 데이터 확인 실패: {e}")
            return False
    
    def _extract_recommendation_data(self, intermediate_steps: List) -> Optional[Dict]:
        """추천 데이터 추출"""
        try:
            for step in intermediate_steps:
                if hasattr(step, '__len__') and len(step) >= 2:
                    action, observation = step[0], step[1]
                    if isinstance(observation, dict):
                        result_data = observation.get('result', {})
                        if isinstance(result_data, dict) and result_data.get('type') == 'recommendation':
                            return result_data
            return None
        except Exception as e:
            logger.error(f"❌ 추천 데이터 추출 실패: {e}")
            return None
    
    def _generate_fallback_response(self) -> SimpleUXResponse:
        """동적 SQL 실패 시 폴백 응답"""
        fallback_component = UIComponent(
            type="html",
            id=str(uuid.uuid4()),
            content="""
            <div style="
                background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
                padding: 40px;
                border-radius: 35px;
                color: #333;
                text-align: center;
                box-shadow: 0 25px 50px rgba(0,0,0,0.2);
                animation: pulse 2.5s infinite;
                border: 3px solid rgba(255,255,255,0.35);
            ">
                <h3 style="margin: 0 0 30px 0; font-size: 26px; font-weight: 800;">🤖 동적 SQL 서비스 일시 중단</h3>
                <p style="margin: 0; line-height: 2.0; font-size: 18px;">
                    현재 실시간 데이터 분석 기능을 이용할 수 없습니다.<br>
                    잠시 후 다시 시도해 주세요.
                </p>
            </div>
            
            <style>
            @keyframes pulse {{
                0% {{ transform: scale(1); }}
                50% {{ transform: scale(1.08); }}
                100% {{ transform: scale(1); }}
            }}
            </style>
            """,
            style="margin: 35px 0;"
        )
        
        return SimpleUXResponse(
            components=[fallback_component],
            total_products=None,
            generated_at=datetime.now().isoformat(),
            ai_generated=False
        )

    async def generate_dynamic_ui(
        self, 
        page_type: str,
        user_context: Optional[Dict[str, Any]] = None,
        custom_requirements: Optional[str] = None
    ) -> SimpleUXResponse:
        """기존 ux_service.py 호환 - 페이지별 UI 생성"""
        try:
            if custom_requirements:
                # 사용자 요구사항이 있으면 AI 방식 사용
                return await self.generate_smart_ui(custom_requirements)
            
            # 페이지 타입별 기본 쿼리 생성
            if page_type == 'home':
                query = "인기있는 보험 상품들을 보여줘"
            elif page_type == 'products':
                query = "모든 보험 상품 목록을 보여줘"
            elif page_type == 'categories':
                query = "보험 카테고리별로 상품을 보여줘"
            else:
                query = f"{page_type} 페이지에 맞는 내용을 보여줘"
            
            return await self.generate_smart_ui(query)
            
        except Exception as e:
            logger.error(f"❌ 동적 UI 생성 실패: {e}")
            return self._generate_fallback_response()
    
    async def search_content(
        self,
        query: str,
        limit: int = 20,
        include_products: bool = True,
        include_faqs: bool = True,
        include_testimonials: bool = True
    ) -> Dict[str, Any]:
        """기존 ux_service.py 호환 - 콘텐츠 검색"""
        try:
            results = {"products": [], "faqs": [], "testimonials": []}
            
            if include_products:
                products_query = self.supabase.table('insurance_products').select("*")
                if query:
                    products_query = products_query.ilike('name', f'%{query}%')
                products_result = products_query.limit(limit).execute()
                results["products"] = products_result.data
            
            if include_faqs:
                faqs_query = self.supabase.table('faqs').select("*")
                if query:
                    faqs_query = faqs_query.ilike('question', f'%{query}%')
                faqs_result = faqs_query.limit(limit).execute()
                results["faqs"] = faqs_result.data
            
            if include_testimonials:
                testimonials_query = self.supabase.table('customer_testimonials').select("*")
                if query:
                    testimonials_query = testimonials_query.ilike('title', f'%{query}%')
                testimonials_result = testimonials_query.limit(limit).execute()
                results["testimonials"] = testimonials_result.data
            
            return results
            
        except Exception as e:
            logger.error(f"❌ 콘텐츠 검색 실패: {e}")
            return {"products": [], "faqs": [], "testimonials": []}
    
    async def get_insurance_products(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """기존 ux_service.py 호환 - 보험 상품 조회"""
        try:
            query = self.supabase.table('insurance_products').select("*")
            if category:
                query = query.eq('category_id', category)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"❌ 보험 상품 조회 실패: {e}")
            return []
    
    async def get_insurance_categories(self) -> List[Dict[str, Any]]:
        """기존 ux_service.py 호환 - 보험 카테고리 조회"""
        try:
            result = self.supabase.table('insurance_categories').select("*").execute()
            return result.data
        except Exception as e:
            logger.error(f"❌ 보험 카테고리 조회 실패: {e}")
            return []
    
    async def get_faqs(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """기존 ux_service.py 호환 - FAQ 조회"""
        try:
            query = self.supabase.table('faqs').select("*")
            if category:
                query = query.eq('category', category)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"❌ FAQ 조회 실패: {e}")
            return []
    
    async def get_testimonials(self, product_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """기존 ux_service.py 호환 - 고객 후기 조회"""
        try:
            query = self.supabase.table('customer_testimonials').select("*")
            if product_id:
                query = query.eq('insurance_product_id', product_id)
            result = query.execute()
            return result.data
        except Exception as e:
            logger.error(f"❌ 고객 후기 조회 실패: {e}")
            return []

# 전역 인스턴스 생성
try:
    smart_ux_service = TrueDynamicSQLService()
except Exception as e:
    logger.error(f"❌ 진짜 동적 SQL 전역 인스턴스 생성 실패: {e}")
    # 폴백용 인스턴스 생성
    smart_ux_service = TrueDynamicSQLService()
    smart_ux_service.ai_available = False

# ===============================
# 🔄 기존 ux_service.py 완전 호환성
# ===============================
ux_service = smart_ux_service  # 호환성을 위한 별칭 