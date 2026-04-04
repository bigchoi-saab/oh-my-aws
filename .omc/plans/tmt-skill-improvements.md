# TMT-Inspired Skill System Improvements

## Context

Three-Man-Team(TMT) GitHub skill 시스템 분석 결과, oh-my-aws 인시던트 대응 skill 시스템에 적용할 8개 개선점을 3개 우선순위 티어로 식별함. C1(YAML 핸드오프 유지)은 변경 불요로 제외, 나머지 7개 항목(A1-A3, B1-B3, C2)을 구현.

### Revision History

- **v1**: 초기 계획 생성
- **v2 (current)**: Architect + Critic 피드백 반영 (9개 항목). 주요 변경:
  - C1: B2 self-review를 execution.yaml 필드가 아닌 별도 `self-review.yaml` 아티팩트로 변경
  - C2: 라우터를 순차 로드 목록에서 **phase-gated dispatch table**로 재설계
  - M1: 실행 순서를 4-Phase로 재구성 (A1/A2/C2 병렬 충돌 해소)
  - M2: A1에 'Section N' 참조 → 파일 경로 참조 교체 AC 추가
  - M3: checkpoint.yaml에 error/rollback/escalation 상태 + error_context 필드 추가
  - M4: CDK Engineer에도 CDK-specific self-review 추가
  - m1: Phase 4 통합 검증 절차 구체화
  - m2: B1 페르소나 섹션 25줄 상한 AC 추가
  - m3: Reporter에 known-gaps.yaml 경로 전달 규칙 추가

### RALPLAN-DR Summary

**Principles:**
1. **Router Minimalism**: 오케스트레이터 파일은 라우팅과 위임만 담당, 지식은 참조 파일로 분리
2. **Token Discipline**: Agent context window를 보호하기 위한 구조적 토큰 절약 규칙. 라우터는 phase-gated dispatch로 필요한 참조만 로드 지시.
3. **Agent Autonomy with Accountability**: 풍부한 페르소나 + self-review로 agent 품질 자율 관리. Self-review는 인시던트 디렉토리 내 별도 아티팩트로 기록 (핸드오프 계약 오염 방지).
4. **Session Resilience**: 세션 중단 시 최소 비용으로 복구 가능한 checkpoint 메커니즘. 에러/롤백/에스컬레이션 상태 포함.
5. **Scope Containment**: 범위 밖 요청은 기록만 하고 현재 작업에 집중

**Decision Drivers (Top 3):**
1. **토큰 효율성**: team-leader 399줄을 매번 전체 로드하면 agent 생성 시 context 낭비 심각. Phase-gated dispatch로 현재 phase 참조만 로드.
2. **운영 안정성**: 인시던트 대응 중 세션 중단 시 처음부터 재시작하는 것은 MTTR 증가. 에러/롤백 중 세션 중단도 올바르게 재개해야 함.
3. **Agent 품질**: 역할 라벨만으로는 agent가 경계 케이스에서 일관된 판단을 내리기 어려움

**Viable Options:**

| | Option A: Incremental Refactor | Option B: Full Restructure |
|---|---|---|
| **접근** | team-leader를 분할하되 기존 파일 구조 최대 보존, 점진적 개선 | 전체 skill 디렉토리 재설계, TMT 구조 완전 복제 |
| **Pros** | 기존 동작 보장, 낮은 리스크, 변경 최소화 | TMT 패턴 100% 적용, 구조적 완성도 높음 |
| **Cons** | 일부 TMT 패턴 적용 불가 (예: file-based handoff는 이미 YAML로 더 나은 구현) | 변경 규모 대, 기존 참조 경로 전부 업데이트 필요, 테스트 부담 |
| **리스크** | LOW | HIGH |

**선택: Option A (Incremental Refactor)**
- 이유: 기존 YAML 핸드오프가 TMT의 Markdown 핸드오프보다 운영 데이터에 적합. 구조만 분리하면 TMT의 핵심 이점(router minimalism, token discipline, persona depth)을 모두 얻을 수 있음.

---

## Work Objectives

team-leader SKILL.md를 ~60줄 phase-gated 라우터로 축소하고, 세션 체크포인트(에러 상태 포함)/토큰 규율/풍부한 페르소나/self-review(Executor+CDK Engineer)/foreground 규칙/scope lock을 추가하여 TMT 수준의 skill 품질을 달성한다.

## Guardrails

### Must Have
- `/aws-incident` 진입점 동작 불변 (SKILL.md 경로, 실행 흐름 동일)
- `handoff-schemas.yaml` 계약 100% 보존 (스키마 필드 변경 없음)
- 모든 기존 agent 정의 파일 경로 유지 (`.claude/agents/aws-*.md`)
- 한국어 운영 콘텐츠 유지
- self-review 결과는 인시던트 디렉토리 내 별도 아티팩트(`self-review.yaml`)로 기록. execution.yaml 필드에 추가하지 않음.

