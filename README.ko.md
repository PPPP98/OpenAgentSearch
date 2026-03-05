# OpenAgentSearch (한국어 문서)

에이전트 워크플로우를 위한 자체 호스팅 웹 검색/추출 플랫폼입니다.
본 프로젝트는 바이브 코딩으로 구현했습니다.

기본 영문 문서: [README.md](README.md)

> OpenAgentSearch는 SearXNG 검색에 본문 추출, 안전 제어, MCP 도구를 결합합니다.

## 빠른 시작 (2분)

```bash
git clone https://github.com/PPPP98/OpenAgentSearch.git
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
- 결정론적 리랭킹(제목/스니펫/도메인/경로/다양성 신호)
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
git clone https://github.com/PPPP98/OpenAgentSearch.git
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
    "limit": 5,
    "language": "en",
    "time_range": "month",
    "safesearch": 1
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

### F. MCP 연결 (실전 가이드)

여기서 많이 막힙니다. `apps/mcp`는 별도 Python 의존성을 사용하므로, MCP 클라이언트 연결 전에 해당 폴더 기준으로 의존성 동기화를 먼저 해야 합니다.

1. API를 먼저 실행(필수):

```bash
docker compose up -d --build
```

2. `apps/mcp` 의존성 설치/동기화:

```bash
uv sync --project apps/mcp --frozen --no-dev
```

환경에 따라 lock 기반 설치가 실패하면 아래를 사용:

```bash
uv sync --project apps/mcp
```

3. MCP 서버 단독 실행 테스트:

```bash
uv run --project apps/mcp python -m app.main
```

에러 없이 실행되면 `Ctrl+C`로 종료합니다.

4. 실행 위치에 맞게 `OAS_API_BASE_URL` 설정:

- MCP 클라이언트를 호스트 OS에서 실행: `http://localhost:8000`
- MCP 클라이언트를 같은 Docker 네트워크에서 실행: `http://api:8000`

5. MCP 클라이언트 설정 파일(`mcp.json` 또는 동등한 설정)에 서버 등록:

중요 경로 규칙:
- `--project`에는 절대경로를 쓰는 것을 권장합니다. (클라이언트의 현재 작업 디렉터리 영향 제거)
- Windows는 `\\` 이스케이프 또는 `/` 경로를 사용할 수 있습니다.

Windows 예시 (`C:/path/to/OpenAgentSearch`):

```json
{
  "mcpServers": {
    "openagentsearch": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "C:/path/to/OpenAgentSearch/apps/mcp",
        "python",
        "-m",
        "app.main"
      ],
      "env": {
        "OAS_API_BASE_URL": "http://localhost:8000",
        "OAS_API_TIMEOUT_SECONDS": "20"
      }
    }
  }
}
```

macOS/Linux 예시:

```json
{
  "mcpServers": {
    "openagentsearch": {
      "command": "uv",
      "args": [
        "run",
        "--project",
        "/absolute/path/to/OpenAgentSearch/apps/mcp",
        "python",
        "-m",
        "app.main"
      ],
      "env": {
        "OAS_API_BASE_URL": "http://localhost:8000",
        "OAS_API_TIMEOUT_SECONDS": "20"
      }
    }
  }
}
```

6. MCP 클라이언트를 완전히 재시작한 뒤 도구 노출 확인:

- `openagentsearch.search`
- `openagentsearch.extract`

7. 자주 발생하는 문제:

- `uv` 명령을 찾을 수 없음: `uv` 설치 및 `PATH` 반영 확인
- `No module named fastmcp`/`httpx`: `uv sync --project apps/mcp` 재실행
- API 연결 실패(타임아웃/거부): `http://localhost:8000/health` 확인
- 도구가 안 뜸: `mcp.json` 문법/경로 확인 후 클라이언트 재시작

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
| `SEARCH_RERANK_TITLE_WEIGHT` | `1.5` | 쿼리-제목 겹침 가중치 |
| `SEARCH_RERANK_SNIPPET_WEIGHT` | `0.8` | 쿼리-스니펫 겹침 가중치 |
| `SEARCH_RERANK_DOMAIN_WEIGHT` | `0.5` | 도메인 prior 가중치 |
| `SEARCH_RERANK_PATH_WEIGHT` | `0.35` | URL 경로 품질 가중치 |
| `SEARCH_RERANK_DIVERSITY_WEIGHT` | `0.35` | 동일 도메인 다양성 패널티 가중치 |
| `SEARCH_RERANK_SOURCE_SCORE_WEIGHT` | `0.05` | 업스트림 점수 반영 가중치 |
| `SEARCH_RERANK_DOMAIN_PRIORS_JSON` | - | 도메인 prior 오버라이드(JSON 객체) |

정책 파일 예시:

- `infra/domain_policies.json`

## API 빠른 참조

`POST /v1/search`

- 입력: `query`, `mode`, `limit`, `page`, `categories`, `engines`, `language`, `time_range`, `safesearch`, `extract_top_n`, `max_extract_chars`
- 출력: `query`, `mode`, `limit`, `page`, `language`, `time_range`, `safesearch`, `results[]`, `cached`
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

- `query`, `mode`, `limit`, `page`, `categories`, `engines`, `language`, `time_range`, `safesearch`, `extract_top_n`, `max_extract_chars`

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
- `artifacts/search-compare`: 벤치마크 입력/결과/리포트
- `plan/PLAN_v2_search_quality_upgrade.md`: 품질 고도화 마일스톤 체크리스트
