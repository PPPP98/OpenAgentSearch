# OpenAgentSearch Plan (v0)

## Goal
Build a fully open, self-hosted agentic web search service with:
- HTTP API: /v1/search, /v1/extract
- MCP tools: openagentsearch.search, openagentsearch.extract
- Strong caching + dedupe to reduce repeated fetch/extract costs
- Optional browser rendering for JS-heavy pages

## Non-goals (v0)
- Building a Google-scale index
- Defeating anti-bot/captcha systems
- Full agent browsing experience

## Verified Progress (2026-03-03)
- `uv run python -m unittest discover -s tests -v`: pass (`OK`, 9 run, 3 skipped)
- `OAS_RUN_DOCKER_TESTS=1 uv run python -m unittest tests.test_m1_stack_integration -v`: partial pass (2 passed, 1 failed)
- Latest failure to follow up: `test_api_health_endpoint` returned `http.client.RemoteDisconnected`
- Integration retest after fix: `OAS_RUN_DOCKER_TESTS=1 uv run python -m unittest tests.test_m1_stack_integration -v` passed (`OK`, 3 run)
- Added M2 core modules: schemas (`SearchRequest/SearchResult/ExtractRequest/ExtractResult`), `SearxngProvider`, URL normalizer + dedupe, and unit tests
- 2026-03-04: Implemented `/v1/extract` pipeline (SSRF validation, fetcher redirect validation, extraction + passage chunking + hash, Redis cache)
- 2026-03-04: `uv run python -m unittest discover -s tests -v` passed (`OK`, 20 run, 3 skipped)
- 2026-03-04: `OAS_RUN_DOCKER_TESTS=1 uv run python -m unittest tests.test_m1_stack_integration -v` passed (`OK`, 3 run)
- 2026-03-04: Implemented `/v1/search` with `mode=speed`, `mode=balanced`, and Redis-backed query cache
- 2026-03-04: `uv run python -m unittest discover -s tests -v` passed (`OK`, 23 run, 3 skipped)
- 2026-03-04: API routes include `/v1/search` and `/v1/extract`

## Branch Strategy (Solo OSS)

Default branch:
- Keep `master` as the stable branch (release-ready only)

Working branches:
- `feat/<scope>` for new features (example: `feat/m2-core-types`)
- `fix/<scope>` for bug fixes (example: `fix/api-health-check`)
- `chore/<scope>` for tooling/infra (example: `chore/uv-lock-refresh`)
- `docs/<scope>` for documentation-only changes

Daily flow:
1. Branch from latest `master`
2. Implement small, focused commits
3. Run local tests before merge (`uv run python -m unittest discover -s tests -v`)
4. Merge back to `master` with `--ff-only` or squash, then delete branch

Hotfix rule (solo exception):
- Direct commit to `master` is allowed only for urgent production break/fix
- After direct commit, create a short follow-up branch for cleanup/tests if needed

Remote repository settings (recommended):
- Protect `master` from force-push
- Require PR for merge when collaboration starts (can stay optional while solo)
- Use semantic commit prefixes: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`

## Milestones

### M1: Repo bootstrap + Docker stack
- [x] Monorepo structure: apps/api, apps/mcp, infra
- [x] docker-compose: searxng + redis + api (+ optional browser service)
- [x] SearXNG config enables JSON format
- [x] Migrate Python dependency management to `uv` (`pyproject.toml` + `uv.lock`)

Acceptance:
- [x] `docker compose up` brings all services healthy (verified by `test_default_services_become_healthy`)
- [x] API endpoint integration check is stable in Docker test (`test_api_health_endpoint`)

### M2: Core types + providers
- [x] Define SearchRequest/SearchResult/ExtractRequest/ExtractResult schemas
- [x] Implement SearxngProvider (GET /search?format=json)
- [x] Implement UrlNormalizer + basic dedupe

Acceptance:
- [x] Unit tests for URL canonicalization and dedupe

### M3: /v1/extract
- [x] SSRF protection (scheme allowlist, private IP block, redirect validation)
- [x] HttpFetcher + Extractor (trafilatura first, readability fallback)
- [x] Passage chunking + hash
- [x] Redis cache: url->extract

Acceptance:
- [x] Given a known URL shape (`https://example.com`), extraction service returns markdown + passages within limits (unit-tested with fake fetcher)
- [ ] Live external URL E2E validation without mocks (environment-dependent)

### M4: /v1/search
- [x] Call SearXNG -> results
- [x] mode=speed (SERP only)
- [x] mode=balanced (fetch+extract top N)
- [x] Query cache

Acceptance:
- [x] Same query twice hits query cache and avoids extra provider call (unit-tested)

### M5: MCP Server (thin wrapper)
- [ ] Expose tools: openagentsearch.search, openagentsearch.extract
- [ ] Minimal tool schemas to reduce token use
- [ ] Auth header support

Acceptance:
- [ ] MCP client can call tools and get correct JSON

### M6: Hardening
- [ ] Per-domain rate limiting
- [ ] Observability: logs + metrics (cache hit, fetch errors)
- [ ] Config file: domain policies (render mode, ttl, allowlist)

Acceptance:
- [ ] Load test with repeated queries shows stable latency and high cache hit