### Must NOT Have
- 새로운 skill 진입점 추가 (기존 `/aws-incident`만 유지)
- handoff-schemas.yaml 스키마 필드 변경
- agent 정의 파일 경로 변경
- aws-incident-response 도메인 지식 구조 변경
- execution.yaml에 self-review 관련 필드 추가 (핸드오프 계약은 순수 inter-agent 계약 유지)

---

## Task Flow

```
Phase 1:
  A1 (team-leader 분할 + phase-gated router 생성)

Phase 2 (Phase 1 완료 후, 모두 병렬):
  A2 (session checkpoint)
  B1 (agent 페르소나 강화)
  B2 (self-review: Executor + CDK Engineer)
  C2 (scope lock + router에 참조 추가)

Phase 3 (Phase 1 완료 후, Phase 2와 병렬 가능):
  A3 (토큰 규율 삽입 — 분할된 참조 파일 수정)
  B3 (foreground 규칙 삽입 — 분할된 라우터/참조 수정)

Phase 4:
  통합 검증 (전체 파이프라인 경로 확인)
```

**의존 관계:**
- Phase 1 (A1)이 라우터 skeleton을 생성해야 Phase 2의 A2/C2가 라우터에 참조를 추가 가능
- Phase 1 (A1)이 참조 파일을 분할해야 Phase 3의 A3/B3가 분할된 파일을 수정 가능
- Phase 2의 B1/B2는 agent 파일만 수정하므로 A1과 무관하게 진행 가능하나, Phase 구분 명확성을 위해 Phase 2에 배치
- Phase 4는 모든 task 완료 후 진행

**A1 단독 Phase 1 사유 (M1 반영):** A1, A2, C2 모두 라우터 SKILL.md를 수정함. A1이 라우터를 처음부터 재작성하므로, A2/C2가 동시에 수정하면 merge conflict 발생. A1이 skeleton을 만든 후 A2/C2가 append 방식으로 추가.

---

## Detailed TODOs

### Task 1: A1 — team-leader SKILL.md 분할 (399 → ~60줄 phase-gated 라우터 + 참조 파일)

**목표:** team-leader SKILL.md를 TMT 스타일 ~60줄 phase-gated 라우터로 축소. 지식을 참조 파일로 분리. 분할된 파일 내 모든 내부 참조를 파일 경로 참조로 교체.

**파일 변경:**

| 작업 | 파일 | 내용 |
|------|------|------|
| **축소** | `.claude/skills/aws-team-leader/SKILL.md` | 60줄 이하 phase-gated 라우터로 재작성 |
| **신규** | `.claude/skills/aws-team-leader/references/triage-protocol.md` | 현재 Section 2 + Section 3 이동. ~40줄 |
| **신규** | `.claude/skills/aws-team-leader/references/agent-creation-protocol.md` | 현재 Section 4 이동. ~70줄 |
| **신규** | `.claude/skills/aws-team-leader/references/execution-flow.md` | 현재 Section 5 이동. ~55줄 |
| **신규** | `.claude/skills/aws-team-leader/references/approval-gate.md` | 현재 Section 6 이동. ~45줄 |
| **신규** | `.claude/skills/aws-team-leader/references/cdk-protocol.md` | 현재 Section 7 이동. ~65줄 |
| **신규** | `.claude/skills/aws-team-leader/references/error-handling.md` | 현재 Section 8 이동. ~30줄 |
| **신규** | `.claude/skills/aws-team-leader/references/final-report-template.md` | 현재 Section 9 이동. ~25줄 |
| **유지** | `.claude/skills/aws-team-leader/references/handoff-schemas.yaml` | 변경 없음 |

**라우터 SKILL.md 구조 — Phase-Gated Dispatch (C2 반영, 목표 ~60줄):**
```
---
frontmatter (기존 유지)
---

# AWS Operations Team Leader

## 역할
[5줄: 핵심 정의]

## 핵심 원칙
[4줄: 직접실행금지, 완화우선, 증거기반, 한번에하나]

## 보유 자원
[기존 테이블 유지 — 이미 간결]

## Phase-Gated Dispatch

현재 phase에 해당하는 참조만 로드하라. 다른 참조는 읽지 않는다.

| 현재 Phase | 로드할 참조 |
|-----------|------------|
| triage | references/triage-protocol.md |
| observe, diagnose | references/agent-creation-protocol.md |
| approve | references/approval-gate.md |
| execute, verify | references/execution-flow.md |
| report | references/final-report-template.md |
| cdk-* | references/cdk-protocol.md |
| error | references/error-handling.md (실패 시에만) |

**항상 로드:** references/session-checkpoint.md (재개 판단용)
```

**핵심 설계 결정:** 라우터는 phase-gated dispatch table로 "현재 phase에 필요한 참조 하나만" 로드 지시. 기존 순차 목록("순서대로 로드하여") 대비 LLM이 불필요한 참조를 eager-load하는 문제 해소 → 토큰 절약 실효성 확보.

