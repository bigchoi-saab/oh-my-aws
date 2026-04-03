# Phase 0 Validation Report

> Date: 2026-04-03
> Project: oh-my-aws
> Scope: Kiro CLI Platform Validation for AWS Incident Response Skill

---

## G0-1: Kiro SKILL.md YAML Frontmatter 스펙 확정

**Result: PASS**

### agentskills.io 공식 사양 필드 목록

| 필드 | 필수/선택 | 타입 | 제약 조건 | 설명 |
|------|-----------|------|-----------|------|
| `name` | **필수** | string | 최대 64자, 소문자·숫자·하이픈만, 폴더명과 일치 | 스킬 식별자 |
| `description` | **필수** | string | 최대 1024자, 비어있으면 안 됨 | 스킬 용도 + 활성화 조건 설명 |
| `license` | 선택 | string | - | 라이선스명 |
| `compatibility` | 선택 | string | 최대 500자 | 환경 요구사항 |
| `metadata` | 선택 | map(string→string) | 임의 키-값 | author, version 등 |
| `allowed-tools` | 선택 | string | 공백 구분 | 사전 승인 도구 (**실험적, 워크스페이스 스킬에서 버그 #6055**) |

### Kiro Skill 디렉토리 구조

```
.kiro/skills/{skill-name}/
├── SKILL.md          # 필수 (name 필드 = 폴더명)
├── scripts/          # 선택: 실행 가능한 스크립트
├── references/       # 선택: 상세 참조 문서
└── assets/           # 선택: 템플릿, 리소스
```

### 핵심 규칙
- 폴더명 = YAML frontmatter `name` 필드 (일치 필수)
- 본문 500줄 이하 권장, 상세 내용은 `references/`로 분리
- Progressive Disclosure: 시작 시 name+description만 로드 → 활성화 시 전체 로드
- 워크스페이스 스킬 > 글로벌 스킬 우선순위

### 출처
- https://kiro.dev/docs/skills/
- https://agentskills.io/specification
- https://github.com/kirodotdev/Kiro/issues/6055

---

## G0-2: Kiro MCP Transport 방식 확인

**Result: PASS**

### MCP 설정 파일 위치

| 레벨 | 경로 |
|------|------|
| 워크스페이스 | `.kiro/settings/mcp.json` |
| 글로벌 | `~/.kiro/settings/mcp.json` |

### 지원 Transport

| Transport | 설정 방식 | 비고 |
|-----------|-----------|------|
| **stdio** | `command` + `args` | 가장 안정적, 로컬 프로세스 |
| **HTTP/Streamable HTTP** | `url` | HTTPS (localhost는 HTTP OK) |
| SSE (deprecated) | `url` | Streamable HTTP로 대체됨 |

### MCP 서버 등록 필드 (stdio)

| 필드 | 필수 | 설명 |
|------|------|------|
| `command` | 필수 | 실행 명령어 (uvx, npx, python 등) |
| `args` | 필수 | 명령어 인수 배열 |
| `env` | 선택 | 환경 변수 (`${VAR}` 참조 가능) |
| `disabled` | 선택 | 비활성화 (기본 false) |
| `autoApprove` | 선택 | 자동 승인 도구 목록 |
| `disabledTools` | 선택 | 차단 도구 목록 |
| `timeout` | 선택 | 타임아웃 ms (기본 60000) |

### 핵심 아키텍처 발견: Skills vs Agents 2계층

**Kiro는 Skills와 Agents가 분리된 2계층 구조:**

1. **Skills** (`.kiro/skills/`): 지식/지시 (SKILL.md, 최소 frontmatter)
   - MCP 도구를 직접 참조하지 않음
   - `allowed-tools`는 실험적이고 현재 워크스페이스 스킬에서 미동작

2. **Agents** (`.kiro/agents/`): 실행 설정 (JSON)
   - MCP 서버 등록 및 도구 접근 제어
   - `tools`, `allowedTools` 필드로 도구 참조
   - `@서버이름/도구이름` 패턴으로 MCP 도구 참조
   - `skill://.kiro/skills/**/SKILL.md`로 Skills 참조

**→ 우리 프로젝트에 필요한 것: Skill (지식) + Agent (실행) 모두 구현**

### 기존 AWS 공식 MCP 서버

이미 사용 가능한 AWS MCP 서버:
- `awslabs.core-mcp-server` - AWS 핵심 API
- `awslabs.aws-documentation-mcp-server` - AWS 문서 검색
- `awslabs.cdk-mcp-server` - CDK 도구
- `awslabs.aws-serverless-mcp-server` - 서버리스 도구

### 출처
- https://kiro.dev/docs/cli/mcp/configuration/
- https://kiro.dev/docs/cli/custom-agents/configuration-reference/
- https://awslabs.github.io/mcp/

---

## G0-3: 승인 게이트 UX 가능 여부

**Result: PARTIAL FAIL → 대안 확보**

### 발견
- Kiro MCP 설정에 `autoApprove` 필드가 존재하여, 도구별 자동 승인/수동 승인 분리 가능
- `disabledTools`로 위험 도구 차단 가능
- 그러나 MCP 도구 자체가 "승인 필요" 응답을 반환하여 인터랙티브 프롬프트를 트리거하는 명시적 메커니즘은 확인 안 됨

### 대안
1. **autoApprove 기반 분리**: LOW risk 도구 → `autoApprove`에 등록, MEDIUM/HIGH risk 도구 → 미등록 (Kiro 기본 승인 흐름 사용)
2. **disabledTools 기반 차단**: CRITICAL 도구를 차단하고, Agent prompt에서 "이 도구를 사용하려면 사용자에게 먼저 확인하라"고 지시
3. **dry_run + execute 분리**: 조회 도구(observe_*)는 autoApprove, 실행 도구(act_*)는 수동 승인

→ **autoApprove/disabledTools 2단 분리 + Agent prompt 지시로 3단계 승인 게이트 구현**

---

## G0-4: 샌드박스 AWS 계정/리전 확보

**Result: PARTIAL FAIL → 대안 확보**

### 현황
- 실제 AWS 계정 접근은 사용자 환경에 의존 (현재 세션에서 확인 불가)
- AWS CLI 설정 여부는 런타임에 확인 필요

### 대안
- Phase 1 E2E 검증을 **dry-run 모드**로 수행: DKR의 CLI 명령어 생성까지 검증, 실제 실행은 사용자 환경에서
- DKR YAML의 구조/내용 검증은 정적으로 수행 가능
- MCP 서버 개발 시 boto3 mock/LocalStack으로 테스트

---

## G0-5: 피벗 기준 정의

**Result: PASS**

### 피벗 매트릭스 최종 판정

| Gate | 결과 | 판정 | 대응 |
|------|------|------|------|
| G0-1 (Skill 스펙) | PASS | Kiro Skill 구현 가능 | agentskills.io 사양 확정 |
| G0-2 (MCP transport) | PASS | MCP 서버 구현 가능 | stdio transport, Python+FastMCP |
| G0-3 (승인 게이트) | PARTIAL FAIL | autoApprove 기반 대안 | 3단 분리 전략 |
| G0-4 (AWS 계정) | PARTIAL FAIL | dry-run 모드 대안 | 정적 검증 + dry-run |
| G0-5 (피벗 기준) | PASS | 문서화 완료 | 이 문서 |

### Phase 1 진입 판정: **GO**

- FULL FAIL 항목 없음
- 2개 PARTIAL FAIL 항목 모두 실행 가능한 대안 확보
- Claude Code Skill 피벗 불필요 (Kiro 플랫폼 충분히 검증됨)

### 아키텍처 수정 사항 (리서치 기반)

1. **Skill + Agent 2계층 필요**: 기존 계획은 Skill만 가정했으나, MCP 도구 접근은 Agent에서 제어. `.kiro/agents/aws-incident-responder.json` 추가 필요
2. **allowed-tools 미사용**: 워크스페이스 Skill에서 현재 미동작 (Bug #6055). 도구 접근 제어는 Agent JSON의 `tools`/`allowedTools` 필드로
3. **기존 AWS MCP 서버 활용 가능**: `awslabs.core-mcp-server`를 Phase 3 전에도 즉시 활용 가능
4. **MCP 서버 구현 언어**: Python (FastMCP, boto3 네이티브, AWS 공식 MCP 서버도 Python/uvx 기반)
