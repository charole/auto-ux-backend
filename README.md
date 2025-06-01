# 🤖 하이브리드 SQL Agent 기반 보험 추천 시스템

## 🎯 프로젝트 개요

**자연어를 SQL로 자동 변환하여 실시간 DB와 상호작용하는 지능형 보험 추천 시스템**

사용자가 자연어로 질문하면 LangChain의 OpenAI Function Calling을 통해 자동으로 적절한 SQL 쿼리를 생성하고, Supabase 데이터베이스에서 실시간 데이터를 조회하여 동적 HTML UI로 응답을 제공합니다.

## ⭐ 핵심 기능

### 🧠 하이브리드 SQL Agent

- **자연어 → SQL 자동 변환**: "가장 비싼 보험료는?" → MAX 쿼리 자동 생성
- **복합 질문 처리**: "30대에게 적합한 보험 상품은?" → 조건부 검색 쿼리 생성
- **통계 분석**: COUNT, AVG, MAX, MIN 자동 계산
- **랭킹 처리**: TOP N, 인기 순위 자동 정렬

### 🔄 실시간 DB 연동

- **Supabase PostgreSQL** 실시간 쿼리
- **다중 테이블 지원**: insurance_products, customer_testimonials, faqs, users
- **안전한 쿼리**: REST API 기반 SQL Injection 방지
- **성능 최적화**: 결과 수 제한 및 캐싱

### 🎨 동적 UI 생성

- **매번 다른 스타일**: 랜덤 색상 스키마와 애니메이션
- **스타일링 요청 지원**: "예쁘게 보여주세요", "3줄 요약으로"
- **반응형 HTML**: 모던 CSS와 애니메이션 적용

## 🛠️ 기술 스택

### Backend

- **FastAPI**: RESTful API 서버
- **LangChain**: OpenAI Function Calling 기반 SQL Agent
- **OpenAI GPT-4**: 자연어 이해 및 SQL 생성
- **Supabase**: PostgreSQL 데이터베이스
- **Python 3.8+**: 메인 개발 언어

### Frontend

- **Next.js 14**: React 프레임워크
- **TypeScript**: 타입 안전성
- **Tailwind CSS**: 스타일링
- **Responsive Design**: 모바일 최적화

## 🚀 주요 질문 처리 예시

### 📊 통계/집계 질문

```
사용자: "보험 상품이 총 몇개 있어?"
AI: 보험 상품은 총 47개가 있습니다.

사용자: "가장 비싼 보험료는 얼마야?"
AI: 가장 비싼 보험료는 5,000,000원인 '즉시연금보험' 상품입니다.

사용자: "평균 보험료를 알려줘"
AI: 평균 보험료는 391,595.74원입니다. 총 47개의 보험 상품이 있습니다.
```

### 🔍 검색/필터 질문

```
사용자: "30대에게 적합한 보험 상품은?"
AI: 30대에게 적합한 보험 상품은 다음과 같습니다:
    1. 안심생명보험 - 150,000원
    2. 프리미엄 건강보험 - 200,000원
    ...

사용자: "보험료가 5만원 이하인 상품들은?"
AI: 보험료가 5만원 이하인 상품들은 총 4개가 있습니다:
    1. 착한암보험 - 45,000원
    2. 국내여행보험 - 25,000원
    ...
```

### 🏆 랭킹 질문

```
사용자: "인기 상품 top 3를 보여줘"
AI: 인기 상품 상위 3개:
    1. 즉시연금보험 - 5,000,000원
    2. 프리미엄 자동차보험 - 1,800,000원
    3. 전기차 전용보험 - 1,400,000원
```

## 📁 프로젝트 구조

```
auto-ux-project/
├── auto-ux-backend/          # FastAPI 백엔드
│   ├── services/
│   │   └── ux_service_agent.py    # 🤖 하이브리드 SQL Agent 핵심
│   ├── routers/
│   │   └── ux.py             # API 엔드포인트
│   ├── database/
│   │   └── client.py         # Supabase 연결
│   └── main.py               # FastAPI 앱
└── auto-ux-frontend/         # Next.js 프론트엔드
    ├── src/services/
    │   └── uxService.ts      # API 클라이언트
    └── src/components/       # React 컴포넌트
```

## 🧪 테스트 결과

