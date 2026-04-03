# AWS 운영 Decision Knowledge Base 설계

> 조사일: 2026-04-03
> 목적: AWS 공식 문서 기반 Decision Knowledge Base 스키마 설계 및 첫 번째 운영 시나리오(Lambda 타임아웃/쓰로틀링) 정규화
> 배경: AWS 자격증 시험 문제 대신 공식 문서에서 "문제 상황 → 진단 → 조치 → 검증" 구조의 운영 지식을 추출하여 AI Agent가 활용 가능한 Knowledge Base 구축

---

## 1. 배경 및 동기

### 1.1 자격증 문제 접근의 한계

초기 아이디어는 AWS Associate/Professional 시험 문제를 AI Agent의 지식 베이스로 활용하는 것이었다.
시험문제는 "문제 상황 → 최적 해결책(best practice)" 쌍으로 구성되어 있어, agent의 의사결정 라우팅에 유용해 보였다.

하지만 3가지 치명적 한계가 확인되었다:

| 한계 | 설명 |
|------|------|
| **저작권/NDA** | AWS 자격증 문제는 Amazon의 독점 자산. 수집·변환하여 상업적 도구에 탑재하면 법적 리스크 |
| **구현 깊이 부족** | 시험문제는 "무엇을 해야 하는가"만 묻고, "어떻게 구현하는가"는 다루지 않음. Agent는 API 호출, 메트릭 쿼리, CDK construct까지 필요 |
| **단일 선택지 한계** | A/B/C/D 선택이 아닌 복합 조치가 실제 장애 대응에 필요 |

### 1.2 대안: 공식 무료 자료에서 동일 구조 추출

시험문제가 주려던 **문제 상황 → best practice 매핑**을 합법적이고 더 깊은 구현 수준에서 제공하는 AWS 공식 소스:

| 소스 | 제공하는 것 | oh-my-aws 활용점 |
|------|------------|-----------------|
| **AWS Well-Architected Framework** (Serverless Lens) | 질문-답변 쌍, 구체적 best practice | `Reason` 단계 의사결정 트리 |
| **AWS Prescriptive Guidance** | 서비스별 패턴, anti-pattern, 아키텍처 결정 트리 | `Reason` → `Act` 라우팅 |
| **AWS Troubleshooting Guides** | 문제 증상 → 원인 → 해결 단계별 절차 | `Observe` → `Reason` 매핑 |
| **AWS re:Post Knowledge Center** | AWS 검증 답변이 있는 실제 Q&A | 장애 대응 시나리오 라이브러리 |
| **AWS Operational Readiness Reviews** | 운영 체크리스트와 검증 항목 | `Verify` 단계 가드레일 |
| **AWS Incident Response Playbooks** | 단계별 대응 절차 | Runbook 레지스트리 원본 |
| **AWS Systems Manager Automation Runbooks** | 실행 가능한 진단/복구 자동화 스크립트 | `Act` 단계 실행 템플릿 |

### 1.3 접근 방식

각 소스에서 **"시나리오 → 판단 → 조치 → 검증"** 구조로 정규화하여, oh-my-aws의 `Observe → Reason → Act → Verify → Audit` 파이프라인에 직접 매핑한다.

```
[공식 문서 원본]                    [정규화된 Decision Knowledge]
                                    ┌─ scenario_id
AWS Well-Architected 질문    ──▶   ├─ symptoms[]
                                    ├─ diagnosis_steps[]
AWS Troubleshooting Guide    ──▶   ├─ root_causes[]
                                    ├─ remediation_actions[]
AWS Prescriptive Guidance    ──▶   ├─ guardrails[]
                                    ├─ verification_checks[]
AWS re:Post Knowledge Center ──▶   ├─ escalation_criteria
                                    └─ source_refs[]
```

---

## 2. 첫 번째 운영 시나리오: Lambda 타임아웃 / 쓰로틀링

### 2.1 시나리오 선정 이유

1. oh-my-aws README에 명시된 MVP 대상 시나리오 중 하나
2. 발생 빈도가 높고(배포 후 장애, 트래픽 증가 시 빈발) 자동화 효용이 큼
3. AWS 공식 문서에서 가장 풍부한 트러블슈팅 지식이 제공되는 영역
4. 진단 → 조치 → 검증의 전체 파이프라인이 명확히 정의 가능

### 2.2 증상 패턴 (Symptom Patterns)

#### 타임아웃 증상

| 증상 | 감지 방법 | CloudWatch 지표/로그 |
|------|----------|---------------------|
| `Task timed out after X seconds` | CloudWatch Logs Insights 쿼리 | `@message like "Task timed out"` |
| `Status: timeout` Init/Invoke 단계 | CloudWatch Logs | `@message like "Status: timeout"` |
| Duration spike near configured timeout | CloudWatch Metrics | `Duration p95/p99/max` |
| 비동기 이벤트 처리 지연 | CloudWatch Metrics | `AsyncEventAge` 증가 |
| SQS/Stream 처리 지연 | CloudWatch Metrics | `IteratorAge` 증가, `ApproximateAgeOfOldestMessage` 증가 |

**감지 쿼리 (CloudWatch Logs Insights):**
```sql
fields @timestamp, @requestId, @message, @logStream
| filter @message like "Status: timeout"
| sort @timestamp desc
| limit 100
```

#### 쓰로틀링 증상

| 증상 | 감지 방법 | CloudWatch 지표/로그 |
|------|----------|---------------------|
| `TooManyRequestsException` | Lambda 로그, API 응답 | HTTP 429 응답 코드 |
| `Rate exceeded` | CloudWatch Logs | `@message like "Rate exceeded"` |
| `Throttles > 0` | CloudWatch Metrics | Lambda `Throttles` 메트릭 |
| `ConcurrentExecutions` near limit | CloudWatch Metrics | 계정/함수 한계 근접 |
| Burst stair-step pattern | CloudWatch Metrics | 초기 버스트 1000 → 분당 500 증가 패턴 |

### 2.3 진단 결정 트리 (Diagnosis Decision Tree)

```
[감지: Lambda 타임아웃/쓰로틀링 의심]
         │
         ▼
    ┌────────────────────────────────┐
    │ Step 1: 증상 분류              │
    │ - Logs에 "timed out"? → TIMEOUT │
    │ - Throttles > 0?     → THROTTLE │
    │ - 둘 다?              → COMPOUND │
    └────────────┬───────────────────┘
                 │
         ┌───────┼───────┐
         ▼               ▼
   [TIMEOUT]        [THROTTLE]
         │               │
         ▼               ▼
  ┌──────────────┐  ┌──────────────────────────┐
  │Step 2: 원인   │  │Step 2: 동시성 수준 확인    │
  │범위 좁히기    │  │                            │
  ├──────────────┤  ├──────────────────────────┤
  │- Duration    │  │ aws lambda                │
  │  p95/p99?    │  │   get-account-settings    │
  │- 메모리/CPU  │  │                            │
  │  사용률?     │  │ ConcurrentExecutions vs    │
  │- 다운스트림  │  │   Account Quota?           │
  │  지연?       │  │                            │
  │- VPC 경로?   │  │ Reserved Concurrency       │
  │- SDK 타임아웃│  │   설정 여부?                │
  │  정렬?       │  │                            │
  └──────┬───────┘  └──────────┬─────────────────┘
         │                     │
         ▼                     ▼
  ┌──────────────┐  ┌──────────────────────────┐
  │Step 3: 근본  │  │Step 3: 근본 원인 분류      │
  │원인 분류      │  │                            │
  ├──────────────┤  ├──────────────────────────┤
  │A. 설정 부족   │  │X. Account-level 한계       │
  │  (timeout,   │  │Y. Function-level 한계      │
  │   memory)    │  │   (Reserved Concurrency)   │
  │B. 다운스트림  │  │Z. Event Source 제한        │
  │  병목        │  │   (SQS batch/concurrency)  │
  │C. 코드 비효율│  │W. Burst rate 한계          │
  │D. VPC/네트워크│  │   (1000/10s/function)     │
  │E. 콜드 스타트│  └────────────────────────────┘
  └──────────────┘
```

### 2.4 근본 원인 카테고리 (Root Cause Categories)

#### 타임아웃 근본 원인

