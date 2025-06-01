# Auto UX Backend

AI 기반 동적 UI/UX 추천 시스템의 백엔드 서버입니다. LangChain과 Supabase를 활용하여 사용자 요청에 따라 동적으로 UI 컴포넌트를 생성하고 보험 도메인에 특화된 UX 서비스를 제공합니다.

## 주요 기능

- 🤖 **AI 기반 동적 UI 생성**: LangChain과 OpenAI GPT를 활용한 실시간 UI 컴포넌트 생성
- 🏦 **보험 도메인 특화**: 보험 상품, 청구, 상담 등 보험 업무에 최적화된 UX 제공
- 📊 **실시간 데이터 연동**: Supabase 데이터베이스와 실시간 연동
- 🎯 **개인화 서비스**: 사용자 프로필 기반 맞춤형 UI 생성
- 📈 **UX 메트릭 추적**: 사용자 행동 분석 및 UI 효과 측정

## 기술 스택

- **Framework**: FastAPI (Python 3.11+)
- **AI/ML**: LangChain, OpenAI GPT-3.5-turbo
- **Database**: Supabase (PostgreSQL)
- **Authentication**: Supabase Auth
- **Deployment**: Uvicorn ASGI Server

## 설치 및 실행

### 1. 의존성 설치

```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 변수들을 설정하세요:

```env
# Supabase 설정
SUPABASE_URL=your_supabase_url_here
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_KEY=your_supabase_service_key_here

# OpenAI API 설정
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-3.5-turbo

# 서버 설정
HOST=0.0.0.0
PORT=8000
DEBUG=true
ENVIRONMENT=development
```

### 3. 데이터베이스 설정

Supabase에서 제공된 SQL 스크립트를 실행하여 테이블을 생성하세요:

```bash
# database/schema.sql 파일의 내용을 Supabase SQL 에디터에서 실행
```

### 4. 서버 실행

```bash
# 개발 서버 실행
python main.py

# 또는 uvicorn 직접 사용
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

서버가 시작되면 다음 주소에서 확인할 수 있습니다:

- API 문서: http://localhost:8000/docs
- 헬스 체크: http://localhost:8000/health

## API 엔드포인트

### 메인 엔드포인트

#### 동적 UI 생성

```http
POST /api/v1/insurance-ux/generate-ui
```

사용자 요청에 따라 동적으로 UI 컴포넌트를 생성합니다.

**파라미터:**

- `page_type`: 페이지 타입 (home, products, claim, mypage, consultation, faq)
- `user_id`: 사용자 ID (선택)
- `product_id`: 상품 ID (선택)
- `custom_requirements`: 커스텀 요구사항 (선택)

**응답 예시:**

```json
{
  "components": [
    {
      "type": "hero_section",
      "id": "hero",
      "title": "보험 상품 추천",
      "content": "맞춤형 보험 상품을 확인하세요",
      "style": "primary",
      "priority": 1
    }
  ],
  "layout": {
    "type": "stack",
    "spacing": "medium"
  },
  "accessibility": {
    "high_contrast": false,
    "large_text": false
  }
}
```

### 데이터 조회 엔드포인트

#### 보험 상품 목록

```http
GET /api/v1/insurance-ux/products?category={category}&limit={limit}
```

#### 보험 카테고리 목록

```http
GET /api/v1/insurance-ux/categories
```

#### 사용자 보험 가입 정보

```http
GET /api/v1/insurance-ux/user/{user_id}/policies
```

#### 사용자 청구 내역

```http
GET /api/v1/insurance-ux/user/{user_id}/claims
```

#### FAQ 목록

```http
GET /api/v1/insurance-ux/faqs?category={category}
```

#### 고객 후기

```http
GET /api/v1/insurance-ux/testimonials?limit={limit}
```

### 레거시 호환성 엔드포인트

#### 기존 UX 추천

```http
POST /api/v1/insurance-ux/legacy/recommend-ux
```

기존 프론트엔드와의 호환성을 위한 엔드포인트입니다.

## 프로젝트 구조

```
auto-ux-backend/
├── main.py              # FastAPI 앱 진입점
├── requirements.txt     # Python 의존성
├── config/
│   └── settings.py      # 설정 관리
├── database/
│   ├── client.py        # Supabase 클라이언트
│   └── schema.sql       # 데이터베이스 스키마
├── models/              # 데이터 모델
├── routers/
│   └── ux_router.py     # UX 관련 라우터
├── schemas/
│   ├── request.py       # 요청 스키마
│   └── response.py      # 응답 스키마
├── services/
│   └── ux_service.py    # UX 서비스 로직
└── langchain/
    ├── chain.py         # LangChain 체인
    └── prompt.py        # 프롬프트 템플릿
```

## 개발 가이드

### 새로운 컴포넌트 타입 추가

1. `schemas/response.py`에서 컴포넌트 타입 정의
2. `services/ux_service.py`에서 생성 로직 구현
3. 프론트엔드에서 렌더링 로직 추가

### 새로운 페이지 타입 추가

1. `services/ux_service.py`의 `_get_page_requirements()` 메서드에 요구사항 추가
2. `_collect_page_data()` 메서드에 데이터 수집 로직 추가
3. 필요시 라우터에 전용 엔드포인트 추가

### 프롬프트 최적화

1. `services/ux_service.py`의 `ui_generation_prompt` 템플릿 수정
2. 테스트를 통해 생성 품질 검증
3. 필요시 OpenAI 모델 파라미터 조정

## 배포

### 프로덕션 설정

1. 환경 변수 `ENVIRONMENT=production` 설정
2. 강력한 `SECRET_KEY` 생성
3. `ALLOWED_ORIGINS`를 실제 도메인으로 제한
4. 로그 레벨을 `WARNING` 또는 `ERROR`로 설정

### Docker 배포 (예정)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 모니터링

- 헬스 체크: `/health`
- API 문서: `/docs`
- 로그 파일: `app.log` (프로덕션)

## 문제 해결

### 자주 발생하는 문제

1. **Supabase 연결 실패**

   - URL과 키가 올바른지 확인
   - 네트워크 연결 상태 확인

2. **OpenAI API 오류**

   - API 키 유효성 확인
   - 할당량 초과 여부 확인

3. **CORS 오류**
   - `ALLOWED_ORIGINS` 설정 확인
   - 프론트엔드 URL이 허용 목록에 있는지 확인

### 로그 확인

```bash
# 실시간 로그 확인
tail -f app.log

# 에러 로그만 확인
grep ERROR app.log
```

## 기여

1. 이슈 생성
2. 기능 브랜치 생성
3. 변경사항 커밋
4. 풀 리퀘스트 생성

## 라이센스

MIT License
