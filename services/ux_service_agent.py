from typing import List, Dict, Any, Optional
import logging
import asyncio
from datetime import datetime

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

# 🛠️ AI가 사용할 Tool들 정의
class InsuranceProductSearchTool(BaseTool):
    """AI가 직접 DB를 쿼리하는 보험 상품 검색 도구"""
    name = "search_insurance_products"
    description = "사용자의 연령과 관심사에 맞는 보험 상품을 DB에서 검색합니다. 연령 필터링이 자동으로 적용됩니다."
    
    # Pydantic 필드로 supabase 클라이언트 선언
    supabase: Any = Field(default=None, exclude=True)
    
    def __init__(self):
        super().__init__()
        supabase_manager.connect()
        # super().__init__() 후에 object.__setattr__ 사용
        object.__setattr__(self, 'supabase', get_supabase_client())
    
    class SearchInput(BaseModel):
        age: Optional[int] = Field(description="사용자 나이 (연령 필터링용)")
        keywords: List[str] = Field(description="검색할 키워드들")
        max_results: int = Field(default=3, description="최대 결과 개수")
    
    args_schema = SearchInput
    
    def _run(self, age: Optional[int] = None, keywords: List[str] = [], max_results: int = 3) -> List[Dict]:
        """🎯 스마트 DB 쿼리 실행"""
        try:
            query = self.supabase.table('insurance_products').select(
                'id, name, description, base_price, max_coverage, age_limit_min, age_limit_max, tags, features'
            )
            
            # 🔍 연령 필터링 (핵심!)
            if age is not None:
                query = query.lte('age_limit_min', age).gte('age_limit_max', age)
                logger.info(f"🎯 연령 필터링 적용: {age}세")
            
            # 🔍 키워드 필터링
            if keywords:
                for keyword in keywords:
                    query = query.or_(f'name.ilike.%{keyword}%,description.ilike.%{keyword}%')
                logger.info(f"🔍 키워드 필터링: {keywords}")
            
            result = query.limit(max_results).execute()
            filtered_products = result.data if result.data else []
            
            logger.info(f"✅ AI Tool 결과: {len(filtered_products)}개 상품 발견")
            for product in filtered_products:
                logger.info(f"   - {product['name']} (연령: {product['age_limit_min']}-{product['age_limit_max']}세)")
            
            return filtered_products
            
        except Exception as e:
            logger.error(f"❌ DB 쿼리 실패: {e}")
            return []
    
    async def _arun(self, *args, **kwargs):
        return self._run(*args, **kwargs)