| 원인 코드 | 원인 | 진단 API/메트릭 | 판단 기준 |
|----------|------|----------------|----------|
| `TIMEOUT-CFG` | 타임아웃 설정이 실제 p95/p99에 너무 근접 | `GetFunctionConfiguration` → `Timeout` vs `Duration p95` | p95가 timeout의 80% 이상 |
| `TIMEOUT-MEM` | 메모리/CPU 부족으로 실행 지연 | `Duration` vs `MemorySize`, CPU 바운드 워크로드 | 메모리 증설 시 Duration 선형 감소 |
| `TIMEOUT-DEP` | 다운스트림 종속성 지연 (S3/API/DB) | X-Ray Traces, 하위 서비스 메트릭 | Trace에서 하위 호출이 Duration 대부분 |
| `TIMEOUT-VPC` | VPC 라우팅/NAT/DNS/SG 문제 | VPC Flow Logs, NAT Gateway 메트릭 | VPC 내 함수만 타임아웃 발생 |
| `TIMEOUT-SDK` | SDK 타임아웃과 Lambda 타임아웃 불일치 | SDK 설정 확인, 로그 분석 | connection/socket timeout > lambda timeout |
| `TIMEOUT-COLD` | 콜드 스타트로 인한 Init 시간 과다 | CloudWatch `Init Duration` 메트릭 | Init Duration이 실행 시간의 50% 이상 |

#### 쓰로틀링 근본 원인

| 원인 코드 | 원인 | 진단 API/메트릭 | 판단 기준 |
|----------|------|----------------|----------|
| `THROTTLE-ACCT` | 계정 레벨 동시성 한계 도달 | `GetAccountSettings` → `ConcurrentExecutions` vs `AccountQuota` | `ConcurrentExecutions` ≈ `AccountQuota` |
| `THROTTLE-RESV` | 함수 Reserved Concurrency 한계 | `GetFunctionConcurrency` → `ReservedConcurrentExecutions` | 해당 함수만 `Throttles > 0` |
| `THROTTLE-BURST` | 버스트 스케일링 한계 (1000/10s) | CloudWatch `Invocations` 급증 패턴 | 짧은 시간에 급증 후 Throttles 발생 |
| `THROTTLE-SRC` | SQS/DynamoDB Stream 이벤트 소스 병목 | `ListEventSourceMappings`, SQS 대기열 길이 | `ApproximateNumberOfMessagesVisible` 증가 |
| `THROTTLE-POISON` | 포이즌 필 메시지 재시도 폭주 | DLQ 메시지 수, `maxReceiveCount` | 동일 메시지의 반복 처리 실패 |

### 2.5 조치 액션 (Remediation Actions)

#### 타임아웃 조치

| 원인 코드 | 조치 | CLI/API | CDK Construct |
|----------|------|---------|---------------|
| `TIMEOUT-CFG` | 타임아웃 증설 | `aws lambda update-function-configuration --timeout 120` | `lambda.Function({ timeout: Duration.seconds(120) })` |
| `TIMEOUT-MEM` | 메모리 증설 (CPU도 비례 증가) | `aws lambda update-function-configuration --memory-size 1024` | `lambda.Function({ memorySize: 1024 })` |
| `TIMEOUT-DEP` | 다운스트림 타임아웃 정렬 + 재시도/서킷브레이커 | SDK 레벨 설정 변경 | 애플리케이션 코드 수정 |
| `TIMEOUT-VPC` | VPC 경로 수정 (NAT → VPC Endpoint 등) | VPC 라우트 테이블, SG 수정 | `ec2.InterfaceVpcEndpoint`, `ec2.GatewayVpcEndpoint` |
| `TIMEOUT-SDK` | SDK connection/socket timeout을 Lambda timeout 이하로 설정 | 환경변수 또는 코드 수정 | `environment: { AWS_NODEJS_CONNECTION_REUSE_ENABLED: '1' }` |
| `TIMEOUT-COLD` | Provisioned Concurrency 활성화 | `aws lambda put-provisioned-concurrency-config --provisioned-concurrent-executions 50` | `lambda.Alias({ provisionedConcurrentExecutions: 50 })` |
| `TIMEOUT-COLD` (Java) | SnapStart 활성화 | `aws lambda update-function-configuration --snap-start ApplyOn=PublishedVersions` | `lambda.Function({ snapStart: lambda.SnapStartConf.ON })` |

#### 쓰로틀링 조치

| 원인 코드 | 조치 | CLI/API | CDK Construct |
|----------|------|---------|---------------|
| `THROTTLE-ACCT` | 계정 동시성 한도 증가 요청 | AWS Support 케이스 (Service Quotas) | 해당 없음 (AWS 요청 필요) |
| `THROTTLE-RESV` | Reserved Concurrency 조정 | `aws lambda put-function-concurrency --reserved-concurrent-executions 100` | `lambda.Function({ reservedConcurrentExecutions: 100 })` |
| `THROTTLE-RESV` | Provisioned Concurrency 추가 | `aws lambda put-provisioned-concurrency-config --provisioned-concurrent-executions 50` | `lambda.Alias({ provisionedConcurrentExecutions: 50 })` |
| `THROTTLE-BURST` | SQS/DynamoDB Stream으로 이벤트 버퍼링 | 이벤트 소스 매핑 생성 | `SqsEventSource(queue, { batchSize: 10, maxBatchingWindow: Duration.seconds(5) })` |
| `THROTTLE-SRC` | SQS 이벤트 소스 최대 동시성 조정 | `aws lambda update-event-source-mapping --uuid <uuid> --scaling-config '{"MaximumConcurrency":5}'` | `SqsEventSource(queue, { maxConcurrency: 5 })` |
| `THROTTLE-SRC` | SQS Provisioned Poller 설정 | `aws lambda update-event-source-mapping --uuid <uuid> --provisioned-poller-config '{"MinimumPollers":5,"MaximumPollers":100}'` | 해당 없음 (CLI/SDK만) |
| `THROTTLE-POISON` | Partial Batch Response 활성화 | `aws lambda update-event-source-mapping --uuid <uuid> --function-response-types ReportBatchItemFailures` | `SqsEventSource(queue, { reportBatchItemFailures: true })` |
| `THROTTLE-POISON` | DLQ + Redrive 설정 | SQS DLQ 설정, `maxReceiveCount` 조정 | `sqs.Queue({ deadLetterQueue: { queue: dlq, maxReceiveCount: 5 } })` |

### 2.6 가드레일 (Guardrails)

조치 실행 전 반드시 확인해야 하는 안전 장치:

```yaml
guardrails:
  pre_action:
    - name: "타임아웃 증설 전 p95/p99 근거 확인"
      check: "Duration p95가 현재 timeout의 80% 이상인가?"
      block_if_false: true

    - name: "메모리 증설 전 실제 메모리 사용률 확인"
      check: "현재 MemorySize 대비 실제 사용량이 80% 이상인가?"
      block_if_false: true

    - name: "Provisioned Concurrency 비용 영향 계산"
      check: "월 예상 비용 증가액을 사용자에게 표시했는가?"
      block_if_false: true
      formula: "PC_count × memory_GB × $0.0000041667/GB-second × seconds_per_month"

    - name: "Reserved Concurrency 0 실수 방지"
      check: "reservedConcurrentExecutions가 0이 아닌가?"
      block_if_false: true

    - name: "계정 동시성 한계 확인"
      check: "aws lambda get-account-settings → ConcurrentExecutions 한계"
      block_if_false: false  # 경고만

    - name: "VPC 변경 시 영향 범위 확인"
      check: "해당 VPC를 사용하는 다른 리소스가 있는가?"
      block_if_false: false  # 경고만

  post_action:
    - name: "조치 후 5분간 메트릭 모니터링"
      check: "Throttles = 0, Duration p95 < timeout × 0.8"
      block_if_false: false  # 자동 롤백 고려

    - name: "비정상 징후 감지 시 자동 롤백"
      check: "Errors가 조치 전보다 증가했는가?"
      block_if_false: true
      action: "이전 설정으로 복원"
```

### 2.7 검증 체크리스트 (Verification Checks)

| 검증 항목 | 확인 방법 | 성공 기준 |
|----------|----------|----------|
| 타임아웃 해소 | CloudWatch Logs Insights 재쿼리 | `Status: timeout` 메시지 0건 (5분 윈도우) |
| Duration 여유 | CloudWatch Metrics `Duration p95` | p95 < timeout × 0.8 |
| 쓰로틀링 해소 | CloudWatch Metrics `Throttles` | `Throttles = 0` (지속적) |
| 동시성 여유 | CloudWatch Metrics `ConcurrentExecutions` | Account Quota의 70% 미만 |
| 비동기 이벤트 처리 | CloudWatch Metrics `AsyncEventAge` | 트렌드 감소 또는 안정 |
| SQS 처리 지연 | CloudWatch Metrics `ApproximateAgeOfOldestMessage` | 안정 또는 감소 |
| SQS 정상 처리 | CloudWatch Metrics `NumberOfMessagesDeleted` | 0이 아닌 지속적 값 |
| PC 효율 | CloudWatch Metrics `ProvisionedConcurrencySpilloverInvocations` | 0에 근접 |
| DLQ 정상 | CloudWatch Metrics `DeadLetterErrors` | 0건 |
| 재시도 정상 | CloudWatch Metrics | 유효 메시지가 DLQ에 유입되지 않음 |

