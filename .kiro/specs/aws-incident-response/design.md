# AWS Incident Response - Design

## Architecture: Observe-Reason-Act-Verify-Audit Pipeline

```
[Observe]           [Reason]            [Act]               [Verify]            [Audit]
──────────────      ──────────────      ──────────────      ──────────────      ──────────────
알람/메트릭 수신     증상 분류           가역적 완화 실행     완화 효과 확인       타임라인 기록
로그 쿼리           원인 가설 수립       (LOW: 자동)         메트릭 정상화 확인   결정사항 추적
CloudTrail 조회     DKR 결정 트리 탐색   (MEDIUM: 제안+승인) 5분 안정성 윈도우    증거 보존
토폴로지 파악       근본 원인 진단       (HIGH: 명시적 승인) 부작용 감지          포스트모템 초안
최근 변경 확인      조치 계획 수립       롤백 명령 대기       자동 롤백 판단       후속 조치 생성
```

### 파이프라인 실행 원칙

1. **안정화 우선**: 완화(Act)가 진단(Reason)보다 먼저 — 가역적 조치는 원인 파악 없이도 즉시 실행
2. **증거 병행 수집**: 조치하면서 로그/메트릭 스냅샷 동시 확보
3. **진단은 안정화 후**: 완화 효과 확인 후 근본 원인 분석 심화
4. **Human-in-the-Loop**: AI가 80% 자율 조사 → 인간이 20% 판단/승인 (MEDIUM/HIGH 조치)

---

## DKR Schema v1

각 장애 시나리오는 Decision Knowledge Record(DKR)로 정규화된다.

```yaml
schema: decision-knowledge-record/v1

metadata:
  id: string                    # e.g. lambda-timeout
  name: string                  # 한국어 설명
  category: Compute|Database|Network|Deployment|Platform|Security
  service: string               # e.g. AWS Lambda
  severity: LOW|MEDIUM|HIGH|CRITICAL
  tags: []
  source_refs: []               # AWS 공식 문서 출처

triggers:
  alarm: string                 # CloudWatch Alarm 패턴
  metric_threshold:             # 임계값 기반 자동 감지
    metric: string
    threshold: number
    comparison: GreaterThan|LessThan
  log_pattern: string           # CW Logs Insights 감지 패턴
  event_bridge: string          # EventBridge 이벤트 패턴

symptoms:
  - signal: string              # 감지 신호 이름
    location: string            # 로그/메트릭 위치
    query: string               # CW Logs Insights 또는 CLI 쿼리
    interpretation: string      # 해석 가이드

diagnosis:
  decision_tree:
    - step: number
      question: string
      check:
        tool: cloudwatch_metrics|cloudwatch_logs|aws_cli
        command: string
      branches:
        - condition: string
          next_step: number|string   # number = 다음 단계, string = root_cause ID

root_causes:
  - code: string                # e.g. RC-001
    name: string
    probability: high|medium|low
    related_symptoms: []

remediation:
  actions:
    - id: string
      name: string
      approval_level: LOW|MEDIUM|HIGH
      aws_cli: string           # 실행 명령
      rollback_cli: string      # 롤백 명령
      risk: string
      estimated_effect: string
  cdk_construct: string         # CDK 기반 영구 수정 방법 (선택)
  ssm_automation: string        # SSM Automation Runbook (선택)

guardrails:
  pre_conditions:
    - check: string
      block_if_false: boolean
  post_conditions:
    - check: string
      auto_rollback: boolean

verification:
  checks:
    - metric: string
      expected: string
  stability_window: string      # e.g. "5m"
  success_criteria: string

escalation:
  auto_remediate: boolean
  approval_required: boolean
  timeout: string               # 승인 대기 제한 시간
  notify: []                    # 알림 대상
```

DKR 스키마 원본 및 Lambda 시나리오 정규화 예시:
`docs/research/05-decision-knowledge-base.md` 섹션 3-4

---

## Kiro Integration: Skill + Agent 2-Layer

```
┌─────────────────────────────────────────────────────────────────┐
│                        Kiro Agent Layer                          │
│  aws-incident-response agent (실행 계층)                         │
│                                                                  │
│  - MCP tool 호출 (AWS CLI, CloudWatch API)                       │
│  - autoApprove: describe_*, list_*, get_*, search_*              │
│  - manual approval: update_*, put_*, create_*                    │
│  - disabled: delete_*, terminate_*                               │
│  - 사용자와 Human-in-the-Loop 승인 인터페이스                     │
└──────────────────────┬──────────────────────────────────────────┘
                       │ 참조 (reads)
┌──────────────────────▼──────────────────────────────────────────┐
│                        Kiro Skill Layer                          │
│  aws-incident-response skill (지식 계층)                         │
│                                                                  │
│  SKILL.md             — 실행 원칙, 시나리오 레지스트리            │
│  scenarios/*.yaml           — 시나리오별 Decision Knowledge Records    │
│  references/          — guardrails.yaml, log-source-map.md      │
└─────────────────────────────────────────────────────────────────┘
```

### 핵심 설계 원칙

- **Skills = Knowledge**: SKILL.md와 DKR 파일은 "무엇을 어떻게 판단하는가"를 정의. 실행하지 않음.
- **Agents = Execution**: Agent가 Skill을 읽고 MCP 도구를 호출하여 실제 AWS API를 실행.
- **분리의 이유**: Skill은 재사용 가능하고 버전 관리되는 지식 베이스. Agent는 Skill을 조합하여 다양한 실행 컨텍스트(Kiro, Claude Code, CI/CD)에서 동작.

### 디렉토리 구조

```
.kiro/
  skills/aws-incident-response/
    SKILL.md                      # Kiro용 골든 소스 (agent가 읽는 버전)
    scenarios/
      lambda-timeout.yaml
      lambda-throttle.yaml
      ...
    references/
      guardrails.yaml             # 3-tier 승인 게이트
      log-source-map.md           # 서비스별 로그 조회 참조
  agents/
    aws-incident-response.json    # Agent 실행 설정
  specs/aws-incident-response/
    requirements.md
    design.md                     # (이 파일)
    tasks.md
```

### 승인 게이트 흐름

```
조치 제안
    │
    ├── LOW (describe/list/get/search)
    │       └── 자동 실행 → 결과 알림
    │
    ├── MEDIUM (update/put/create)
    │       └── 제안 표시 → 사용자 승인 → 실행 → post_action_checks
    │
    └── HIGH (롤백/트래픽 우회/IAM 비활성화/페일오버)
            └── 분석 결과 제시 → 명시적 승인 요구 → 실행 → 모니터링
```