class SmartAIUXService:
    """🤖 AI Agent 기반 스마트 UX 서비스"""
    
    def __init__(self):
        logger.info("🏗️ SmartAIUXService.__init__() 시작")
        
        try:
            logger.info("📊 Supabase 연결 중...")
            supabase_manager.connect()
            self.supabase = get_supabase_client()
            logger.info("✅ Supabase 연결 완료")
        except Exception as e:
            logger.error(f"❌ Supabase 연결 실패: {e}")
        
        # OpenAI 초기화
        logger.info(f"🔑 OpenAI API 키 확인: {'설정됨' if settings.openai_api_key else '❌ 없음'}")
        
        if settings.openai_api_key:
            try:
                logger.info("🤖 ChatOpenAI 초기화 중...")
                self.llm = ChatOpenAI(
                    openai_api_key=settings.openai_api_key,
                    model_name=settings.openai_model,
                    temperature=0.7,  # 창의성을 위해 조금 높게
                    max_tokens=2000
                )
                self.ai_available = True
                logger.info("✅ AI Agent 초기화 성공")
            except Exception as e:
                logger.error(f"❌ ChatOpenAI 초기화 실패: {e}")
                import traceback
                traceback.print_exc()
                self.ai_available = False
        else:
            self.ai_available = False
            logger.warning("❌ AI Agent 비활성화 (API 키 없음)")
        
        logger.info(f"🏁 SmartAIUXService 초기화 완료 - AI Available: {self.ai_available}")
    
    async def generate_smart_ui(self, user_request: str) -> SimpleUXResponse:
        """🧠 AI Agent가 사용자 요청을 분석하고 적절한 Tool을 사용하여 UI 생성"""
        logger.info(f"🚀 generate_smart_ui 호출됨 - AI Available: {self.ai_available}, Request: {user_request}")
        
        try:
            if not self.ai_available:
                logger.warning("⚠️ AI Agent 비활성화 상태로 폴백 응답 반환")
                return self._generate_fallback_response()
            
            logger.info(f"🤖 AI Agent 시작: {user_request}")
            
            # 🛠️ Tool 초기화
            logger.info("🔧 Tool 초기화 중...")
            search_tool = InsuranceProductSearchTool()
            tools = [search_tool]
            logger.info("✅ Tool 초기화 완료")
            
            # 🤖 AI Agent 프롬프트 설정
            logger.info("📝 AI Agent 프롬프트 설정 중...")
            prompt = ChatPromptTemplate.from_messages([
                ("system", """
                당신은 한국 보험 전문 AI Agent입니다. 사용자의 요청을 분석하여 적절한 도구를 사용해 맞춤형 UI를 생성합니다.

                **역할**:
                1. 사용자 요청에서 연령, 관심사, UI 스타일 선호도를 분석
                2. search_insurance_products Tool을 사용해 적절한 상품을 검색
                3. 검색 결과를 바탕으로 사용자 친화적인 UI 생성

                **중요 규칙**:
                - 연령이 명시되면 반드시 해당 연령이 가입 가능한 상품만 검색
                - "5살", "어린이" → 0~18세 가입 가능 상품만
                - "20대" → 20~29세 최적 상품
                - 귀여운 스타일이 요청되면 밝은 색상과 이모지 사용
                
                **응답 형식**: 
                검색한 상품 정보를 바탕으로 HTML UI 코드를 생성하여 응답하세요.
                """),
                ("user", "{input}"),
                ("assistant", "{agent_scratchpad}")
            ])
            logger.info("✅ 프롬프트 설정 완료")
            
            # 🤖 Agent 생성 및 실행
            logger.info("🏗️ AI Agent 생성 중...")
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=tools,
                prompt=prompt
            )
            logger.info("✅ AI Agent 생성 완료")
            
            logger.info("🎯 AgentExecutor 생성 중...")
            agent_executor = AgentExecutor(
                agent=agent,
                tools=tools,
                verbose=True,
                max_iterations=3
            )
            logger.info("✅ AgentExecutor 생성 완료")
            
            # 🚀 Agent 실행
            logger.info("🚀 AI Agent 실행 시작...")
            result = await agent_executor.ainvoke({"input": user_request})
            logger.info(f"🎉 AI Agent 실행 완료: {len(str(result))} 문자 결과")
            
            logger.info(f"🎉 AI Agent 완료: {result.get('output', '')[:100]}...")
            
            # 📝 결과를 UIComponent로 변환
            logger.info("📝 UI 컴포넌트 변환 중...")
            components = self._convert_agent_result_to_components(
                user_request, 
                result.get('output', ''),
                result.get('intermediate_steps', [])
            )
            logger.info(f"✅ UI 컴포넌트 변환 완료: {len(components)}개 컴포넌트")
            
            final_response = SimpleUXResponse(
                components=components,
                total_products=None,
                generated_at=datetime.now().isoformat(),
                ai_generated=True
            )
            logger.info("🏁 AI Agent 응답 생성 완료 - ai_generated=True")
            return final_response
            
        except Exception as e:
            logger.error(f"❌ AI Agent 실행 실패: {e}")
            import traceback
            logger.error(f"❌ 스택 트레이스: {traceback.format_exc()}")
            return self._generate_fallback_response()
    
    def _convert_agent_result_to_components(
        self, 
        user_request: str, 
        agent_output: str, 
        intermediate_steps: List
    ) -> List[UIComponent]:
        """AI Agent 결과를 UI 컴포넌트로 변환"""
        components = []
        
        # 🧠 Agent가 실행한 Tool 결과 분석
        searched_products = []
        for step in intermediate_steps:
            if len(step) >= 2 and hasattr(step[0], 'tool') and step[0].tool == 'search_insurance_products':
                searched_products = step[1] if isinstance(step[1], list) else []
                break
        
        # 📋 헤더 컴포넌트
        is_cute_request = any(word in user_request.lower() for word in ['5살', '어린이', '귀엽게'])
        
        if is_cute_request:
            header_style = "text-align: center; padding: 2rem; background: linear-gradient(135deg, #ff6b6b 0%, #4ecdc4 100%); color: white; border-radius: 20px; margin-bottom: 2rem;"
            emoji = "🎈"
        else:
            header_style = "text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border-radius: 12px; margin-bottom: 2rem;"
            emoji = "🤖"
        
        header_component = UIComponent(
            type="header",
            id="ai_agent_header",
            title=f"AI Agent 분석 결과",
            content=f"""
            <div style='{header_style}'>
                <h1 style='margin: 0; font-size: 2rem; font-weight: 700;'>{emoji} {user_request}</h1>
                <p style='margin: 1rem 0 0 0; font-size: 1.1rem;'>AI가 분석한 맞춤 결과입니다!</p>
            </div>
            """,
            style="",
            priority=1,
            data={"source": "ai_agent", "query": user_request}
        )
        components.append(header_component)
        
        # 📦 상품 결과 컴포넌트
        if searched_products:
            products_html = self._generate_smart_products_html(searched_products, is_cute_request)
            
            products_component = UIComponent(
                type="section",
                id="ai_searched_products",
                title=f"AI가 찾은 {len(searched_products)}개 상품",
                content=products_html,
                style="padding: 2rem; background: #f8f9fa; border-radius: 16px;",
                priority=2,
                data={"source": "ai_agent_search", "count": len(searched_products)}
            )
            components.append(products_component)
        
        # 🗨️ AI 분석 내용
        analysis_component = UIComponent(
            type="article",
            id="ai_analysis",
            title="AI 분석 내용",
            content=f"""
            <div style='background: white; padding: 1.5rem; border-radius: 12px; border-left: 4px solid #4ecdc4;'>
                <h3 style='margin: 0 0 1rem 0; color: #333;'>🧠 AI Agent 분석</h3>
                <p style='color: #666; line-height: 1.6; margin: 0;'>{agent_output}</p>
            </div>
            """,
            style="margin-top: 1rem;",
            priority=3,
            data={"source": "ai_agent_analysis"}
        )
        components.append(analysis_component)
        
        return components
    
    def _generate_smart_products_html(self, products: List[Dict[str, Any]], is_cute_style: bool = False) -> str:
        """AI가 검색한 상품들을 HTML로 변환"""
        if is_cute_style:
            card_style = "background: white; padding: 1.5rem; border-radius: 20px; box-shadow: 0 4px 12px rgba(255,107,107,0.2); border: 3px solid #ff6b6b; margin-bottom: 1.5rem;"
            price_style = "background: #ff6b6b; color: white; padding: 0.7rem 1.2rem; border-radius: 25px; font-size: 1.2rem; font-weight: 600;"
            emoji = "🎨"
        else:
            card_style = "background: white; padding: 1.5rem; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); border: 1px solid #e0e0e0; margin-bottom: 1.5rem;"
            price_style = "background: #667eea; color: white; padding: 0.5rem 1rem; border-radius: 20px; font-size: 1.1rem; font-weight: 600;"
            emoji = "🛡️"
        
        cards_html = ""
        for product in products:
            cards_html += f"""
            <div style='{card_style}'>
                <h3 style='margin: 0 0 1rem 0; color: #333; font-size: 1.4rem;'>{emoji} {product['name']}</h3>
                <div style='margin-bottom: 1rem;'>
                    <span style='{price_style}'>{product['base_price']:,.0f}원/월</span>
                </div>
                <p style='color: #666; margin-bottom: 1rem; line-height: 1.6;'>{product['description']}</p>
                <div style='background: #f8f9fa; padding: 1rem; border-radius: 8px;'>
                    <strong style='color: #333;'>📋 연령: {product['age_limit_min']}-{product['age_limit_max']}세</strong><br>
                    <strong style='color: #333;'>💰 최대 보장: {product['max_coverage']:,.0f}원</strong>
                </div>
            </div>
            """
        
        return f"<div>{cards_html}</div>"
    
    def _generate_fallback_response(self) -> SimpleUXResponse:
        """폴백 응답 생성"""
        return SimpleUXResponse(
            components=[
                UIComponent(
                    type="notice",
                    id="ai_unavailable",
                    title="AI 서비스 일시 중단",
                    content="<div style='text-align: center; padding: 2rem;'><p>AI Agent 서비스가 일시적으로 중단되었습니다.</p></div>",
                    style="background: #fff3cd; border-radius: 8px;",
                    priority=1
                )
            ],
            total_products=None,
            generated_at=datetime.now().isoformat(),
            ai_generated=False
        )

# 전역 인스턴스 생성
logger.info("🏗️ SmartAIUXService 전역 인스턴스 생성 중...")
try:
    smart_ux_service = SmartAIUXService()
    logger.info(f"✅ 전역 인스턴스 생성 완료 - AI Available: {smart_ux_service.ai_available}")
except Exception as e:
    logger.error(f"❌ 전역 인스턴스 생성 실패: {e}")
    # 폴백용 인스턴스 생성
    smart_ux_service = SmartAIUXService()
    smart_ux_service.ai_available = False 