---

## 3. Knowledge Base 스키마 설계

### 3.1 Decision Knowledge Record 스키마

하나의 운영 시나리오를 표현하는 기본 단위:

```yaml
# Decision Knowledge Record (DKR) Schema v1
schema: decision-knowledge-record/v1

metadata:
  id: string                    # 고유 식별자 (예: "lambda-timeout-cold-start")
  name: string                  # 시나리오 이름
  description: string           # 시나리오 설명
  category: string              # 분류 (compute | database | network | storage | security | cost)
  service: string               # AWS 서비스 (lambda | rds | ec2 | s3 | dynamodb | ...)
  severity: string              # 기본 심각도 (critical | high | medium | low)
  tags: [string]                # 검색용 태그
  created_at: datetime
  updated_at: datetime
  source_refs:                  # 출처 목록 (추적 가능성)
    - title: string
      url: string
      type: enum [well_architected | troubleshooting_guide | prescriptive_guidance | repost_kc | official_doc | ssm_runbook]

triggers:
  - type: enum [alarm | metric_threshold | log_pattern | event_bridge | manual]
    description: string
    condition: string            # 감지 조건 (CEL 또는 JSONata 표현식)
    metrics:                     # 관련 CloudWatch 메트릭
      - namespace: string       # 예: "AWS/Lambda"
        metric_name: string     # 예: "Throttles"
        statistic: string       # 예: "Sum"
        period: number          # 초
        threshold: number
        comparison_operator: string

symptoms:
  - id: string
    description: string
    detection_method: string     # 감지 방법
    log_query: string            # CloudWatch Logs Insights 쿼리 (선택)
    api_call: string             # 확인용 AWS API 호출 (선택)

diagnosis:
  decision_tree:
    - step: number
      question: string           # 무엇을 확인할 것인가?
      check:                     # 확인 방법
        api: string              # AWS API 호출
        cli: string              # AWS CLI 명령어
        metric: string           # CloudWatch 메트릭
        log_query: string        # 로그 쿼리
      branches:
        - condition: string      # 판단 조건
          result: string         # 원인 코드 또는 다음 단계
          next_step: number      # 다음 진단 단계 (선택)

root_causes:
  - code: string                 # 원인 코드 (예: "TIMEOUT-COLD")
    name: string                 # 원인 이름
    description: string
    probability: enum [high | medium | low]  # 발생 확률 (초기 추정)
    related_symptoms: [string]   # 관련 증상 ID

remediation:
  - root_cause_code: string      # 매핑될 근본 원인 코드
    actions:
      - order: number
        name: string
        description: string
        type: enum [aws_cli | aws_api | cdk | ssm_automation | manual | code_change]
        command: string           # 실행 명령/코드
        rollback_command: string  # 롤백 명령 (선택)
        risk: enum [low | medium | high]
        requires_approval: boolean  # 인간 승인 필요 여부
        estimated_impact: string   # 비용/성능 영향
    alternative_actions:
      - name: string
        description: string
        tradeoff: string          # 대안의 트레이드오프

guardrails:
  pre_conditions:
    - description: string
      check: string               # 확인 조건
      block: boolean              # 조건 불충족 시 차단 여부
  post_conditions:
    - description: string
      check: string
      auto_rollback: boolean      # 자동 롤백 여부

verification:
  checks:
    - name: string
      method: string              # 확인 방법
      expected: string            # 기대 결과
      metric:                     # CloudWatch 메트릭 (선택)
        namespace: string
        metric_name: string
        statistic: string
        threshold: string
  stability_window: number        # 안정성 확인 시간 (초)
  success_criteria: string        # 전체 성공 기준

escalation:
  auto_remediate: boolean         # 자동 조치 가능 여부
  approval_required: boolean      # 승인 필요 여부
  escalation_timeout: number      # 에스컬레이션 타임아웃 (초)
  notify: [string]                # 알림 대상
```

### 3.2 시나리오 레지스트리 스키마

여러 Decision Knowledge Record를 관리하는 레지스트리:

```yaml
# Decision Knowledge Registry Schema v1
schema: decision-knowledge-registry/v1

registry:
  name: string                   # 레지스트리 이름
  description: string
  version: string

  categories:
    - id: string
      name: string
      description: string
      services: [string]

  scenarios:
    - ref: string                # DKR 파일 경로 또는 ID
      category: string
      priority: number           # 우선순위 (1 = 최우선)

  mappings:
    # oh-my-aws Harness 파이프라인 매핑
    observe:
      - trigger_type: string
        scenario_refs: [string]
    reason:
      - symptom_pattern: string
        scenario_refs: [string]
    act:
      - action_type: string
        scenario_refs: [string]
    verify:
      - check_type: string
        scenario_refs: [string]
```

---

## 4. Lambda 타임아웃/쓰로틀링 Decision Knowledge (정규화된 전체 레코드)

### 4.1 타임아웃 시나리오: 콜드 스타트로 인한 지연