**내부 참조 교체 (M2 반영):**

분할 후 참조 파일 내 "Section N" 참조를 파일 경로 참조로 교체해야 할 5개 위치:

| 원본 위치 (현 SKILL.md) | 원본 참조 | 교체 후 |
|---|---|---|
| execution-flow.md (L182) | "Section 6의 승인 게이트 프로토콜" | `references/approval-gate.md` |
| execution-flow.md (L204) | "Section 8 에러 핸들링" | `references/error-handling.md` |
| execution-flow.md (L219) | "Section 7 CDK 연계 프로토콜" | `references/cdk-protocol.md` |
| execution-flow.md (L220) | "Section 9 최종 보고" | `references/final-report-template.md` |
| error-handling.md (L358) | "Section 6 기준" | `references/approval-gate.md` |

**Acceptance Criteria:**
- [ ] team-leader SKILL.md가 60줄 이하
- [ ] SKILL.md가 phase-gated dispatch table을 포함 (순차 목록 아님)
- [ ] "현재 phase에 해당하는 참조만 로드하라. 다른 참조는 읽지 않는다." 명시
- [ ] 7개 참조 파일이 `references/` 디렉토리에 생성됨
- [ ] 기존 SKILL.md의 모든 내용이 참조 파일에 빠짐없이 이동됨 (diff 검증)
- [ ] **분할된 참조 파일 내 모든 'Section N' 참조가 파일 경로 참조로 교체됨** (5개 위치)
- [ ] `aws-incident/SKILL.md`에서 team-leader 참조 경로 변경 불필요 확인
- [ ] handoff-schemas.yaml 경로/내용 변경 없음

**Effort:** L (Large) — 가장 큰 구조 변경

---

### Task 2: A2 — SESSION-CHECKPOINT 메커니즘 추가

**목표:** 인시던트 대응 중 세션 중단 시 마지막 완료 단계부터 재개할 수 있는 체크포인트. 에러/롤백/에스컬레이션 상태 포함.

**파일 변경:**

| 작업 | 파일 | 내용 |
|------|------|------|
| **신규** | `.claude/skills/aws-team-leader/references/session-checkpoint.md` | 체크포인트 프로토콜 정의 |
| **수정** | `.claude/skills/aws-team-leader/SKILL.md` (라우터) | dispatch table 하단에 "항상 로드" 참조로 포함 (A1이 skeleton에 이미 배치) |

**session-checkpoint.md 내용:**

```markdown
# Session Checkpoint Protocol

## 체크포인트 파일
인시던트 디렉토리에 `checkpoint.yaml`을 유지한다.

## 스키마
incident_id: string
scenario_id: string
current_phase: enum [triage, observe, diagnose, approve, execute, verify, report, cdk-analyze, cdk-engineer, cdk-deploy, cdk-report, error, rollback, escalation, complete]
completed_artifacts:
  - filename: string
    timestamp: string
last_user_decision: string  # 마지막 승인/거부 내용
next_action: string          # 다음에 해야 할 일 (사람이 읽을 수 있는 설명)
resumed_count: integer       # 세션 재개 횟수
error_context:               # 에러/롤백 시 상세 컨텍스트 (해당 시에만)
  error_type: enum [agent_failure, verify_failure, unknown_scenario]
  failed_action: string
  rollback_in_progress: boolean
  retry_count: integer

## 기록 규칙
- 각 phase 완료 시 checkpoint.yaml 업데이트
- 사용자 승인/거부 결정도 기록
- agent 산출물 파일명 + timestamp 기록
- error/rollback/escalation phase 진입 시 error_context 필드 기록
- rollback_in_progress: true인 상태에서 세션 중단 시, 재개 후 롤백 계속 진행

## 재개 규칙
- 인시던트 디렉토리에 checkpoint.yaml이 존재하면 재개 모드
- checkpoint.current_phase 확인 → 해당 단계부터 실행
- current_phase가 error/rollback/escalation이면 error_context를 확인하여 적절한 복구 수행
- rollback_in_progress가 true이면 롤백을 계속 진행 (중복 실행 방지)
- completed_artifacts에 나열된 파일 존재 여부 검증
- 누락된 산출물이 있으면 해당 단계 재실행
```

**handoff-schemas.yaml 변경:** 없음. checkpoint.yaml은 팀장 내부 상태이므로 agent 간 핸드오프 계약에 포함하지 않음.

**Acceptance Criteria:**
- [ ] `session-checkpoint.md` 파일 생성됨
- [ ] checkpoint.yaml current_phase enum에 `error`, `rollback`, `escalation` 포함
- [ ] `error_context` 필드 정의됨 (error_type, failed_action, rollback_in_progress, retry_count)
- [ ] 롤백 중 세션 중단 시 재개 규칙 명시 (rollback_in_progress 처리)
- [ ] 라우터 SKILL.md에 체크포인트 참조 포함 ("항상 로드"로 표기)
- [ ] 기존 파이프라인 흐름과 호환 (체크포인트 없으면 기존 동작)