**전체 시스템 테스트: 10/10 성공 (100%)**

| 질문 유형   | 테스트 질문                    | 결과         |
| ----------- | ------------------------------ | ------------ |
| 📊 통계     | 보험 상품 개수, 최고가, 평균가 | ✅ 모두 성공 |
| 🔍 검색     | 연령별, 가격별, 인기도별 검색  | ✅ 모두 성공 |
| 🗣️ 대화     | 인사말, 절차 문의              | ✅ 모두 성공 |
| 🎨 스타일링 | 예쁘게 보여주기, 요약 요청     | ✅ 모두 성공 |

## 🎯 Q&A 체인 vs SQL Agent 비교

| 특징          | Q&A 체인         | **하이브리드 SQL Agent** |
| ------------- | ---------------- | ------------------------ |
| **질문 처리** | 단순 조회        | ✅ 복합 질문 처리        |
| **쿼리 생성** | 미리 정의된 패턴 | ✅ 동적 SQL 자동 생성    |
| **확장성**    | 제한적           | ✅ 무제한 확장 가능      |
| **정확도**    | 패턴 매칭        | ✅ LLM 컨텍스트 이해     |

## 🚀 설치 및 실행

### 1. 환경 설정

```bash
# 백엔드 의존성 설치
cd auto-ux-backend
pip install -r requirements.txt

# 프론트엔드 의존성 설치
cd ../auto-ux-frontend
npm install
```

### 2. 환경 변수 설정

```bash
# auto-ux-backend/.env
OPENAI_API_KEY=your_openai_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
```

### 3. 실행

```bash
# 백엔드 실행
cd auto-ux-backend
uvicorn main:app --reload --port 8000

# 프론트엔드 실행
cd auto-ux-frontend
npm run dev
```

## 🔧 API 엔드포인트

### 메인 엔드포인트

```
GET /api/v1/ux/generate-ui-smart?query={사용자_질문}
```

**응답 예시:**

```json
{
  "components": [
    {
      "type": "html",
      "id": "uuid",
      "title": null,
      "content": "<div>동적 HTML 콘텐츠</div>",
      "style": "margin: 10px 0;",
      "priority": 1,
      "data": {}
    }
  ],
  "ai_generated": true,
  "generated_at": "2025-06-01T18:44:56.704000"
}
```

## 🎨 UI 특징

- **동적 색상 스키마**: 매번 다른 그라데이션과 색상 조합
- **CSS 애니메이션**: slideInUp, fadeIn 등 모던 애니메이션
- **반응형 디자인**: 모바일/데스크톱 최적화
- **접근성**: 적절한 색상 대비와 폰트 크기

## 📈 성능 최적화

- **쿼리 결과 제한**: 대용량 데이터 처리 최적화
- **비동기 처리**: FastAPI async/await 활용
- **에러 핸들링**: 포괄적인 예외 처리 및 로깅
- **캐싱**: Supabase 클라이언트 재사용

## 🔐 보안 특징

- **SQL Injection 방지**: Supabase REST API 사용
- **API 키 보안**: 환경 변수 기반 설정
- **CORS 정책**: 적절한 도메인 제한
- **입력 검증**: 사용자 입력 파라미터 검증

## 🤖 하이브리드 SQL Agent 작동 원리

1. **사용자 질문 분석**: OpenAI GPT-4가 자연어 의도 파악
2. **쿼리 타입 결정**: 통계/검색/랭킹/대화 등 자동 분류
3. **SQL 파라미터 생성**: 테이블, 컬럼, 조건 자동 생성
4. **Supabase 쿼리**: REST API로 안전한 데이터 조회
5. **결과 포맷팅**: 동적 HTML과 CSS로 결과 표시

## 📚 추가 개발 가능성

- **더 많은 테이블 연동**: 상품 리뷰, 보험사 정보 등
- **고급 통계 분석**: 트렌드 분석, 예측 모델링
- **다국어 지원**: 영어, 중국어 등 다양한 언어
- **음성 인터페이스**: 음성 질문/답변 기능
- **실시간 채팅**: WebSocket 기반 실시간 상담

---

**🎉 하이브리드 SQL Agent를 통해 자연어와 데이터베이스 사이의 완벽한 가교를 구축했습니다!**