```yaml
schema: decision-knowledge-record/v1

metadata:
  id: "lambda-timeout-cold-start"
  name: "Lambda 콜드 스타트로 인한 타임아웃"
  description: "Lambda 함수의 초기화(Init) 시간이 과도하여 실행 타임아웃 발생"
  category: "compute"
  service: "lambda"
  severity: "high"
  tags: ["lambda", "timeout", "cold-start", "latency", "serverless"]
  source_refs:
    - title: "Lambda Troubleshooting - Invocation Issues"
      url: "https://docs.aws.amazon.com/lambda/latest/dg/troubleshooting-invocation.html"
      type: "troubleshooting_guide"
    - title: "Lambda Provisioned Concurrency"
      url: "https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html"
      type: "official_doc"
    - title: "Well-Architected Serverless Lens - Lambda Performance"
      url: "https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/aws-lambda-2.html"
      type: "well_architected"
    - title: "Lambda Troubleshoot Invocation Timeouts (re:Post)"
      url: "https://repost.aws/knowledge-center/lambda-troubleshoot-invocation-timeouts"
      type: "repost_kc"

triggers:
  - type: "log_pattern"
    description: "Lambda 로그에 timeout 메시지 발생"
    condition: "@message like 'Task timed out' OR @message like 'Status: timeout'"
    log_query: |
      fields @timestamp, @requestId, @message, @logStream
      | filter @message like "Status: timeout"
      | sort @timestamp desc
      | limit 100

symptoms:
  - id: "s1"
    description: "Init Duration이 실행 시간의 50% 이상"
    detection_method: "CloudWatch Logs에서 Init Duration 필드 확인"
    log_query: |
      filter @type = "REPORT"
      | stats max(@initDuration) as maxInit, avg(@initDuration) as avgInit, avg(@duration) as avgDuration
      | eval initRatio = maxInit / (maxInit + avgDuration)
  - id: "s2"
    description: "Duration p95/p99가 설정 타임아웃에 근접"
    detection_method: "CloudWatch Metrics 확인"
    metric: "AWS/Lambda | Duration | p95"
  - id: "s3"
    description: "첫 번째 호출 또는 장기 유휴 후 호출에서만 발생"
    detection_method: "시간 패턴 분석"

diagnosis:
  decision_tree:
    - step: 1
      question: "Init Duration이 비정상적으로 긴가?"
      check:
        log_query: |
          filter @type = "REPORT"
          | stats max(@initDuration) by bin(5m)
      branches:
        - condition: "Init Duration > 1초 (Python) 또는 > 5초 (Java)"
          result: "COLD-START-CONFIRMED"
          next_step: 2
        - condition: "Init Duration 정상"
          result: "NOT_COLD_START"
          next_step: 0  # 다른 원인 탐색
    - step: 2
      question: "함수 런타임이 Java인가?"
      check:
        api: "GetFunctionConfiguration → Runtime"
      branches:
        - condition: "Runtime starts with 'java'"
          result: "JAVA_COLD_START"
          next_step: 3
        - condition: "Other runtime"
          result: "GENERAL_COLD_START"
          next_step: 4
    - step: 3
      question: "SnapStart가 활성화되어 있는가?"
      check:
        api: "GetFunctionConfiguration → SnapStart"
      branches:
        - condition: "SnapStart not configured"
          result: "TIMEOUT-COLD-JAVA-NOSNAP"
          next_step: 0
        - condition: "SnapStart configured"
          result: "TIMEOUT-COLD-OTHER"  # SnapStart로 해결 안 됨
          next_step: 4

root_causes:
  - code: "TIMEOUT-COLD-JAVA-NOSNAP"
    name: "Java 런타임 콜드 스타트 (SnapStart 미사용)"
    description: "Java Lambda에서 SnapStart 미활성화로 인한 긴 초기화 시간"
    probability: "high"
    related_symptoms: ["s1", "s2", "s3"]
  - code: "TIMEOUT-COLD-GENERAL"
    name: "일반 콜드 스타트 (의존성 과다)"
    description: "함수의 의존성/레이어 크기가 커서 초기화 시간 과다"
    probability: "medium"
    related_symptoms: ["s1", "s2", "s3"]

remediation:
  - root_cause_code: "TIMEOUT-COLD-JAVA-NOSNAP"
    actions:
      - order: 1
        name: "SnapStart 활성화"
        description: "Java Lambda의 초기화 단계를 사전 실행하여 콜드 스타트 제거"
        type: "aws_cli"
        command: |
          aws lambda update-function-configuration \
            --function-name <FUNCTION_NAME> \
            --snap-start ApplyOn=PublishedVersions
        rollback_command: |
          aws lambda update-function-configuration \
            --function-name <FUNCTION_NAME> \
            --snap-start ApplyOn=None
        risk: "low"
        requires_approval: false
        estimated_impact: "비용 영향 없음 (SnapStart 자체 무료)"
      - order: 2
        name: "버전/별칭 게시 후 SnapStart 적용 확인"
        description: "SnapStart는 Published Versions에만 적용됨"
        type: "aws_cli"
        command: |
          aws lambda publish-version --function-name <FUNCTION_NAME>
          aws lambda update-alias --function-name <FUNCTION_NAME> --name LIVE --function-version 1
        risk: "low"
        requires_approval: false
        estimated_impact: "없음"

  - root_cause_code: "TIMEOUT-COLD-GENERAL"
    actions:
      - order: 1
        name: "Provisioned Concurrency 활성화"
        description: "사전 초기화된 실행 환경 유지하여 콜드 스타트 제거"
        type: "aws_cli"
        command: |
          aws lambda put-provisioned-concurrency-config \
            --function-name <FUNCTION_NAME> \
            --qualifier <ALIAS_NAME> \
            --provisioned-concurrent-executions <PC_COUNT>
        rollback_command: |
          aws lambda delete-provisioned-concurrency-config \
            --function-name <FUNCTION_NAME> \
            --qualifier <ALIAS_NAME>
        risk: "medium"
        requires_approval: true
        estimated_impact: |
          월 비용 = PC_COUNT × Memory_GB × $0.0000041667/GB-s × 2,592,000s
          예: 5개 × 0.5GB × $0.0000041667 × 2,592,000 = 약 $27/월
      - order: 2
        name: "의존성/레이어 크기 최소화"
        description: "불필요한 의존성 제거, Lazy Loading 적용"
        type: "code_change"
        command: "애플리케이션 코드 수정"
        risk: "medium"
        requires_approval: true
        estimated_impact: "개발 공수 필요"
    alternative_actions:
      - name: "타임아웃 증설만으로 대응"
        description: "Provisioned Concurrency 없이 타임아웃만 늘리기"
        tradeoff: "비용 절감 but 첫 응답 지연 유지, SLA 위반 가능"

guardrails:
  pre_conditions:
    - description: "Provisioned Concurrency 적용 전 비용 영향 계산"
      check: "월 예상 비용을 사용자에게 표시"
      block: true
    - description: "Alias가 존재하는지 확인 (PC는 Alias에 적용)"
      check: "aws lambda get-alias --function-name <FN> --name <ALIAS>"
      block: true
  post_conditions:
    - description: "ProvisionedConcurrencySpilloverInvocations 확인"
      check: "SpilloverInvocations ≈ 0"
      auto_rollback: false

verification:
  checks:
    - name: "타임아웃 메시지 소멸"
      method: "CloudWatch Logs Insights 재쿼리"
      expected: "Status: timeout 메시지 0건 (5분 윈도우)"
      log_query: |
        fields @timestamp, @message
        | filter @message like "Status: timeout"
        | stats count() by bin(5m)
    - name: "Init Duration 감소"
      method: "CloudWatch Logs"
      expected: "Init Duration < 100ms (PC/SnapStart 적용 시)"
    - name: "Duration p95 여유 확보"
      method: "CloudWatch Metrics"
      expected: "Duration p95 < timeout × 0.8"
      metric:
        namespace: "AWS/Lambda"
        metric_name: "Duration"
        statistic: "p95"
        threshold: "< configured timeout × 0.8"
  stability_window: 300  # 5분
  success_criteria: "타임아웃 메시지 0건, Duration p95 < timeout × 0.8"

escalation:
  auto_remediate: false
  approval_required: true
  escalation_timeout: 600
  notify: ["oncall"]
```

### 4.2 쓰로틀링 시나리오: 동시성 한계 도달