**Effort:** M (Medium)

---

### Task 3: A3 — 토큰 규율 5 규칙 삽입

**목표:** TMT의 토큰 절약 규칙을 skill 파일에 구조적으로 내장.

**파일 변경:**

| 작업 | 파일 | 내용 |
|------|------|------|
| **수정** | `.claude/skills/aws-team-leader/SKILL.md` (라우터) | 핵심 원칙에 토큰 규율 추가 |
| **수정** | `.claude/skills/aws-team-leader/references/agent-creation-protocol.md` | Agent 프롬프트 템플릿에 토큰 규율 포함 |

**5가지 토큰 규율 규칙:**
```
1. Phase-gated 참조 로드: dispatch table에 명시된 현재 phase 참조만 읽는다 (다른 참조 금지)
2. Agent 프롬프트 최소화: agent에게 전달하는 context는 해당 작업에 필요한 최소 정보만
3. 산출물 요약 우선: 긴 YAML을 전체 읽지 말고 필요한 필드만 추출
4. 에러 출력 잘라내기: AWS CLI 에러 출력은 처음 20줄만 기록
5. 반복 프롬프트 금지: 이전 대화에서 이미 전달한 정보를 다시 전달하지 않는다
```

**삽입 위치:**
- 라우터 SKILL.md의 `## 핵심 원칙` 섹션에 "토큰 규율" 항목 추가
- agent-creation-protocol.md의 Agent 프롬프트 템플릿 하단에 "## 토큰 규율" 섹션 추가

**의존:** Task 1 (A1) 완료 후 진행

**Acceptance Criteria:**
- [ ] 5개 규칙이 라우터 핵심 원칙에 명시됨
- [ ] 규칙 1이 phase-gated dispatch를 명시적으로 참조
- [ ] Agent 프롬프트 템플릿에 토큰 규율 섹션 포함
- [ ] 규칙이 기존 동작을 제한하지 않음 (가이드라인 수준)

**Effort:** S (Small)

---

### Task 4: B1 — Agent 페르소나 강화 (Backstory + Values)

**목표:** 5개 기존 agent 정의 파일에 TMT 스타일의 풍부한 페르소나(배경 + 가치관 + 판단 원칙)를 추가. 각 페르소나 섹션은 25줄 이하.

**파일 변경:**

| 작업 | 파일 | 추가 내용 |
|------|------|-----------|
| **수정** | `.claude/agents/aws-diagnostician.md` | 페르소나 섹션 추가 |
| **수정** | `.claude/agents/aws-executor.md` | 페르소나 섹션 추가 |
| **수정** | `.claude/agents/aws-reporter.md` | 페르소나 섹션 추가 |
| **수정** | `.claude/agents/aws-cdk-analyzer.md` | 페르소나 섹션 추가 |
| **수정** | `.claude/agents/aws-cdk-engineer.md` | 페르소나 섹션 추가 |

**각 agent에 추가할 페르소나 섹션 구조:**
```markdown
## 페르소나

### 배경
[이 agent가 모방하는 인간 전문가의 경력/전문성 서술]

### 핵심 가치
- [가치 1]: [설명]
- [가치 2]: [설명]
- [가치 3]: [설명]

### 판단 원칙 (우선순위 순)
1. [최우선 원칙]
2. [차선 원칙]
3. [기본 원칙]

### 경계 케이스 행동
- [상황 1] → [행동]
- [상황 2] → [행동]
```

**Agent별 페르소나 요약:**

| Agent | 배경 모델 | 핵심 가치 | 판단 원칙 우선순위 |
|-------|-----------|-----------|-------------------|
| Diagnostician | 10년차 SRE, 관측 수집 전문가 | 증거 순수성, 체계적 의심, 시간 압박 인식 | 증거보존 > 체계적탐색 > 속도 |
| Executor | 변경관리 전문가, 최소개입 철학 | 가역성 집착, 한 번에 하나, 검증 강박 | 안전성 > 최소변경 > 효과 |
| Reporter | 인시던트 스크라이브, 포스트모템 전문가 | 사실만 기록, 타임라인 정확성, 후속조치 실용성 | 정확성 > 완전성 > 간결성 |
| CDK Analyzer | IaC 아키텍트, drift 탐정 | 코드-인프라 일치 집착, 영향 범위 정밀 추적 | 정확한분석 > 영향범위파악 > 실행가능성 |
| CDK Engineer | CDK 장인, 최소 diff 철학 | 변경 최소화, synth/diff 검증 강박, 스타일 일관성 | 최소변경 > 검증통과 > 코드품질 |

