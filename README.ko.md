# OpenAgentSearch (한국어 문서)

에이전트 워크플로우를 위한 자체 호스팅 웹 검색/추출 플랫폼입니다.
본 프로젝트는 바이브 코딩으로 구현했습니다.

기본 영문 문서: [README.md](README.md)

> OpenAgentSearch는 SearXNG 검색에 본문 추출, 안전 제어, MCP 도구를 결합합니다.

## 빠른 시작 (2분)

```bash
git clone <YOUR_REPO_URL>
cd OpenAgentSearch
docker compose up -d --build
```

이후 확인:

- API 상태: `http://localhost:8000/health`
- API 메트릭: `http://localhost:8000/internal/metrics`

## 목차

- [프로젝트 소개](#프로젝트-소개)
- [특장점](#특장점)
- [처음부터 끝까지 설정 가이드](#처음부터-끝까지-설정-가이드)
- [운영 및 설정](#운영-및-설정)
- [API 빠른 참조](#api-빠른-참조)
- [MCP 빠른 참조](#mcp-빠른-참조)
- [프로젝트 구조](#프로젝트-구조)

## 프로젝트 소개

OpenAgentSearch는 에이전트용 검색 레이어를 직접 통제 가능하게 만들기 위한 개인 오픈소스 프로젝트입니다.

만든 이유:

- 웹 검색과 본문 추출을 한 곳에서 처리하고 싶었음
- 블랙박스형 호스팅 API와 호출 비용 증가를 피하고 싶었음
- 에이전트 클라이언트와 쉽게 붙는 MCP 인터페이스가 필요했음

이 프로젝트는 `SearXNG`를 검색 provider로 사용하고, 그 위에 실사용 레이어를 추가합니다.

- 구조화된 추출 결과(`markdown`, `passages`, `content_hash`)
- 캐시 및 안전 제어
- 에이전트 직접 연동용 MCP 도구

## 특장점

- API 모드 분리: `speed`(SERP 전용), `balanced`(SERP + 추출)
- LLM 파이프라인 후처리에 맞는 추출 결과 구조 제공
- 검색/추출 모두 Redis 캐시 지원
- 보안 기본기 내장: SSRF 차단, 도메인 정책, 도메인별 rate limit
- FastMCP thin-wrapper 구조로 MCP 연동 단순화
- Docker Compose 기반의 간단한 배포

## 처음부터 끝까지 설정 가이드

### A. 사전 준비

1. Docker Desktop (`docker compose`)
2. Python 3.11+
3. `uv`
4. Git

### B. 클론

```bash
git clone <YOUR_REPO_URL>
cd OpenAgentSearch
```

### C. 서비스 실행 (로컬/호스팅 공통)

1. 스택 실행:

```bash
docker compose up -d --build
```

2. 상태 확인:

```bash
docker compose ps
```

3. 서비스 상태 확인:

- API 상태: `http://localhost:8000/health`
- API 메트릭: `http://localhost:8000/internal/metrics`
- SearXNG 샘플: `http://localhost:8080/search?format=json&q=agent`

4. 종료:

```bash
docker compose down
```

### D. API 확인

1. 검색(speed 모드):

```bash
curl -X POST "http://localhost:8000/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "latest ai news",
    "mode": "speed",
    "limit": 5
  }'
```

2. URL 본문 추출:

```bash
curl -X POST "http://localhost:8000/v1/extract" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "max_chars": 20000
  }'
```

### E. 호스팅 메모

기본 포트:

| 포트 | 서비스 | 비고 |
|---|---|---|
| `8000` | OpenAgentSearch API | 외부 진입점(리버스 프록시 뒤 운영 권장) |
| `8080` | SearXNG | 가능하면 비공개 운영 |

권장 운영 방식:

- API만 리버스 프록시(Nginx/Caddy) 뒤로 공개
- HTTPS/TLS 적용
- 불필요한 방화벽 포트 차단
- SearXNG는 내부 네트워크에서만 접근

### F. MCP 연결

1. MCP 서버 실행:

```bash
uv run --project apps/mcp python -m app.main
```

2. 환경 변수:

- `OAS_API_BASE_URL`
- `OAS_API_TIMEOUT_SECONDS`
- `OAS_AUTH_HEADER_NAME` (선택)
- `OAS_AUTH_HEADER_VALUE` (선택)

3. MCP 클라이언트 실행 위치에 맞춰 `OAS_API_BASE_URL` 설정:

- 호스트 OS에서 실행: `http://localhost:8000`
- 동일 Docker 네트워크에서 실행: `http://api:8000`

4. MCP 설정 예시:

```json
{
  "mcpServers": {
    "openagentsearch": {
      "command": "uv",
      "args": ["run", "--project", "apps/mcp", "python", "-m", "app.main"],
      "env": {
        "OAS_API_BASE_URL": "http://localhost:8000",
        "OAS_API_TIMEOUT_SECONDS": "20"
      }
    }
  }
}
```

5. 아래 도구가 보이는지 확인:

- `openagentsearch.search`
- `openagentsearch.extract`

## 운영 및 설정

주요 API 환경 변수:

| 변수 | 기본값 | 설명 |
|---|---|---|
| `REDIS_URL` | - | Redis 연결 문자열 (예: `redis://redis:6379/0`) |
| `SEARXNG_BASE_URL` | `http://searxng:8080` | SearXNG 기본 URL |
| `SEARXNG_TIMEOUT_SECONDS` | `12` | 업스트림 타임아웃 |
| `SEARCH_CACHE_TTL_SECONDS` | `120` | 검색 캐시 TTL |
| `EXTRACT_CACHE_TTL_SECONDS` | `600` | 추출 캐시 TTL |
| `DOMAIN_POLICY_FILE` | - | 도메인 정책 파일 경로 |
| `EXTRACT_RATE_LIMIT_ENABLED` | `true` | 도메인별 rate limit 활성화 |
| `EXTRACT_RATE_LIMIT_TOKENS_PER_SEC` | `1.0` | 초당 토큰 리필 속도 |
| `EXTRACT_RATE_LIMIT_BURST` | `3` | 버스트 토큰 크기 |
| `OAS_DISABLE_RATE_LIMIT` | `false` | rate limit 강제 비활성화 |

정책 파일 예시:

- `infra/domain_policies.json`

## API 빠른 참조

`POST /v1/search`

- 입력: `query`, `mode`, `limit`, `page`, `categories`, `engines`, `extract_top_n`, `max_extract_chars`
- 출력: `query`, `mode`, `limit`, `page`, `results[]`, `cached`
- `balanced` 모드에서는 `results[].extract` 포함 가능

`POST /v1/extract`

- 입력: `url`, `max_chars`
- 출력: `url`, `markdown`, `passages[]`, `title`, `content_hash`, `cached`

공통 오류 코드:

- `400` 잘못된 입력 또는 요청 검증 실패
- `403` 도메인 정책에 의해 차단됨
- `429` 도메인 rate limit 초과
- `502` 업스트림/provider/fetch 실패

## MCP 빠른 참조

도구:

- `openagentsearch.search`
- `openagentsearch.extract`

`openagentsearch.search` 주요 인자:

- `query`, `mode`, `limit`, `page`, `extract_top_n`, `max_extract_chars`

`openagentsearch.extract` 주요 인자:

- `url`, `max_chars`

요청 단위 인증 헤더 오버라이드:

- `auth_header_name`
- `auth_header_value`

## 프로젝트 구조

- `apps/api`: FastAPI 서비스
- `apps/mcp`: FastMCP 서비스
- `infra`: 인프라 및 정책 파일
- `tests`: 단위/통합 테스트
- `plan/PLAN_v1.md`: 마일스톤/진행 문서
