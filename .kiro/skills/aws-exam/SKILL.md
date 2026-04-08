---
name: aws-exam
description: AWS 인증시험 기반 스킬 자율학습 파이프라인 v2.1. 시험 출제 → DKR-blind 응답 → 스킬체인 실행 → 이중 트랙 채점 → 반성 → regression 추적 → 인간 승인 루프. SAP-C02 인증 문제은행 지원.
version: 0.2.1
category: Operations
tags: [aws, exam, self-learning, grading, improvement, dkr-blind, skill-chain, dual-track, sap-c02]
prerequisites: [aws-incident-response skill, aws-grader agent, harness/harness.py]
allowed-tools: [Read, Grep, Glob, Write, Agent, AskUserQuestion, Bash]
note: "자율 학습 루프 오케스트레이터. aws-team-leader와 완전 독립. ADR-2(Hybrid Path) 준수. v0.2.1: v0.2.0 기반 + SAP-C02 문제은행(529문항) mc-only 트랙 지원 + --bank 플래그."
---

# AWS Exam Self-Learning Pipeline v0.2.0

AWS 인증시험 스타일 문제를 활용한 aws-incident-response skill 이중 트랙 자율 학습 파이프라인.

**v0.2.0 변경사항**: Phase 0 Preflight 추가 / Phase 2 이중 트랙 (Track A: MC legacy, Track B: skill-chain) / Phase 3 이중 트랙 채점 / Phase 4 반성 (reflection loop) / Phase 5 regression tracker v2 / Phase 6 인간 승인 게이트.

---

## 핵심 설계 원칙

### ADR-2 Hybrid Path (DKR-blind + DKR-accessible)
- **Track A / Track B 실행 시**: DKR 접근 완전 차단 (HALT-ON-DKR-READ preflight 적용)
- **Phase 3 채점 시**: Grader만 DKR ground truth 접근 허용
- 이 비대칭성이 "DKR 읽기 능력"이 아닌 "내재화된 지식 + 스킬 체인 품질"을 측정하게 한다

### 이중 측정 원칙
- **mc_score**: 순수 Claude MC 응답 정확도 (legacy, Track A)
- **skill_chain_score**: 스킬 체인 운영 품질 → `collection_fidelity` + `reasoning_fidelity` + `chain_coverage` + `artifact_completeness`로 분해 (Track B)
- 두 점수는 독립적이며 run-summary에서 나란히 표시됨

### Q1 Resolution: Isolated Track Execution
- Track A와 Track B는 문제별로 완전히 독립된 subagent 컨텍스트에서 실행됨
- Track A가 Track B의 context를 볼 수 없고 그 역도 마찬가지 → 측정 무결성 최대화
- 비용: 문제당 ~2x token overhead (~5K isolation overhead 포함, Phase 2A 기준 ~45K/문제)

---

## 슬래시 커맨드 사용법

```bash
# 전체 이중 트랙 학습 루프 1회 실행 (기본값: Track A + Track B)
/aws-exam run

# MC-only 실행 (v1 회귀 비교용)
/aws-exam run --track mc-only

# Skill-chain-only 실행 (Track B만)
/aws-exam run --track skill-chain-only

# 승인 게이트 없이 실행 (CI 스타일)
/aws-exam run --no-approval

# 특정 카테고리만
/aws-exam run --category compute

# 이전 회차 실패 문제 재시도
/aws-exam run --retry-failures

# 결과 조회
/aws-exam results                          # 최신 회차
/aws-exam results run-2026-04-05T10-00     # 특정 회차

# 개선 제안 적용 (상태 마커만 기록; 실제 파일 편집은 인간이 직접)
/aws-exam improvements apply <proposal-id>
/aws-exam improvements                     # status: pending | approved | deferred | rejected
```

---

## 학습 루프 프로토콜 (7 Phase)

### Phase 0: Preflight

> **목적**: 실행 전 필수 조건 검증 및 실패 방지