**Acceptance Criteria:**
- [ ] 5개 agent 파일 모두에 `## 페르소나` 섹션 추가됨
- [ ] 각 페르소나에 배경, 핵심 가치 3개, 판단 원칙 3개, 경계 케이스 2개 이상 포함
- [ ] **각 agent의 페르소나 섹션은 25줄을 초과하지 않는다** (m2 반영)
- [ ] 기존 역할/입력/실행순서/제약사항/산출물 섹션 변경 없음
- [ ] 한국어로 작성

**Effort:** M (Medium) — 5개 파일, 각각 독립 작업

---

### Task 5: B2 — Self-Review 단계 추가 (Executor + CDK Engineer)

**목표:** TMT의 "Builder answers 3 critical questions before review" 패턴을 Executor와 CDK Engineer 모두에 적용. Self-review 결과는 별도 `self-review.yaml` 아티팩트로 기록 (execution.yaml 오염 방지).

**파일 변경:**

| 작업 | 파일 | 내용 |
|------|------|------|
| **수정** | `.claude/agents/aws-executor.md` | Act와 Verify 사이에 Self-Review phase 삽입 |
| **수정** | `.claude/agents/aws-cdk-engineer.md` | CDK 코드 변경 후 Self-Review phase 삽입 |

**Executor Self-Review (Phase 1.5: Act → Self-Review → Verify):**

Executor가 Act 완료 후, Verify 시작 전에 다음 3개 질문에 자체 답변:

```markdown
### Phase 1.5: Self-Review (자체 검증)

Act 완료 후, Verify 시작 전에 다음 질문에 답한다. 모든 답이 "예"여야 Verify로 진행.

1. **의도한 조치만 실행했는가?**
   - 승인된 actions 목록과 실제 실행된 명령어 1:1 대조
   - 추가 실행된 명령어가 없는지 확인

2. **모든 조치에 롤백 경로가 확보되어 있는가?**
   - 각 action의 rollback_command가 현재 상태에서 실행 가능한지 확인
   - 롤백 순서 (역순)가 논리적으로 유효한지 확인

3. **예상치 못한 부작용이 관측되는가?**
   - execution 결과에서 warning/unexpected output 확인
   - 에러율이나 관련 메트릭의 급격한 변화 여부 확인

하나라도 "아니오"인 경우:
- 인시던트 디렉토리에 self-review.yaml 기록 (passed: false, failed_question, reason)
- 실패 사유를 팀장에게 보고
- Verify로 진행하지 않음

모든 답이 "예"인 경우:
- 인시던트 디렉토리에 self-review.yaml 기록 (passed: true)
- Verify로 진행
```

**CDK Engineer Self-Review (M4 반영):**

CDK 코드 변경 완료 후, 팀장 보고 전에 다음 3개 질문에 자체 답변:

```markdown
### CDK Self-Review (자체 검증)

CDK 코드 변경 완료 후, 팀장 보고 전에 다음 질문에 답한다.

1. **cdk synth가 성공했는가?**
   - synth 출력에 에러/경고 없음 확인

2. **diff가 예상 범위 내인가?**
   - cdk diff 결과가 의도한 리소스 변경만 포함하는지 확인
   - 예상 외 리소스 추가/삭제/변경이 없는지 확인

3. **다른 스택에 영향이 있는가?**
   - cross-stack reference 변경 여부 확인
   - 영향받는 스택이 있으면 범위와 영향을 명시

하나라도 "아니오"인 경우:
- 인시던트 디렉토리에 self-review.yaml 기록 (agent: cdk-engineer, passed: false, failed_question, reason)
- 실패 사유를 팀장에게 보고
- 배포 진행하지 않음
```

**self-review.yaml 스키마 (인시던트 디렉토리 내 intra-agent 아티팩트):**
```yaml
agent: string          # executor | cdk-engineer
timestamp: ISO8601
passed: boolean
questions:
  - question: string
    answer: boolean
    detail: string     # 실패 시 사유
```

**C1 반영 핵심:** self-review.yaml은 execution.yaml의 필드가 아닌, 인시던트 디렉토리 내 별도 파일이다. execution.yaml은 순수 inter-agent 핸드오프 계약으로 유지한다. self-review.yaml은 intra-agent 아티팩트로, 팀장이 참고용으로 읽을 수 있으나 핸드오프 계약의 일부가 아니다.

**Acceptance Criteria:**
- [ ] Executor agent 정의에 Phase 1.5: Self-Review 섹션이 Act와 Verify 사이에 삽입됨
- [ ] CDK Engineer agent 정의에 CDK Self-Review 섹션 삽입됨
- [ ] Executor 3개 질문 + CDK Engineer 3개 질문이 각각 정의됨
- [ ] 실패 시 `self-review.yaml`을 인시던트 디렉토리에 기록 (execution.yaml 필드 아님)
- [ ] self-review.yaml 스키마가 정의됨
- [ ] 기존 Act/Verify 로직 변경 없음
- [ ] handoff-schemas.yaml 변경 없음