```yaml
schema: decision-knowledge-record/v1

metadata:
  id: "lambda-throttle-concurrency-exhaustion"
  name: "Lambda 동시성 한계 도달로 인한 쓰로틀링"
  description: "Lambda 함수의 동시 실행 수가 계정/함수 한계에 도달하여 429 Throttling 발생"
  category: "compute"
  service: "lambda"
  severity: "high"
  tags: ["lambda", "throttling", "concurrency", "rate-limit", "serverless"]
  source_refs:
    - title: "Lambda Concurrency"
      url: "https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html"
      type: "official_doc"
    - title: "Lambda Scaling Behavior"
      url: "https://docs.aws.amazon.com/lambda/latest/dg/scaling-behavior.html"
      type: "official_doc"
    - title: "Lambda Troubleshoot Throttling (re:Post)"
      url: "https://repost.aws/knowledge-center/lambda-troubleshoot-throttling"
      type: "repost_kc"
    - title: "Lambda Reserved Concurrency (re:Post)"
      url: "https://repost.aws/knowledge-center/lambda-reserved-concurrency"
      type: "repost_kc"
    - title: "Lambda Concurrency Limit Increase (re:Post)"
      url: "https://repost.aws/knowledge-center/lambda-concurrency-limit-increase"
      type: "repost_kc"

triggers:
  - type: "metric_threshold"
    description: "Lambda Throttles 메트릭이 0 초과"
    condition: "AWS/Lambda.Throttles.Sum > 0 for 2 consecutive periods of 60s"
    metrics:
      - namespace: "AWS/Lambda"
        metric_name: "Throttles"
        statistic: "Sum"
        period: 60
        threshold: 0
        comparison_operator: "GreaterThanThreshold"

symptoms:
  - id: "s1"
    description: "Throttles 메트릭 > 0"
    detection_method: "CloudWatch Metrics"
    metric: "AWS/Lambda | Throttles | Sum"
  - id: "s2"
    description: "HTTP 429 / TooManyRequestsException"
    detection_method: "Lambda 로그, API Gateway 로그"
    log_query: |
      filter @message like "TooManyRequestsException" or @message like "Rate exceeded"
  - id: "s3"
    description: "ConcurrentExecutions가 한계에 근접"
    detection_method: "CloudWatch Metrics"
    metric: "AWS/Lambda | ConcurrentExecutions | Maximum"

diagnosis:
  decision_tree:
    - step: 1
      question: "Lambda 자체가 쓰로틀된 것인가? (하위 서비스가 아닌)"
      check:
        metric: "AWS/Lambda | Throttles | Sum > 0"
      branches:
        - condition: "Throttles > 0 for this function"
          result: "LAMBDA_THROTTLE_CONFIRMED"
          next_step: 2
        - condition: "Throttles = 0, but downstream calls failing"
          result: "DOWNSTREAM_THROTTLE"  # 다른 시나리오
          next_step: 0
    - step: 2
      question: "어느 수준의 동시성 한계에 도달했는가?"
      check:
        cli: |
          aws lambda get-account-settings --query 'AccountLimit.ConcurrentExecutions'
          aws lambda get-function-concurrency --function-name <FN> --query 'ReservedConcurrentExecutions' 2>/dev/null || echo "No reserved"
      branches:
        - condition: "ConcurrentExecutions ≈ AccountLimit"
          result: "THROTTLE-ACCT"
          next_step: 0
        - condition: "Reserved Concurrency 설정됨, ConcurrentExecutions ≈ Reserved"
          result: "THROTTLE-RESV"
          next_step: 3
        - condition: "Reserved = 0 (실수로 0 설정)"
          result: "THROTTLE-RESV-ZERO"
          next_step: 0
        - condition: "버스트 트래픽으로 인한 일시적 한계"
          result: "THROTTLE-BURST"
          next_step: 4
    - step: 3
      question: "Reserved Concurrency를 늘릴 여유가 있는가?"
      check:
        cli: "aws lambda get-account-settings --query 'AccountLimit.ConcurrentExecutions'"
      branches:
        - condition: "AccountLimit - sum(all reserved) >= needed"
          result: "THROTTLE-RESV-INCREASE"
          next_step: 0
        - condition: "AccountLimit 부족"
          result: "THROTTLE-ACCT"
          next_step: 0
    - step: 4
      question: "이벤트 소스가 SQS/DynamoDB Stream인가?"
      check:
        cli: "aws lambda list-event-source-mappings --function-name <FN>"
      branches:
        - condition: "Event source mapping exists"
          result: "THROTTLE-SRC"
          next_step: 0
        - condition: "No event source (synchronous)"
          result: "THROTTLE-BURST-SYNC"
          next_step: 0

root_causes:
  - code: "THROTTLE-ACCT"
    name: "계정 레벨 동시성 한계 도달"
    description: "해당 리전의 모든 Lambda 함수가 계정 동시성 한계를 공유하여 경합 발생"
    probability: "medium"
    related_symptoms: ["s1", "s2", "s3"]
  - code: "THROTTLE-RESV"
    name: "함수 Reserved Concurrency 한계 도달"
    description: "특정 함수에 할당된 Reserved Concurrency에 도달"
    probability: "high"
    related_symptoms: ["s1", "s2", "s3"]
  - code: "THROTTLE-RESV-ZERO"
    name: "Reserved Concurrency 0 설정 (실수)"
    description: "Reserved Concurrency를 0으로 설정하여 함수가 완전히 차단됨"
    probability: "low"
    related_symptoms: ["s1", "s2"]
  - code: "THROTTLE-BURST"
    name: "버스트 트래픽으로 인한 스케일링 한계"
    description: "초기 버스트 1000/10s 한계를 초과하는 트래픽 급증"
    probability: "medium"
    related_symptoms: ["s1", "s2"]
  - code: "THROTTLE-SRC"
    name: "이벤트 소스(SQS/Stream) 처리 병목"
    description: "SQS 또는 DynamoDB Stream의 이벤트 소스 설정이 처리량에 맞지 않음"
    probability: "medium"
    related_symptoms: ["s1", "s3"]

remediation:
  - root_cause_code: "THROTTLE-ACCT"
    actions:
      - order: 1
        name: "계정 동시성 한도 증가 요청"
        description: "Service Quotas를 통해 리전별 동시성 한도 증가 요청"
        type: "manual"
        command: |
          # Service Quotas 콘솔 또는 CLI로 증가 요청
          aws service-quotes request-service-quota-increase \
            --service-code lambda \
            --quota-code L-B99A9384 \
            --desired-value <NEW_LIMIT>
        risk: "low"
        requires_approval: true
        estimated_impact: "비용은 사용량에 비례, 한도 증가 자체는 무료"
      - order: 2
        name: "비중요 함수 Reserved Concurrency 낮추기"
        description: "중요 함수에 동시성 확보를 위해 비중요 함수의 할당량 조정"
        type: "aws_cli"
        command: |
          aws lambda put-function-concurrency \
            --function-name <LOW_PRIORITY_FN> \
            --reserved-concurrent-executions <REDUCED_COUNT>
        risk: "medium"
        requires_approval: true
        estimated_impact: "비중요 함수의 처리량 감소 가능"

  - root_cause_code: "THROTTLE-RESV"
    actions:
      - order: 1
        name: "Reserved Concurrency 증설"
        description: "함수의 Reserved Concurrency 한계를 증가"
        type: "aws_cli"
        command: |
          aws lambda put-function-concurrency \
            --function-name <FUNCTION_NAME> \
            --reserved-concurrent-executions <NEW_LIMIT>
        rollback_command: |
          aws lambda put-function-concurrency \
            --function-name <FUNCTION_NAME> \
            --reserved-concurrent-executions <ORIGINAL_LIMIT>
        risk: "low"
        requires_approval: false
        estimated_impact: "다른 함수의 사용 가능 동시성 감소 (총 한계 내에서)"
      - order: 2
        name: "Provisioned Concurrency 추가"
        description: "일정 수준의 사전 초기화된 실행 환경 유지"
        type: "aws_cli"
        command: |
          aws lambda put-provisioned-concurrency-config \
            --function-name <FUNCTION_NAME> \
            --qualifier <ALIAS_NAME> \
            --provisioned-concurrent-executions <PC_COUNT>
        risk: "medium"
        requires_approval: true
        estimated_impact: "월 비용 = PC_COUNT × Memory_GB × $0.0000041667/GB-s × 2,592,000s"

  - root_cause_code: "THROTTLE-RESV-ZERO"
    actions:
      - order: 1
        name: "Reserved Concurrency 0 해제"
        description: "실수로 설정된 0 값을 제거하거나 적절한 값으로 변경"
        type: "aws_cli"
        command: |
          aws lambda delete-function-concurrency --function-name <FUNCTION_NAME>
          # 또는 적절한 값으로 설정
          aws lambda put-function-concurrency \
            --function-name <FUNCTION_NAME> \
            --reserved-concurrent-executions <APPROPRIATE_VALUE>
        risk: "low"
        requires_approval: false
        estimated_impact: "함수가 정상적으로 실행 가능해짐"

  - root_cause_code: "THROTTLE-BURST"
    actions:
      - order: 1
        name: "SQS/DynamoDB Stream으로 이벤트 버퍼링"
        description: "직접 동기 호출을 비동기 큐 기반으로 전환하여 트래픽 버퍼링"
        type: "aws_cli"
        command: |
          aws lambda create-event-source-mapping \
            --function-name <FUNCTION_NAME> \
            --batch-size 10 \
            --maximum-batching-window-in-seconds 5 \
            --event-source-arn <QUEUE_ARN>
        risk: "medium"
        requires_approval: true
        estimated_impact: "아키텍처 변경, 처리 지연 증가 가능"
      - order: 2
        name: "SQS 이벤트 소스 Max Concurrency 설정"
        description: "SQS 이벤트 소스의 최대 동시성을 명시적으로 제한하여 안정적 처리"
        type: "aws_cli"
        command: |
          aws lambda update-event-source-mapping \
            --uuid <UUID> \
            --scaling-config '{"MaximumConcurrency": <VALUE>}'
        risk: "low"
        requires_approval: false
        estimated_impact: "처리 속도 제한 but 쓰로틀링 방지"

  - root_cause_code: "THROTTLE-SRC"
    actions:
      - order: 1
        name: "SQS 이벤트 소스 동시성 최적화"
        description: "배치 크기, 배치 윈도우, 최대 동시성 조정"
        type: "aws_cli"
        command: |
          aws lambda update-event-source-mapping \
            --uuid <UUID> \
            --batch-size <BATCH_SIZE> \
            --maximum-batching-window-in-seconds <WINDOW> \
            --scaling-config '{"MaximumConcurrency": <MAX_CONCURRENCY>}'
        risk: "low"
        requires_approval: false
        estimated_impact: "처리량 변화"
      - order: 2
        name: "Provisioned Poller 설정"
        description: "SQS 이벤트 소스의 폴러 수를 사전 프로비저닝"
        type: "aws_cli"
        command: |
          aws lambda update-event-source-mapping \
            --uuid <UUID> \
            --provisioned-poller-config '{"MinimumPollers":5,"MaximumPollers":100}'
        risk: "low"
        requires_approval: false
        estimated_impact: "비용 미미"

guardrails:
  pre_conditions:
    - description: "Reserved Concurrency 0 실수 방지"
      check: "reservedConcurrentExecutions != 0"
      block: true
    - description: "계정 동시성 여유 확인"
      check: "AccountLimit.ConcurrentExecutions - sum(reserved) >= requested"
      block: false  # 경고만
    - description: "Provisioned Concurrency 비용 영향 계산"
      check: "월 예상 비용을 사용자에게 표시"
      block: true
  post_conditions:
    - description: "Throttles 메트릭 0 확인"
      check: "AWS/Lambda.Throttles.Sum = 0 for 5 minutes"
      auto_rollback: true
    - description: "ConcurrentExecutions 안정"
      check: "ConcurrentExecutions < AccountLimit × 0.7"
      auto_rollback: false

verification:
  checks:
    - name: "쓰로틀링 해소"
      method: "CloudWatch Metrics"
      expected: "Throttles = 0 (지속 5분)"
      metric:
        namespace: "AWS/Lambda"
        metric_name: "Throttles"
        statistic: "Sum"
        threshold: "= 0"
    - name: "동시성 여유 확보"
      method: "CloudWatch Metrics"
      expected: "ConcurrentExecutions < AccountLimit × 0.7"
    - name: "SQS 처리 정상화"
      method: "CloudWatch Metrics"
      expected: "ApproximateAgeOfOldestMessage 안정/감소, NumberOfMessagesDeleted > 0"
    - name: "오류율 정상"
      method: "CloudWatch Metrics"
      expected: "Errors 감소 추세"
  stability_window: 300
  success_criteria: "Throttles = 0, ConcurrentExecutions < AccountLimit × 0.7"

escalation:
  auto_remediate: false
  approval_required: true
  escalation_timeout: 600
  notify: ["oncall"]
```