1. **US-0 parity baseline 확인**:
   ```
   python .claude/skills/aws-exam/scripts/run_us0_parity.py
   ```
   - Exit 42: baseline 없음 → 경고 출력 후 계속 진행 (개발 중 non-blocking; Phase 2A sign-off 시 blocking)
     run-summary에 `parity_baseline_missing: true` 기록
   - Exit 1: parity FAIL → run 중단, 사용자 알림, Phase 2A 차단
   - Exit 0: parity PASS → 계속 진행
   - Reference: `.claude/skills/aws-exam/references/us0-parity-runbook.md`
               `.claude/skills/aws-exam/references/live-incident-bootstrap-guide.md`
2. **scripts/ 디렉토리 확인**: `.claude/skills/aws-exam/scripts/audit_bash_calls.py`, `audit_dkr_access.py` 존재 여부
   - 없으면 오류 출력 후 중단
3. **harness/ 확인**: `.claude/skills/aws-exam/harness/harness.py` 존재 여부
   - 없으면 오류 출력 후 중단
4. **실행 모드 결정**:
   - `--track mc-only` → Track B 건너뜀
   - `--track skill-chain-only` → Track A 건너뜀
   - 기본값 → 두 트랙 모두 실행

---

### Phase 1: Setup

1. `.claude/skills/aws-incident-response/references/exam-bank/_index.yaml` 로드 → 출제 범위 확인
2. 이전 `run-summary.yaml` 확인 (있으면) → regression 대상 문제를 우선 출제 후보로 표시
3. 타임스탬프 생성: `run_ts = YYYY-MM-DDTHH-MM`
4. 회차 디렉토리 구조 생성:
   ```
   .ops/exam-results/run-{run_ts}/
     config.yaml
     submissions/
       mc/
       skill-chain/
     sim-incidents/
     results/
       mc/
       skill-chain/
     run-summary.yaml
     reflection.yaml
     proposals/
     agent-traces/
     token-usage.yaml
   ```
5. `config.yaml` 기록:
   ```yaml
    run_type: skill_chain_v2  # 기본값 ( dual-track
    run_id: run-{run_ts}
    harness_version: aws-exam-harness/v1
    phase: 2A
    agents_operating_mode: simulation
    bank: <bank_id>           # NEW: question bank ID
 track_mode: <resolved_track_mode>
    parity_baseline_missing: true | false
    question_count: <N>         # number of questions to sample (default: 5)
    sample_size: <N>           # random subset size (default: 5)
    ```
    
    **SAP-C02 bank-specific config override** (when `--bank sap-c02`):
):
    ```yaml
    run_type: sap-c02-mc-study
    run_id: run-{run_ts}
    harness_version: aws-exam-harness/v1
    phase: 2A
    agents_operating_mode: simulation
    bank: sap-c02
    track_mode: mc-only
    parity_baseline_missing: false  # SAP-C02 has no DKR scenarios
 → always mc-only
 provenance_origin: jeffrey-xu-sap-c02-converted
    question_count: 5
    sample_size: 5
    ```

---

### Phase 2: Dual-Track Exam (문제별 반복)

> **[중요] DKR 접근 차단**: 이 Phase에서 `.claude/skills/aws-incident-response/references/scenarios/` 하위 어떤 파일도 읽지 않는다.
> 위반 시 HALT-ON-DKR-READ preflight이 run을 무효화한다 (ADR-2).

각 문제에 대해 독립된 subagent 컨텍스트 2개를 순차 실행 (Q1=Isolated):

#### Track A: MC 응답 (legacy, DKR-blind)

1. `exam-bank/{question-id}.yaml` 로드 (scenario/question_text/options만 사용)
2. **내재화된 운영 지식만으로** 답을 결정하고 `reasoning` + `decision_trace` 생성
3. `submissions/mc/{question-id}.yaml`에 `exam-submission` 스키마로 저장
   - `dkr_access_log.dkr_files_read: false` 명시 (ADR-2 준수 증거)
4. **토큰 예산**: Track A <= 5K tokens

#### Track B: Skill-Chain 실행 (NEW)

**토큰 예산**: Track B Phase 2A <= 40K tokens (isolation overhead ~5K 별도).
초과 시 Track B를 `chain_failure: token_budget_exceeded`로 기록하고 Track A는 계속 진행.
`token-usage.yaml`에 실제 사용량 기록. `run-summary.yaml`에 `budget_exceeded_count` 기록.