**Effort:** M (Medium) — Executor + CDK Engineer 두 파일 수정

---

### Task 6: B3 — Foreground-Agent-Only 규칙 추가

**목표:** 승인 프롬프트가 필요한 agent는 반드시 foreground에서 실행하도록 규칙 명시.

**파일 변경:**

| 작업 | 파일 | 내용 |
|------|------|------|
| **수정** | `.claude/skills/aws-team-leader/SKILL.md` (라우터) | 핵심 원칙에 foreground 규칙 추가 |
| **수정** | `.claude/skills/aws-team-leader/references/agent-creation-protocol.md` | Agent 생성 시 foreground 규칙 명시 |

**규칙 내용:**
```markdown
## Foreground Agent 규칙

모든 Agent는 foreground에서 생성한다 (Agent tool 기본 동작).

**이유:** 인시던트 대응 중 agent가 사용자 승인을 요청해야 하는 상황이 빈번하다.
Background agent는 사용자 프롬프트를 받을 수 없으므로, 승인 게이트가 작동하지 않는다.

**예외 없음:** Diagnostician (관측 전용)이라도 guardrails pre_conditions 검증에서
사용자 확인이 필요할 수 있으므로, 모든 agent는 foreground로 실행한다.
```

**의존:** Task 1 (A1) 완료 후 분할된 파일에 삽입

**Acceptance Criteria:**
- [ ] 라우터 핵심 원칙에 foreground 규칙 명시
- [ ] agent-creation-protocol.md에 foreground 실행 지시 포함
- [ ] 예외 없이 모든 agent에 적용됨을 명시

**Effort:** S (Small)

---

### Task 7: C2 — Scope Lock 메커니즘 (Known Gaps 추적)

**목표:** 인시던트 대응 중 범위 밖 요청/발견사항을 Known Gaps로 기록하고 scope creep을 방지. Reporter에 known-gaps.yaml 경로 전달.

**파일 변경:**

| 작업 | 파일 | 내용 |
|------|------|------|
| **신규** | `.claude/skills/aws-team-leader/references/scope-lock.md` | Scope lock 프로토콜 정의 |
| **수정** | `.claude/skills/aws-team-leader/SKILL.md` (라우터) | dispatch table의 report phase에 scope-lock.md 공동 로드 추가 |
| **수정** | `.claude/skills/aws-team-leader/references/agent-creation-protocol.md` | Reporter 생성 시 known-gaps.yaml 경로 전달 규칙 추가 |

**scope-lock.md 내용:**
```markdown
# Scope Lock Protocol

## 원칙
인시던트 대응 중에는 현재 시나리오의 완화/검증/보고에만 집중한다.
범위 밖 발견사항은 기록만 하고 현재 파이프라인을 중단하지 않는다.

## Known Gaps 파일
인시던트 디렉토리에 `known-gaps.yaml`을 유지한다.

## Known Gaps 스키마
gaps:
  - id: string (gap-001, gap-002, ...)
    discovered_at: ISO8601
    discovered_by: string (agent명)
    phase: string (어떤 phase에서 발견)
    category: enum [other-incident, improvement, security, monitoring, architecture]
    description: string
    priority: enum [urgent, normal, low]
    related_resource: string (선택)

## 기록 규칙
- 현재 시나리오와 직접 관련 없는 문제를 발견하면 known-gaps.yaml에 추가
- 기록 후 즉시 현재 작업으로 복귀
- 사용자에게 "범위 밖 문제를 발견했으나 known-gaps에 기록했습니다" 알림

## 예시 상황
- Lambda throttle 대응 중 RDS slow query 발견 → known-gaps에 기록
- 인시던트 조사 중 IAM 과잉 권한 발견 → known-gaps에 기록
- CloudTrail에서 비인가 변경 발견 → urgent로 기록 + 사용자에게 즉시 알림

## 최종 보고에 포함
audit-report.yaml의 follow_ups에 known-gaps 항목을 포함한다.
```

**Reporter에 known-gaps.yaml 전달 (m3 반영):**

agent-creation-protocol.md에 다음 규칙 추가:
```
Reporter 생성 시, 인시던트 디렉토리에 known-gaps.yaml이 존재하면 해당 파일 경로를 Reporter에게 추가로 전달한다. Reporter는 known-gaps 내용을 최종 보고의 follow_ups 섹션에 포함한다.
```
이것은 team-leader의 agent 생성 행동 변경이며, Reporter agent 정의 파일 자체는 변경하지 않는다.

**Acceptance Criteria:**
- [ ] `scope-lock.md` 파일 생성됨
- [ ] known-gaps.yaml 스키마 정의됨
- [ ] 라우터 dispatch table에 scope-lock 로드 조건 포함
- [ ] urgent gap 발견 시 즉시 알림 규칙 포함
- [ ] 최종 보고에 known-gaps 포함 지시 포함
- [ ] agent-creation-protocol.md에 Reporter 생성 시 known-gaps.yaml 경로 전달 규칙 추가됨