### 4.3 복합 시나리오: SQS 포이즌 필 메시지 재시도 폭주

```yaml
schema: decision-knowledge-record/v1

metadata:
  id: "lambda-sqs-poison-pill-retry-storm"
  name: "SQS 포이즌 필 메시지로 인한 Lambda 재시도 폭주"
  description: "SQS에서 처리 불가능한 메시지가 반복 재시도되면서 정상 메시지 처리까지 방해"
  category: "compute"
  service: "lambda"
  severity: "high"
  tags: ["lambda", "sqs", "poison-pill", "dlq", "retry", "batch"]
  source_refs:
    - title: "Lambda SQS Error Handling"
      url: "https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html"
      type: "official_doc"
    - title: "Lambda SQS Scaling"
      url: "https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-scaling.html"
      type: "official_doc"
    - title: "Prescriptive Guidance - Partial Batch Response Best Practices"
      url: "https://docs.aws.amazon.com/prescriptive-guidance/latest/lambda-event-filtering-partial-batch-responses-for-sqs/best-practices-partial-batch-responses.html"
      type: "prescriptive_guidance"
    - title: "Lambda Retrying Valid SQS Messages (re:Post)"
      url: "https://repost.aws/knowledge-center/lambda-retrying-valid-sqs-messages"
      type: "repost_kc"
    - title: "Lambda Idempotent Functions (re:Post)"
      url: "https://repost.aws/knowledge-center/lambda-function-idempotent"
      type: "repost_kc"

triggers:
  - type: "metric_threshold"
    description: "SQS 대기열 길이 증가 + DLQ 메시지 급증"
    condition: "SQS.ApproximateNumberOfMessagesNotVisible 증가 AND SQS NumberOfMessagesReceived >> NumberOfMessagesDeleted"
    metrics:
      - namespace: "AWS/SQS"
        metric_name: "ApproximateNumberOfMessagesNotVisible"
        statistic: "Average"
        period: 300
        threshold: "급증 추세"
      - namespace: "AWS/SQS"
        metric_name: "ApproximateNumberOfMessagesVisible"
        statistic: "Average"
        period: 300
        threshold: "지속 증가"

symptoms:
  - id: "s1"
    description: "SQS 대기열 메시지 수 지속 증가"
    detection_method: "CloudWatch Metrics"
    metric: "AWS/SQS | ApproximateNumberOfMessagesVisible | Average"
  - id: "s2"
    description: "DLQ에 유효한 메시지가 유입됨"
    detection_method: "DLQ 메시지 검사"
    cli: "aws sqs receive-message --queue-url <DLQ_URL> --max-number-of-messages 10"
  - id: "s3"
    description: "Lambda가 동일 메시지를 반복 처리"
    detection_method: "CloudWatch Logs에서 messageId 중복 확인"
    log_query: |
      fields @timestamp, @message
      | parse @message "* messageId: *" as timestamp, messageId
      | stats count() by messageId
      | filter count > 1
      | sort count desc

diagnosis:
  decision_tree:
    - step: 1
      question: "ReportBatchItemFailures가 활성화되어 있는가?"
      check:
        cli: |
          aws lambda get-event-source-mapping --uuid <UUID> --query 'FunctionResponseTypes'
      branches:
        - condition: "ReportBatchItemFailures NOT in list"
          result: "MISSING_PARTIAL_BATCH"
          next_step: 3
        - condition: "ReportBatchItemFailures present"
          result: "PARTIAL_BATCH_ENABLED"
          next_step: 2
    - step: 2
      question: "DLQ가 설정되어 있는가?"
      check:
        cli: "aws sqs get-queue-attributes --queue-url <QUEUE_URL> --attribute-names RedrivePolicy"
      branches:
        - condition: "RedrivePolicy exists"
          result: "DLQ_CONFIGURED"
          next_step: 3
        - condition: "No RedrivePolicy"
          result: "NO_DLQ"
          next_step: 3
    - step: 3
      question: "Visibility Timeout이 Lambda 타임아웃의 6배 이상인가?"
      check:
        cli: |
          aws sqs get-queue-attributes --queue-url <QUEUE_URL> --attribute-names VisibilityTimeout
          aws lambda get-function-configuration --function-name <FN> --query 'Timeout'
      branches:
        - condition: "VisibilityTimeout < 6 × LambdaTimeout"
          result: "VISIBILITY_TIMEOUT_MISCONFIGURED"
          next_step: 0
        - condition: "VisibilityTimeout >= 6 × LambdaTimeout"
          result: "VISIBILITY_OK"
          next_step: 0

root_causes:
  - code: "POISON-MISSING-PARTIAL-BATCH"
    name: "Partial Batch Response 미활성화"
    description: "배치 내 일부 메시지 실패 시 전체 배치가 재시도되어 정상 메시지도 반복 처리됨"
    probability: "high"
    related_symptoms: ["s1", "s2", "s3"]
  - code: "POISON-NO-DLQ"
    name: "DLQ 미설정"
    description: "최대 재시도 초과 후 메시지가 손실됨"
    probability: "medium"
    related_symptoms: ["s2"]
  - code: "POISON-VISIBILITY"
    name: "Visibility Timeout 오설정"
    description: "Visibility Timeout이 너무 짧아 처리 중인 메시지가 다시 큐에 노출됨"
    probability: "medium"
    related_symptoms: ["s1", "s3"]
  - code: "POISON-NO-IDEMPOTENCY"
    name: "멱등성(Idempotency) 미보장"
    description: "재시도 시 동일 작업이 중복 실행됨"
    probability: "medium"
    related_symptoms: ["s3"]

remediation:
  - root_cause_code: "POISON-MISSING-PARTIAL-BATCH"
    actions:
      - order: 1
        name: "ReportBatchItemFailures 활성화"
        description: "배치 내 실패한 메시지만 재시도되도록 설정"
        type: "aws_cli"
        command: |
          aws lambda update-event-source-mapping \
            --uuid <UUID> \
            --function-response-types ReportBatchItemFailures
        risk: "low"
        requires_approval: false
        estimated_impact: "Lambda 코드에서 batchItemFailures 응답 필요"
      - order: 2
        name: "Lambda 코드 수정 - partial batch response 반환"
        description: "실패한 메시지 ID를 포함한 응답 형식으로 코드 수정"
        type: "code_change"
        command: |
          # Python 예시
          return {
              "batchItemFailures": [
                  {"itemIdentifier": failed_message_id}
              ]
          }
        risk: "medium"
        requires_approval: true
        estimated_impact: "코드 배포 필요"

  - root_cause_code: "POISON-NO-DLQ"
    actions:
      - order: 1
        name: "DLQ 생성 및 연결"
        description: "최대 재시도 초과 메시지를 DLQ로 이동"
        type: "aws_cli"
        command: |
          aws sqs create-queue --queue-name <QUEUE_NAME>-dlq
          aws sqs set-queue-attributes \
            --queue-url <QUEUE_URL> \
            --attributes '{
              "RedrivePolicy": "{\"deadLetterTargetArn\":\"<DLQ_ARN>\",\"maxReceiveCount\":\"5\"}"
            }'
        risk: "low"
        requires_approval: false
        estimated_impact: "메시지 손실 방지, DLQ 모니터링 필요"

  - root_cause_code: "POISON-VISIBILITY"
    actions:
      - order: 1
        name: "Visibility Timeout 조정"
        description: "Lambda 타임아웃의 6배 이상으로 설정 (AWS 권장)"
        type: "aws_cli"
        command: |
          # Lambda timeout의 6배로 설정
          aws sqs set-queue-attributes \
            --queue-url <QUEUE_URL> \
            --attributes VisibilityTimeout=<6_TIMES_LAMBDA_TIMEOUT>
        risk: "low"
        requires_approval: false
        estimated_impact: "메시지 재시도 간격 증가"

  - root_cause_code: "POISON-NO-IDEMPOTENCY"
    actions:
      - order: 1
        name: "멱등성 처리 로직 추가"
        description: "메시지 ID 또는 비즈니스 키 기반 중복 실행 방지"
        type: "code_change"
        command: |
          # AWS Lambda Powertools for Python - idempotency 예시
          from aws_lambda_powertools.utilities.idempotency import idempotent

          @idempotent
          def handler(event, context):
              # 비즈니스 로직
              pass
        risk: "medium"
        requires_approval: true
        estimated_impact: "DynamoDB 비용 미발생 (idempotency store)"

guardrails:
  pre_conditions:
    - description: "DLQ 설정 전 큐가 비어있는지 확인"
      check: "ApproximateNumberOfMessagesVisible = 0 또는 영향 최소화 계획 수립"
      block: false
    - description: "Visibility Timeout 변경 시 처리 중인 메시지 영향 확인"
      check: "ApproximateNumberOfMessagesNotVisible 확인"
      block: false
  post_conditions:
    - description: "DLQ에 유효 메시지 유입 중지 확인"
      check: "DLQ 메시지 검사하여 모두 포이즌 필인지 확인"
      auto_rollback: false
    - description: "큐 처리 속도 정상화"
      check: "NumberOfMessagesDeleted > 0 지속"
      auto_rollback: false

verification:
  checks:
    - name: "큐 대기 메시지 감소"
      method: "CloudWatch Metrics"
      expected: "ApproximateNumberOfMessagesVisible 감소 추세"
      metric:
        namespace: "AWS/SQS"
        metric_name: "ApproximateNumberOfMessagesVisible"
        statistic: "Average"
        threshold: "감소 추세"
    - name: "DLQ에 유효 메시지 없음"
      method: "DLQ 메시지 수동 검사"
      expected: "DLQ 메시지가 모두 처리 불가능한 포이즌 필"
    - name: "메시지 삭제율 정상"
      method: "CloudWatch Metrics"
      expected: "NumberOfMessagesDeleted 지속 > 0"
    - name: "재시도 감소"
      method: "CloudWatch Logs"
      expected: "동일 messageId 반복 처리 감소"
      log_query: |
        fields @timestamp, @message
        | parse @message "* messageId: *" as ts, mid
        | stats count() by mid
        | filter count <= 2
  stability_window: 600
  success_criteria: "큐 대기 메시지 감소, DLQ에 유효 메시지 없음, 재시도 감소"

escalation:
  auto_remediate: false
  approval_required: true
  escalation_timeout: 600
  notify: ["oncall"]
```

