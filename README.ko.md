# OpenAgentSearch (한국어 문서)

OpenAgentSearch는 자체 호스팅 가능한 웹 검색 API + MCP 도구 서버입니다.

기본 영문 문서: [README.md](README.md)

## 왜 이 프로젝트를 만들었나

에이전트 워크플로우에 웹 검색과 본문 추출이 필요했지만, 아래와 같은 방식은 피하고 싶었습니다.
- 내부 동작이 보이지 않는 블랙박스형 서비스
- 호출량이 늘수록 커지는 사용 비용
- 특정 벤더 도구에 강하게 묶이는 구조

이 프로젝트는 직접 통제 가능한 self-hosted 기반을 목표로 만들었고, 실행과 연동이 단순하도록 구성했습니다.

## 특장점

- 목적별 API 분리: 빠른 검색과 본문 추출을 분리해 사용 시나리오에 맞게 선택 가능
- 에이전트 연동 용이: FastMCP 기반 `openagentsearch.search`, `openagentsearch.extract` 제공
- 비용/지연 최적화: Redis 캐시로 반복 질의와 추출 비용 절감
- 기본 보안 내장: SSRF 검증, 도메인 정책, 도메인 단위 rate limit
- 운영 단순성: Docker Compose로 로컬/개인 서버에서 빠르게 구동 가능

## 할 수 있는 일

- `POST /v1/search`로 웹 검색
- `POST /v1/extract`로 URL 본문 추출
- MCP 도구 `openagentsearch.search`, `openagentsearch.extract` 사용

## 빠른 시작

필수:
- Docker Desktop (`docker compose`)
- Python 3.11+
- `uv`

실행:

```bash
docker compose up -d --build
```

확인:
- API 상태: `http://localhost:8000/health`
- API 메트릭: `http://localhost:8000/internal/metrics`
- SearXNG 예시: `http://localhost:8080/search?format=json&q=agent`

종료:

```bash
docker compose down
```

## 첫 API 호출

### 1) 빠른 검색(`mode=speed`)

```bash
curl -X POST "http://localhost:8000/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "open source search engine",
    "mode": "speed",
    "limit": 5
  }'
```

### 2) 검색 + 상위 결과 추출(`mode=balanced`)

```bash
curl -X POST "http://localhost:8000/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "llm agent memory architecture",
    "mode": "balanced",
    "limit": 5,
    "extract_top_n": 2,
    "max_extract_chars": 6000
  }'
```

### 3) 단일 URL 추출

```bash
curl -X POST "http://localhost:8000/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_chars": 20000
  }'
```

## API 요약

### `POST /v1/search`

요청 필드:
- `query` (필수)
- `mode` (`speed` | `balanced`, 기본 `speed`)
- `limit` (1..50)
- `page` (1 이상)
- `categories` (선택)
- `engines` (선택)
- `extract_top_n` (0..20)
- `max_extract_chars` (1..200000)

응답 핵심:
- `results[]` 검색 결과
- `extract` (balanced 추출 성공 시)
- `extract_error` (추출 실패 시)
- `cached` 캐시 여부

### `POST /v1/extract`

요청 필드:
- `url` (필수)
- `max_chars` (1..200000, 기본 20000)

응답 핵심:
- `markdown`
- `passages[]`
- `title`
- `content_hash`
- `cached`

### 주요 에러 코드

- `400` 입력 오류/요청 검증 실패
- `403` 도메인 정책 차단
- `429` 도메인 rate limit 초과
- `502` 외부 fetch/provider 오류

## MCP 서버

실행:

```bash
uv run --project apps/mcp python -m app.main
```

도구:
- `openagentsearch.search`
- `openagentsearch.extract`

환경 변수:
- `OAS_API_BASE_URL`
- `OAS_API_TIMEOUT_SECONDS`
- `OAS_AUTH_HEADER_NAME`
- `OAS_AUTH_HEADER_VALUE`

요청 단위 인증 헤더 override:
- `auth_header_name`
- `auth_header_value`

## 설정

주요 API 환경 변수:
- `REDIS_URL`
- `SEARXNG_BASE_URL`
- `SEARXNG_TIMEOUT_SECONDS`
- `SEARCH_CACHE_TTL_SECONDS`
- `EXTRACT_CACHE_TTL_SECONDS`
- `DOMAIN_POLICY_FILE`
- `EXTRACT_RATE_LIMIT_ENABLED`
- `EXTRACT_RATE_LIMIT_TOKENS_PER_SEC`
- `EXTRACT_RATE_LIMIT_BURST`
- `OAS_DISABLE_RATE_LIMIT`

정책 샘플:
- `infra/domain_policies.json`

## 테스트

```bash
uv sync --project apps/api
uv sync --project apps/mcp
uv run python -m unittest discover -s tests -v
```

통합 테스트:

PowerShell:

```powershell
$env:OAS_RUN_DOCKER_TESTS='1'
uv run python -m unittest tests.test_m1_stack_integration -v
```

Bash:

```bash
OAS_RUN_DOCKER_TESTS=1 uv run python -m unittest tests.test_m1_stack_integration -v
```