**Effort:** S (Small)

---

## Phase 4: Integration Verification (m1 반영)

Phase 1-3의 모든 task 완료 후 다음 항목을 검증한다:

**검증 절차:**

1. **Router phase-gate dispatch 동작 검증:**
   - 각 phase 값에 대해 dispatch table이 정확한 참조 파일을 지시하는지 확인
   - "다른 참조는 읽지 않는다" 지시가 명확한지 확인
   - session-checkpoint.md가 "항상 로드"로 올바르게 표기되었는지 확인

2. **Checkpoint 생성 및 전환 검증:**
   - checkpoint.yaml의 current_phase enum이 dispatch table의 모든 phase를 커버하는지 확인
   - error, rollback, escalation phase가 enum에 포함되어 있는지 확인
   - error_context 필드가 정의되어 있는지 확인

3. **Scope-lock 기록 검증:**
   - scope-lock.md가 dispatch table에서 접근 가능한지 확인
   - known-gaps.yaml 스키마가 정의되어 있는지 확인
   - Reporter 생성 시 known-gaps.yaml 전달 규칙이 agent-creation-protocol.md에 있는지 확인

4. **Self-review 발동 검증:**
   - Executor의 self-review가 Act와 Verify 사이에 위치하는지 확인
   - CDK Engineer의 self-review가 코드 변경 후 보고 전에 위치하는지 확인
   - self-review.yaml이 execution.yaml과 별도 파일임이 명시되어 있는지 확인
   - handoff-schemas.yaml에 self-review 관련 필드가 추가되지 않았는지 확인

5. **Cross-reference 무결성:**
   - 분할된 참조 파일 내 "Section N" 참조가 남아있지 않은지 전체 검색
   - 모든 파일 경로 참조가 실제 존재하는 파일을 가리키는지 확인

---

## Success Criteria

1. **team-leader SKILL.md 60줄 이하** — 현재 399줄에서 85% 감소, phase-gated dispatch table 포함
2. **7개 참조 파일 생성** — triage, agent-creation, execution-flow, approval-gate, cdk-protocol, error-handling, final-report-template
3. **2개 프로토콜 파일 생성** — session-checkpoint.md (에러 상태 포함), scope-lock.md
4. **5개 agent 파일에 페르소나 추가** — 각각 배경/가치/원칙/경계케이스 포함, 25줄 이하
5. **Executor + CDK Engineer에 Self-Review phase 삽입** — 각각 3개 질문, self-review.yaml 아티팩트로 기록
6. **토큰 규율 5 규칙** — 라우터 + agent-creation-protocol에 삽입, phase-gated dispatch 참조
7. **Foreground 규칙** — 라우터 + agent-creation-protocol에 삽입
8. **`/aws-incident` 진입점 동작 불변** — aws-incident/SKILL.md 변경 불필요
9. **handoff-schemas.yaml 무변경** — self-review 포함 어떤 필드도 추가되지 않음
10. **Phase 4 통합 검증 통과** — 5개 검증 항목 모두 Pass

## Execution Order (4-Phase, M1 반영)

```
Phase 1 (단독):
  - Task 1 (A1): team-leader 분할 + phase-gated router [L]
    → 라우터 skeleton 생성, 7개 참조 파일 분할, Section N 참조 교체

Phase 2 (Phase 1 완료 후, 병렬):
  - Task 2 (A2): session checkpoint              [M]  — 라우터에 "항상 로드" 참조 추가
  - Task 4 (B1): agent 페르소나                    [M]  — agent 파일만 수정
  - Task 5 (B2): self-review (Executor+CDK Eng)   [M]  — agent 파일만 수정
  - Task 7 (C2): scope lock                        [S]  — 라우터 dispatch table에 참조 추가 + agent-creation-protocol 수정

Phase 3 (Phase 1 완료 후, Phase 2와 병렬 가능):
  - Task 3 (A3): 토큰 규율 삽입                    [S]  — 분할된 참조 파일 수정
  - Task 6 (B3): foreground 규칙 삽입              [S]  — 분할된 라우터/참조 수정

Phase 4 (전체 완료 후):
  - 통합 검증: 5개 검증 항목 수행
```

**Phase 2 병렬 안전성:** A2/C2는 라우터의 서로 다른 위치에 append (A2: "항상 로드" 행, C2: dispatch table 행). B1/B2는 라우터를 수정하지 않음 (agent 파일만). 따라서 merge conflict 없음.

## ADR (Architecture Decision Record)