---

## 5. Harness 아키텍처: Knowledge Base 레이어 설계

### 5.1 oh-my-aws 전체 아키텍처에 KB 레이어 배치

```
┌─────────────────────────────────────────────────────────────────────┐
│                        oh-my-aws Harness                            │
│                                                                     │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐        │
│  │ Observe  │──▶│ Reason   │──▶│   Act    │──▶│ Verify   │        │
│  │          │   │          │   │          │   │          │        │
│  │ CloudWatch│  │ Decision │   │ AWS CLI  │   │ Metrics  │        │
│  │ Logs      │  │ Engine   │   │ CDK      │   │ Logs     │        │
│  │ Metrics   │  │          │   │ SDK      │   │ Diff     │        │
│  │ Events    │  │          │   │ SSM Auto │   │ Check    │        │
│  │ Config    │  │          │   │          │   │          │        │
│  └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘        │
│       │              │              │              │                │
│       │    ┌─────────┴──────────────┤──────────────┘                │
│       │    │                        │                               │
│       ▼    ▼                        ▼                               │
│  ┌──────────────────────────────────────────┐                       │
│  │        Knowledge Base Layer (NEW)        │                       │
│  │                                          │                       │
│  │  ┌────────────────┐  ┌────────────────┐  │                       │
│  │  │ Decision       │  │ Action         │  │                       │
│  │  │ Knowledge      │  │ Templates      │  │                       │
│  │  │ Records (DKR)  │  │ (CLI/CDK/SSM)  │  │                       │
│  │  └────────────────┘  └────────────────┘  │                       │
│  │  ┌────────────────┐  ┌────────────────┐  │                       │
│  │  │ Verification   │  │ Guardrails     │  │                       │
│  │  │ Checklists     │  │ (Pre/Post)     │  │                       │
│  │  └────────────────┘  └────────────────┘  │                       │
│  │  ┌────────────────┐  ┌────────────────┐  │                       │
│  │  │ Escalation     │  │ Source Refs    │  │                       │
│  │  │ Rules          │  │ (Traceability) │  │                       │
│  │  └────────────────┘  └────────────────┘  │                       │
│  └──────────────────────────────────────────┘                       │
│       │                                                             │
│       ▼                                                             │
│  ┌──────────────────┐                                               │
│  │      Audit       │                                               │
│  │                  │                                               │
│  │ Decision Trace   │                                               │
│  │ Action Log       │                                               │
│  │ Evidence Bundle  │                                               │
│  └──────────────────┘                                               │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### 5.2 Knowledge Base 레이어 내부 구조

```
knowledge-base/
├── registry.yaml                      # 시나리오 레지스트리
├── schemas/
│   ├── decision-knowledge-record.v1.yaml   # DKR 스키마
│   └── registry.v1.yaml                    # 레지스트리 스키마
├── scenarios/
│   ├── compute/
│   │   ├── lambda-timeout-cold-start.yaml
│   │   ├── lambda-throttle-concurrency-exhaustion.yaml
│   │   ├── lambda-sqs-poison-pill-retry-storm.yaml
│   │   ├── ec2-unreachable.yaml           # (향후)
│   │   └── ecs-deployment-failure.yaml    # (향후)
│   ├── database/
│   │   ├── rds-performance-degradation.yaml  # (향후)
│   │   └── dynamodb-throttling.yaml          # (향후)
│   ├── network/
│   │   ├── vpc-unreachable.yaml              # (향후)
│   │   └── cloudfront-cache-issues.yaml      # (향후)
│   ├── storage/
│   │   └── s3-access-denied.yaml             # (향후)
│   └── security/
│       └── acm-tls-issues.yaml               # (향후)
└── templates/
    ├── cli-commands.yaml               # CLI 명령어 템플릿
    ├── cdk-constructs.yaml             # CDK construct 패턴
    ├── cw-queries.yaml                 # CloudWatch Logs Insights 쿼리
    └── alarm-definitions.yaml          # 표준 알람 정의
```

### 5.3 Harness 파이프라인과 KB의 상호작용

#### Observe 단계

```yaml
observe:
  input: "CloudWatch 알람, EventBridge 이벤트, 수동 트리거"
  kb_interaction:
    - action: "알람/이벤트를 KB 트리거 조건과 매칭"
      query: |
        SELECT scenario_id FROM registry.triggers
        WHERE condition MATCHES incoming_event
    - action: "해당 시나리오의 symptoms 쿼리 실행"
      query: |
        SELECT symptoms FROM scenario WHERE id = :matched_id
    - output: "매칭된 시나리오 ID + 수집된 증상 데이터"
```

#### Reason 단계

```yaml
reason:
  input: "Observe에서 수집한 증상 데이터 + 매칭된 시나리오"
  kb_interaction:
    - action: "진단 결정 트리 순회"
      process: |
        FOR EACH step IN diagnosis.decision_tree:
          EXECUTE step.check (API/CLI/metric/log_query)
          EVALUATE step.branches
          SELECT matching branch
          CONTINUE or TERMINATE
    - action: "근본 원인 식별"
      process: |
        MAP diagnosis_result TO root_causes.code
        RANK by probability + evidence
    - action: "조치 계획 수립"
      process: |
        SELECT remediation.actions WHERE root_cause_code = identified_cause
        EVALUATE guardrails.pre_conditions
        FLAG blocked actions
        PRESENT plan to user (if approval_required)
    - output: "식별된 근본 원인 + 조치 계획 + 가드레일 상태"
```

#### Act 단계

```yaml
act:
  input: "승인된 조치 계획"
  kb_interaction:
    - action: "조치 실행"
      process: |
        FOR EACH action IN approved_plan:
          IF action.requires_approval AND NOT approved:
            SKIP and LOG
          ELSE:
            EXECUTE action.command
            RECORD result
            IF failed:
              EXECUTE action.rollback_command (if exists)
              LOG failure
    - action: "롤백 템플릿 사용"
      source: "remediation.actions[].rollback_command"
    - output: "실행 결과 + 롤백 이력"
```

#### Verify 단계

```yaml
verify:
  input: "Act 실행 결과"
  kb_interaction:
    - action: "검증 체크리스트 실행"
      process: |
        FOR EACH check IN verification.checks:
          EXECUTE check.method
          COMPARE result WITH check.expected
          RECORD pass/fail
        WAIT verification.stability_window
        RE-RUN all checks
    - action: "성공 기준 평가"
      process: |
        EVALUATE verification.success_criteria
        IF NOT met:
          TRIGGER rollback or escalation
    - action: "post_conditions 확인"
      source: "guardrails.post_conditions"
    - output: "검증 결과 (pass/fail per check)"