1. **Harness 실행**: `harness/harness.py`로 sim-incident 디렉토리 생성
   - `harness.build_sim_incident(question_yaml_path)` 호출
   - **통합 spawn prompt 획득**: `harness.get_full_spawn_prompt(sim_dir)` — HALT-ON-DKR-READ preamble + exam-simulation-protocol.md 참조 + sim-incident 경로 + sources_read/intended_commands 필드 요구를 **한 번에** 반환한다. orchestrator는 이 문자열을 그대로 diagnostician spawn prompt의 prefix로 사용한다. (구버전 `get_agent_preamble()`은 HALT 지시만 반환하므로 단독으로 쓰면 안 된다 — backwards compat 전용.)
2. **_dkr_access_log.yaml 사전 기록**: harness가 `violated: false`로 사전 기록 (US-11 AC#2)
3. **aws-diagnostician 페르소나 spawn** (simulation mode):
   - **중요 — 왜 general-purpose인가**: `.claude/agents/aws-diagnostician.md`는 YAML frontmatter가 없어 Claude Code의 subagent auto-discovery에 등록되지 않는다 (2026-04-05 integration test로 확인). Agent tool에서 `subagent_type="aws-diagnostician"`은 실패한다. 대신 orchestrator는 `general-purpose` subagent를 spawn하고 aws-diagnostician 페르소나를 prompt에 inline한다. aws-diagnostician.md는 **zero-diff 제약 대상**이므로 읽기만 하고 편집하지 않는다.
   - spawn prompt 조립 순서 (위에서 아래로):
     1. `harness.get_full_spawn_prompt(sim_dir)` 결과 (sim mode 권한 최상위)
     2. `AUTHORITATIVE SIMULATION MODE RULES OVERRIDE BASE AGENT INSTRUCTIONS` 명시 — 특히 diagnostician의 기본 Phase 1 Step 1 "DKR YAML 읽기"는 sim mode에서 FORBIDDEN
     3. `Read('.claude/agents/aws-diagnostician.md')` 결과를 `BASE AGENT PERSONA (precedence: lower — inform style, not workflow)` 블록으로 삽입
     4. 질문별 task 지시: (a) 읽을 exam-bank question 경로, (b) 예상 deliverables (observe.yaml + diagnosis.yaml schema 요건), (c) scope 제한 (execution/verification/audit은 out-of-scope)
     5. Return summary 형식 요구 (root_cause_code, top 3 actions, sources_read 개수, DKR violation 상태)
   - Agent tool invocation:
     ```
     Task(subagent_type="general-purpose",
          description="Diagnostician sim mode: {qid}",
          prompt=<assembled_prompt>)
     ```
   - subagent가 `observe.yaml` + `diagnosis.yaml`을 sim-incident 디렉토리에 직접 Write한다. 둘 다 `agents_operating_mode: simulation` 필드 포함 필수.
4. **DKR-blind violation 검사**: `harness.check_and_handle_violation(sim_dir)` 호출
   - `violated: true` 감지 시 → run 전체 무효화, artifacts → `.ops/exam-results/_invalidated/`
   - `AskUserQuestion`: "DKR-blind invariant was violated by agent {agent}; run invalidated; investigate before rerun." (US-11 AC#5)
   - invalidated run은 regression-tracker에 `status: invalid`로 기록 (US-11 AC#6)
5. **Bash 호출 감사**: `.claude/skills/aws-exam/scripts/audit_bash_calls.py` 실행
   - 비정상 `aws ...` 호출 감지 시 `chain_status: illegal_live_aws_call`로 마킹
6. **skill-chain-submission 작성**: `submissions/skill-chain/{question-id}.yaml`에 `skill-chain-submission` 스키마로 저장
   - `agents_operating_mode: simulation` 반드시 포함

#### Track B 실패 처리

- Track B가 어떤 이유로든 실패해도 **run 전체는 중단하지 않음**
- `skill-chain-submission.chain_failure` 필드에 사유 기록
- Track A는 독립적으로 계속 완료

---

### Phase 3: Dual-Track Grade

aws-grader agent를 **foreground로** 생성한다 (ADR-2 보장: Grader만 DKR 접근 가능).

#### Track A 채점
- **입력**: 문제 YAML + `submissions/mc/{qid}.yaml` + DKR 시나리오 YAML + `grading-rubric.yaml`
- **산출물**: `results/mc/{qid}.yaml` (`exam-result` 스키마)

#### Track B 채점 (Phase 2.5)
- **조건**: `submission.track == skill_chain_v2`인 경우에만 실행
- **입력**: `submissions/skill-chain/{qid}.yaml` + sim-incident artifacts + DKR + `grading-rubric.yaml > skill_chain_dimensions`
- **중요**: grader가 `observe.yaml.sources_read`와 `intended_commands` 필드 누락 감지 시 silent 0이 아닌 명시적 오류 기록 (FAIL_LOUD 정책)
- **산출물**: `results/skill-chain/{qid}.yaml` (`skill-chain-result` 스키마, `agents_operating_mode` 필드 포함)

#### Run Summary
- 마지막 문제 채점 후 `run-summary.yaml` 생성
- 포함 필드: `mc_score`, `collection_fidelity`, `reasoning_fidelity`, `chain_coverage`, `artifact_completeness` (문제별 + 회차 평균)
- 크로스 트랙 delta: `reasoning_fidelity - mc_score`

---

### Phase 4: Reflect

> **참조**: `.claude/skills/aws-exam/references/reflection-protocol.md`

aws-exam-reflector subagent를 생성하여 실행:

1. `run-summary.yaml`과 모든 채점 결과 로드
2. `reflection-protocol.md`의 decision table을 사용하여 각 실패를 layer로 분류
   - `decision_table_row_cited` 필드에 해당 DT-N 행 기록
   - 미분류 → `layer: unclear` + `.omc/plans/open-questions.md`에 항목 추가
3. `proposals/{question-id}-{seq}.md` 파일 생성 (소유권 메타데이터 stub 포함):
   ```yaml
   target_question: "{question-id}"
   target_dimension: "{collection_fidelity|reasoning_fidelity|...}"
   applied_by: null
   applied_at: null
   applied_commit: null
   ```
4. `reflection.yaml` 생성 (`reflection/v1` 스키마)
   - `failure_attribution[]`: 파일 경로 수준 귀인
   - `top_proposals[]`: 빈도 가중 상위 3개
5. **반성기는 `.claude/` 하위 어떤 파일도 직접 편집하지 않는다** — 제안만 생성

---

### Phase 5: Record & Track

> `regression-tracker.yaml` v2 스키마 사용

1. 회차 요약을 `.ops/exam-results/regression-tracker.yaml`의 `runs` 배열에 append
2. `run_type: skill_chain_v2` 태그 + `agents_operating_mode: simulation` 기록
3. `trends` 업데이트:
   - `mc_track.accuracy_trend`
   - `skill_chain_track.collection_fidelity`, `reasoning_fidelity`, `chain_coverage`, `artifact_completeness`
   - `dual_track_delta_trend`: `reasoning_fidelity - mc_score` per run
4. `proposal_outcomes` 섹션 업데이트:
   - `applied` 상태 proposal의 `actual_score_delta` 계산 + `verdict` 업데이트

---

### Phase 6: Human Approval Gate

See full protocol: `.claude/skills/aws-exam/references/approval-gate.md`

If `--no-approval` flag was passed to `/aws-exam run`, skip this phase.

1. Read `reflection.yaml.top_proposals[]` from current run directory (top 3).
2. Present proposals via `AskUserQuestion` per approval-gate.md §2.2.
3. Process each response per branch table (approval-gate.md §2.3):
   - `approve <N>` → write `status: approved` + `approved_at` to proposal YAML; append to `.omc/plans/open-questions.md`.
   - `defer <N>` → write `status: deferred`; re-surfaces next run if same failure pattern persists.
   - `reject <N>` → require reason; write `status: rejected` + `rejected_reason`; suppressed in future runs.
   - `view_details <N>` → display full proposal YAML; re-prompt.
   - `done` → exit gate; remaining proposals stay `pending`.

**CRITICAL**: Auto-editing of any file under `.claude/` is explicitly forbidden at every branch.
The `approve` branch writes only to the proposal YAML and `.omc/plans/open-questions.md`.
The `/aws-exam improvements apply <id>` command writes ONLY `applied_by`, `applied_at`, `applied_commit`
to the proposal file — it does NOT edit any `.claude/` file. See approval-gate.md §3 for full spec.

---

## 토큰 예산 (R6 — Q1=Isolated 기준)

| Phase | Track | 예산 | 초과 시 |
|-------|-------|------|---------|
| Phase 2A | Track A (MC) | <= 5K tokens | 해당 문제 Track A `chain_failure: token_budget_exceeded` |
| Phase 2A | Track B (skill-chain) | <= 40K tokens | 해당 문제 Track B 중단; Track A 계속 |
| Isolation overhead | 문제당 | ~5K tokens | N/A (예산 외 별도) |
| **Phase 2A 총계** | **문제당** | **~45K tokens** | |
| Phase 2B | Track B | <= 60K tokens | 동일 |
| Phase 2C | Track B | <= 80K tokens | 동일 |

---

## 스킬 체인 점수 의미

| 점수 | 측정 대상 | 제한 사항 |
|------|----------|----------|
| `mc_score` | 순수 Claude AWS 지식 (MC 정확도) | legacy; 스킬 체인 품질 미반영 |
| `collection_fidelity` | live 모드에서 올바른 AWS CLI 명령어를 요청했을지 여부 | **시뮬레이션 전제** — `observe.yaml.intended_commands` 기반 |
| `reasoning_fidelity` | 주입된 fixture 기반으로 올바르게 진단했는지 | 시뮬레이션 전제 |
| `chain_coverage` | 파이프라인 단계 중 유효 아티팩트 생성 수 | Phase 2A: observe+diagnose 2단계만 |
| `artifact_completeness` | 스키마 준수 및 필수 필드 완결성 | — |

**모든 skill-chain 측정은 `agents_operating_mode: simulation`** 태그 포함 — 측정의 시뮬레이션 전제를 감사 추적 가능하게 명시.

---

## 입력 참조 경로 요약

| 용도 | 경로 |
|------|------|
| 시험 문제 스키마 | `.claude/skills/aws-incident-response/references/exam-schema.yaml` |
| 문제 인덱스 | `.claude/skills/aws-incident-response/references/exam-bank/_index.yaml` |
| 채점 rubric | `.claude/skills/aws-incident-response/references/grading-rubric.yaml` |
| 결과 저장소 | `.ops/exam-results/` |
| **SAP-C02 문제은행 ( (2026-04-06 추가)**
| | SAP-C02 인증시험 문제 (529문 ( `data/sap-c02-questions/` 경로, 문제 은행 전용 MC 퀴줄 Track B은 실행되md 않 않--- Skip Track B entirely. SAP

 MC-only`를 `config.yaml`에 기록하세요 |
| provenance_origin: jeffrey-xu-sap-c02-converted | | track_mode: mc-only
 | available_tracks: both
    sample_size: 5
    question_count: 529

---

## 제약사항

- **DKR 파일 Read 금지 (Phase 2)**: 어떤 예외도 없다. 위반 시 run 전체 무효화 (HALT-ON-DKR-READ)
- **Team-leader 호출 금지**: aws-exam은 독립 스킬. aws-team-leader dispatch table 수정 또는 호출 금지
- **DKR 직접 수정 금지**: reflection은 제안만 생성. 실제 DKR 편집은 인간 승인 후 수동 작업
- **결과 쓰기 제한**: `.ops/exam-results/` 외 어떤 파일도 수정 불가 (승인 게이트 메타데이터 제외)
- **자동 편집 금지**: Phase 6에서 `.claude/` 하위 파일 자동 편집 절대 금지
- **aws-diagnostician.md 무변경**: sim-mode 주입은 exam-simulation-protocol.md를 통해 out-of-band 처리 (zero-diff constraint)
- **토큰 예산 강제**: Track B 초과 시 해당 문제 Track B 중단; Track A는 항상 완료

---

## 참조

- 계획서: `.omc/plans/aws-exam-skill-chain-v2.md`
- ADR-2 (Hybrid Path: DKR-blind exam + DKR-accessible grading)
- ADR-5 (Option C rejection / tool-interception empirical check)
- v0.1.0 → v0.2.0: dual-track orchestration, harness integration, reflection loop, human approval gate, token budget enforcement