**Decision:** team-leader SKILL.md를 ~60줄 phase-gated dispatch 라우터 + 7개 참조 파일로 분할하고, TMT의 5가지 개선 패턴(토큰 규율, 세션 체크포인트, 풍부한 페르소나, self-review, scope lock)을 적용한다. Self-review 결과는 핸드오프 계약 외부의 별도 아티팩트로 기록한다.

**Drivers:**
1. 토큰 효율성 (399줄 전체 로드 → phase-gated dispatch로 현재 phase 참조만 선택적 로드)
2. 세션 복원력 (인시던트 중 세션 중단 대비, 에러/롤백 중 중단 포함)
3. Agent 판단 품질 (역할 라벨 → 풍부한 페르소나 + self-review, Executor와 CDK Engineer 모두 적용)

**Alternatives Considered:**
- **Full Restructure:** 전체 skill 디렉토리 재설계. TMT 구조 100% 복제. 기각 사유: 변경 규모 과대, 기존 YAML 핸드오프가 이미 TMT보다 우수.
- **No Change (status quo):** 기각 사유: 399줄 모놀리식 파일은 토큰 낭비 + 유지보수 어려움.
- **Sequential list router (v1 design):** "순서대로 로드하여" 방식. 기각 사유: LLM이 모든 참조를 eager-load하여 토큰 절약 효과 없음. Phase-gated dispatch table로 대체.
- **Self-review in execution.yaml (v1 design):** execution.yaml에 self_review_failed 필드 추가. 기각 사유: handoff-schemas.yaml 계약 오염. 별도 self-review.yaml 아티팩트로 대체.

**Why Chosen:** Incremental Refactor with phase-gated dispatch는 기존 동작을 보장하면서 TMT의 핵심 이점을 모두 획득. YAML 핸드오프는 이미 TMT의 Markdown 핸드오프보다 우수하므로 유지. Phase-gated dispatch로 토큰 절약 실효성 확보. Self-review를 별도 아티팩트로 분리하여 핸드오프 계약의 순수성 유지.

**Consequences:**
- (+) 토큰 사용량 ~40% 감소 (phase-gated dispatch로 현재 phase 참조만 로드)
- (+) 세션 중단 시 마지막 phase부터 재개 가능 (에러/롤백 상태 포함)
- (+) Agent 판단 일관성 향상 (풍부한 페르소나 + self-review, CDK Engineer 포함)
- (+) 핸드오프 계약(execution.yaml) 순수성 유지 (self-review는 별도 아티팩트)
- (-) 참조 파일 수 증가 (관리 포인트 9개 → 16개)
- (-) 참조 간 내용 중복 가능성 (정기적 정합성 확인 필요)

**Follow-ups:**
- 실제 인시던트 대응 시 토큰 사용량 측정 (before/after 비교, phase-gated dispatch 효과 검증)
- session-checkpoint 재개 시나리오 테스트 (특히 error/rollback 중 재개)
- agent 페르소나가 실제 판단 품질에 미치는 영향 관찰
- known-gaps 데이터가 충분히 쌓이면 자동 인시던트 생성 검토
- CDK Engineer self-review 질문의 적정성 검증 (실제 CDK 작업 사례 기반)

---

## Feedback Incorporation Tracker (v2)

| ID | Type | Summary | How Addressed |
|---|---|---|---|
| C1 | CRITICAL | B2 self-review가 execution.yaml 필드 오염 | B2에서 self-review.yaml 별도 아티팩트로 변경. Guardrails에 execution.yaml 필드 추가 금지 명시. |
| C2 | CRITICAL | 라우터 순차 로드가 eager-load 유발 | A1 라우터를 phase-gated dispatch table로 재설계. "현재 phase에 해당하는 참조만 로드하라" 명시. |
| M1 | MAJOR | A1/A2/C2 병렬 시 merge conflict | 실행 순서를 4-Phase로 재구성. A1 단독 Phase 1 → A2/C2는 Phase 2에서 append. |
| M2 | MAJOR | Section N 참조 깨짐 | A1 AC에 "모든 Section N 참조가 파일 경로 참조로 교체됨" 추가. 5개 위치 명시. |
| M3 | MAJOR | checkpoint에 error 상태 누락 | A2 checkpoint.yaml enum에 error/rollback/escalation 추가. error_context 필드 추가. |
| M4 | MAJOR | CDK Engineer self-review 부재 | B2에 CDK Engineer self-review 3개 질문 추가 (cdk synth, diff 범위, 타 스택 영향). |
| m1 | MINOR | Phase 4 검증 절차 미정의 | Phase 4 통합 검증 섹션 신설. 5개 구체 검증 항목 정의. |
| m2 | MINOR | 페르소나 섹션 길이 무제한 | B1 AC에 "각 agent의 페르소나 섹션은 25줄을 초과하지 않는다" 추가. |
| m3 | MINOR | Reporter에 known-gaps 전달 누락 | C2에 agent-creation-protocol.md 수정 추가. Reporter 생성 시 known-gaps.yaml 경로 전달 규칙. |