```

#### Audit 단계

```yaml
audit:
  input: "전체 파이프라인 실행 이력"
  kb_interaction:
    - action: "결정 추적 기록"
      record: |
        - matched_scenario_id
        - diagnosis_steps_executed + results
        - root_cause_identified
        - actions_executed + results
        - verification_results
        - source_refs (어떤 공식 문서를 근거로 사용했는가)
    - action: "증거 번들 생성"
      contents: |
        - DKR ID + version
        - 수집된 메트릭/로그 스냅샷
        - 실행된 명령어 + 출력
        - 검증 결과
        - source_refs
    - output: "재현 가능한 감사 기록"
```

### 5.4 AWS 공식 런북/자동화와의 통합 포인트

oh-my-aws는 AWS가 이미 제공하는 자동화 런북을 `Act` 단계에서 활용할 수 있다:

| AWS 제공 자동화 | oh-my-aws 활용 방식 | 통합 계층 |
|----------------|-------------------|----------|
| **AWSSupport-TroubleshootLambdaInternetAccess** | VPC 내 Lambda 인터넷 접근 불가 시 진단 자동 실행 | `Act` - SSM Automation |
| **AWSSupport-TroubleshootLambdaS3Event** | S3 이벤트가 Lambda를 트리거하지 않을 때 진단 | `Act` - SSM Automation |
| **AWSSupport-RemediateLambdaS3Event** | S3→Lambda 이벤트 연결 자동 복구 | `Act` - SSM Automation |
| **AWS Health Event → EventBridge** | Lambda 서비스 이벤트 자동 감지 및 라우팅 | `Observe` - EventBridge |
| **CloudWatch Alarms** | 표준 Lambda 알람 정의를 KB에서 관리 | `Observe` - CloudWatch |
| **Service Quotas** | 동시성 한계 도달 시 자동 증가 요청 | `Act` - Service Quotas |

---

## 6. 다음 단계

### 6.1 즉시 수행 가능한 작업

1. **Decision Knowledge Record 파일 생성**
   - `knowledge-base/scenarios/compute/` 아래에 3개 YAML 파일 생성
   - 스키마 검증 스크립트 작성

2. **Harness 아키텍처 초안에 KB 레이어 반영**
   - `Reason` 엔진이 DKR을 읽어 결정 트리를 순회하는 인터페이스 정의
   - `Act` 엔진이 액션 템플릿을 실행하는 어댑터 계층 정의

3. **첫 번째 MVP 시나리오 구현**
   - Lambda 타임아웃/쓰로틀링 → Observe → Reason → Act → Verify 전체 흐름

### 6.2 확장 계획

| 우선순위 | 시나리오 | 소스 |
|----------|----------|------|
| 1 (현재) | Lambda 타임아웃/쓰로틀링 | 본 문서 4절 |
| 2 | RDS 성능 저하 | AWS RDS Troubleshooting Guide + Well-Architected |
| 3 | 배포 후 5xx 에러 | AWS DevOps Agent 사례 + CodeDeploy 문서 |
| 4 | DynamoDB 쓰로틀링 | DynamoDB Best Practices + Prescriptive Guidance |
| 5 | VPC 연결 불가 | VPC Troubleshooting + Network ACL 디버깅 |
| 6 | S3 Access Denied | IAM/S3 정책 분석 + re:Post KC |
| 7 | CloudFront 캐시 문제 | CloudFront Troubleshooting |
| 8 | SQS/SNS 메시지 처리 실패 | SQS Best Practices + DLQ 패턴 |

### 6.3 시험문제 지식의 간접 활용

AWS 자격증 문제를 직접 사용할 수는 없지만, 자격증이 평가하는 **지식 영역**은 DKR 작성 시 체크리스트로 활용할 수 있다:

```yaml
# 시험 대상 지식 영역을 커버리지 체크리스트로 활용
cert_coverage:
  saa_c03:  # Solutions Architect Associate
    domains:
      - "Secure Architectures"
      - "Resilient Architectures"
      - "High-Performing Architectures"
      - "Cost-Optimized Architectures"
    lambda_coverage:
      - "Provisioned Concurrency vs Reserved Concurrency 차이"
      - "VPC 내 Lambda 네트워킹"
      - "Lambda + SQS 통합 패턴"
      - "Lambda + DynamoDB Streams 패턴"
      - "Lambda 권한 모델 (resource-based vs execution role)"
    check: |
      FOR EACH cert_coverage item:
        ENSURE at least one DKR addresses this knowledge area
```

이 방식은 저작권 침해 없이, 자격증이 다루는 **주제 영역**을 커버리지 검증에만 활용하는 것이다.

---

## 7. 참고 자료

### AWS 공식 문서

- [Lambda Troubleshooting - Invocation Issues](https://docs.aws.amazon.com/lambda/latest/dg/troubleshooting-invocation.html)
- [Lambda Troubleshooting - Configuration](https://docs.aws.amazon.com/lambda/latest/dg/troubleshooting-configuration.html)
- [Lambda Concurrency](https://docs.aws.amazon.com/lambda/latest/dg/lambda-concurrency.html)
- [Lambda Scaling Behavior](https://docs.aws.amazon.com/lambda/latest/dg/scaling-behavior.html)
- [Lambda Monitoring Metrics](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- [Lambda Monitoring Concurrency](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-concurrency.html)
- [Lambda SQS Error Handling](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-errorhandling.html)
- [Lambda SQS Scaling](https://docs.aws.amazon.com/lambda/latest/dg/services-sqs-scaling.html)
- [Lambda Provisioned Concurrency](https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html)
- [Lambda Async Error Handling](https://docs.aws.amazon.com/lambda/latest/dg/invocation-async-error-handling.html)
- [Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)

### AWS Well-Architected

- [Well-Architected Serverless Lens - Reliability](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/rel-foundations.html)
- [Well-Architected Serverless Lens - Lambda](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/aws-lambda.html)
- [Well-Architected Serverless Lens - Lambda Performance](https://docs.aws.amazon.com/wellarchitected/latest/serverless-applications-lens/aws-lambda-2.html)
- [Well-Architected Reliability Pillar - Retries](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_limit_retries.html)
- [Well-Architected Reliability Pillar - Fail Fast](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_fail_fast.html)
- [Well-Architected Operational Readiness Reviews](https://docs.aws.amazon.com/wellarchitected/latest/operational-readiness-reviews/the-orr-tool.html)

### AWS Prescriptive Guidance

- [Lambda Event Filtering + Partial Batch Response Best Practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/lambda-event-filtering-partial-batch-responses-for-sqs/best-practices-partial-batch-responses.html)
- [Cloud Design Pattern - Retry Backoff](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html)
- [Cloud Design Pattern - Circuit Breaker](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/circuit-breaker.html)

### AWS re:Post Knowledge Center

- [Lambda Troubleshoot Invocation Timeouts](https://repost.aws/knowledge-center/lambda-troubleshoot-invocation-timeouts)
- [Lambda Verify Invocation Timeouts](https://repost.aws/knowledge-center/lambda-verify-invocation-timeouts)
- [Lambda VPC Troubleshoot Timeout](https://repost.aws/knowledge-center/lambda-vpc-troubleshoot-timeout)
- [Lambda Function Retry Timeout SDK](https://repost.aws/knowledge-center/lambda-function-retry-timeout-sdk)
- [Lambda Troubleshoot Throttling](https://repost.aws/knowledge-center/lambda-troubleshoot-throttling)
- [Lambda Reserved Concurrency](https://repost.aws/knowledge-center/lambda-reserved-concurrency)
- [Lambda Retrying Valid SQS Messages](https://repost.aws/knowledge-center/lambda-retrying-valid-sqs-messages)
- [Lambda Concurrency Limit Increase](https://repost.aws/knowledge-center/lambda-concurrency-limit-increase)
- [Lambda Function Idempotent](https://repost.aws/knowledge-center/lambda-function-idempotent)

### AWS Incident Response & Automation

- [AWS Incident Response Playbooks (GitHub)](https://github.com/aws-samples/aws-incident-response-playbooks)
- [AWS Customer Playbook Framework (GitHub)](https://github.com/aws-samples/aws-customer-playbook-framework)
- [AWS Health EventBridge Schema](https://docs.aws.amazon.com/health/latest/ug/aws-health-events-eventbridge-schema.html)
- [SSM Automation Runbooks - Lambda](https://docs.aws.amazon.com/systems-manager-automation-runbooks/latest/userguide/automation-ref-lam.html)
- [AWSSupport-TroubleshootLambdaInternetAccess](https://docs.aws.amazon.com/systems-manager-automation-runbooks/latest/userguide/AWSSupport-TroubleshootLambdaInternetAccess.html)
