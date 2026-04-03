---
name: aws-incident-response
description: >-
  AWS 장애 발생 시 case별 초동 조치를 수행하는 운영 자동화 스킬.
  Observe-Reason-Act-Verify-Audit 파이프라인 기반으로 장애 감지, 진단, 완화, 검증, 기록을 자동화/보조한다.
  20개 장애 시나리오(Lambda 타임아웃, RDS 페일오버, ECS 크래시 루프, VPC 연결 불가, 배포 후 5xx 등)를 커버한다.
  Use when: AWS 환경에서 장애 알림을 받았을 때, CloudWatch 알람이 발생했을 때, 서비스 에러율이 급증했을 때,
  인시던트 대응 절차가 필요할 때, 또는 사용자가 AWS 장애/인시던트/트러블슈팅을 언급할 때.
compatibility: >-
  Requires AWS CLI configured with appropriate credentials,
  CloudWatch Logs/Metrics read access, Lambda management permissions,
  and optionally X-Ray and CloudTrail read access.
allowed-tools: Bash(aws:*) Read Glob
metadata:
  author: oh-my-aws
  version: "0.1.0"
---

# AWS Incident Response Skill

## 1. The Insight

AWS 장애 초동 조치의 핵심은 **"완화가 진단보다 먼저"** 라는 원칙이다. 인간 운영자가 장애 대응 시 가장 많은 시간을 낭비하는 지점은 "원인 파악에 집착하여 완화를 미루는 것"이다. AI Agent는 이 패턴을 역전시켜야 한다:

1. **안정화 우선**: 가역적(reversible) 조치를 10분 내 실행
2. **증거 보존 병행**: 조치하면서 로그/메트릭 스냅샷 확보
3. **진단은 안정화 후**: 완화 효과 확인 후 근본 원인 분석

## 2. Why This Matters

- MTTR(Mean Time To Resolve)의 60-80%가 "진단" 단계에서 소모됨
- 가역적 완화(롤백, 트래픽 우회, 스케일아웃)는 진단 없이도 실행 가능
- AWS DevOps Agent 사례에서 MTTR 75% 감소 달성 (2시간 → 28분)
- Human-in-the-Loop 패턴: AI가 80% 자율 조사 → 인간이 20% 판단/승인

## 3. Core Architecture: Observe-Reason-Act-Verify-Audit

```
[Observe]       [Reason]        [Act]           [Verify]        [Audit]
알람/메트릭/    증상 분류 →     가역적 완화     완화 효과 확인   타임라인 기록
로그/토폴로지   원인 진단 →     실행            메트릭 정상화    결정사항 추적
최근 변경 수집  조치 계획       (승인 필요시    안정성 윈도우    증거 보존
                               인간 확인)      유지 확인        후속 조치 생성
```

## 4. Scenario Registry

DKR 시나리오 파일은 `scenarios/` 디렉토리에 YAML로 정의됩니다.
전체 레지스트리: `references/scenario-registry.yaml`

### Compute
| ID | 시나리오 | 심각도 | DKR |
|----|----------|--------|-----|
| `lambda-timeout-cold-start` | Lambda 콜드 스타트 및 타임아웃 | HIGH | `lambda-timeout.yaml` |
| `lambda-throttle-concurrency-exhaustion` | Lambda 동시성 쓰로틀링 | HIGH | `lambda-throttle.yaml` |
| `lambda-sqs-poison-pill-retry-storm` | SQS 포이즌 필 재시도 폭주 | HIGH | `lambda-sqs-poison-pill.yaml` |
| `ecs-crash-loop` | ECS 태스크 반복 실패 | CRITICAL | `ecs-crash-loop.yaml` |
| `ec2-unreachable` | EC2 인스턴스 응답 불가 | HIGH | Phase 4 |

### Database
| ID | 시나리오 | 심각도 |
|----|----------|--------|
| `rds-perf-degradation` | RDS 성능 저하 | HIGH |
| `rds-failover` | RDS Multi-AZ 페일오버 | CRITICAL |
| `dynamodb-throttle` | DynamoDB 쓰로틀링 | HIGH |

### Network / Storage
| ID | 시나리오 | 심각도 |
|----|----------|--------|
| `vpc-unreachable` | VPC 연결 불가 | CRITICAL |
| `s3-access-denied` | S3 403 Forbidden | MEDIUM |
| `cloudfront-issue` | CloudFront 캐시/5xx 문제 | MEDIUM |

### Deployment
| ID | 시나리오 | 심각도 |
|----|----------|--------|
| `post-deploy-5xx` | 배포 후 5xx 에러 급증 | CRITICAL |
| `cert-expiry` | 인증서/자격증명 만료 | HIGH |

### Platform
| ID | 시나리오 | 심각도 |
|----|----------|--------|
| `az-failure` | AZ 수준 장애 | CRITICAL |
| `region-outage` | 리전 전체 장애 | CRITICAL |
| `control-plane-failure` | 제어 평면 장애 | HIGH |
| `cascade-failure` | 연쇄 실패 / 재시도 폭풍 | CRITICAL |

### Security
| ID | 시나리오 | 심각도 |
|----|----------|--------|
| `iam-compromise` | IAM 자격증명 유출 | CRITICAL |
| `s3-public-exposure` | S3 버킷 공개 노출 | HIGH |
| `network-unauthorized` | 비인가 네트워크 변경 | HIGH |

## 5. Scenario Routing (증상 → 시나리오 매칭)

사용자 입력에서 키워드/증상을 추출하여 적절한 DKR 시나리오를 자동 선택한다.

| 입력 키워드/증상 | 매칭 시나리오 | DKR 파일 |
|-----------------|-------------|---------|
| "Task timed out", "Lambda timeout", "Duration 급증" | `lambda-timeout-cold-start` | `lambda-timeout.yaml` |
| "429", "TooManyRequests", "Throttles", "동시성" | `lambda-throttle-concurrency-exhaustion` | `lambda-throttle.yaml` |
| "SQS 메시지 누적", "DLQ 증가", "포이즌 필" | `lambda-sqs-poison-pill-retry-storm` | `lambda-sqs-poison-pill.yaml` |
| "unable to start tasks", "exit 137", "OOM", "ECS 크래시" | `ecs-crash-loop` | `ecs-crash-loop.yaml` |
| "RDS CPU", "쿼리 느림", "SlowQuery" | `rds-perf-degradation` | `rds-perf-degradation.yaml` |
| "RDS 페일오버", "Multi-AZ failover" | `rds-failover` | `rds-failover.yaml` |
| "DynamoDB 쓰로틀", "WCU/RCU" | `dynamodb-throttle` | `dynamodb-throttle.yaml` |
| "Connection timed out", "VPC", "SG 차단" | `vpc-unreachable` | `vpc-unreachable.yaml` |
| "배포 후 5xx", "deploy 실패", "롤백" | `post-deploy-5xx` | `post-deploy-5xx.yaml` |
| "인증서 만료", "TLS 에러", "certificate expired" | `cert-expiry` | `cert-expiry.yaml` |
| "AZ 장애", "Zonal Shift" | `az-failure` | `az-failure.yaml` |
| "리전 장애", "Region outage", "AWS 전체 장애" | `region-outage` | `region-outage.yaml` |
| "연쇄 실패", "재시도 폭풍", "모든 서비스 느림" | `cascade-failure` | `cascade-failure.yaml` |
| "IAM 유출", "credential compromise" | `iam-compromise` | `iam-compromise.yaml` |

복수 매칭 시 심각도 높은 것 우선. 매칭 실패 시 사용자에게 추가 설명 요청.

## 6. Pipeline Execution Instructions

시나리오가 선택되면 다음 순서로 파이프라인을 실행한다.

### Step 1: Observe (T+0~3분)

1. DKR.triggers의 log_query 실행 → 에러 패턴 확인
2. DKR.triggers의 metrics 조회 → 현재 메트릭 상태 확인
3. 최근 변경 확인: `aws cloudtrail lookup-events`
4. AWS Health 확인: `aws health describe-events`
5. 결과를 사용자에게 요약 제시

### Step 2: Reason (T+3~8분)

1. DKR.symptoms를 현재 관측 데이터와 대조
2. DKR.diagnosis.decision_tree를 순서대로 탐색
3. 매칭된 root_cause 코드를 사용자에게 제시 (확신도 포함)
4. 복수 원인 의심 시 모두 나열하고 가장 유력한 것 표시

### Step 3: Act (T+8~13분)

1. DKR.remediation에서 매칭된 root_cause_code의 actions 로드
2. `references/guardrails.yaml`의 승인 게이트 확인:
   - LOW risk → 자동 실행
   - MEDIUM risk → 제안 + 승인 요청
   - HIGH risk → 분석 + 명시적 승인
3. guardrails.pre_conditions 검증
4. 승인 후 명령어 실행, rollback_command 항상 병기

### Step 4: Verify (T+13~18분)

1. DKR.verification.checks 순서대로 실행
2. expected 결과와 실제 결과 비교
3. stability_window 동안 메트릭 모니터링
4. 모든 check 통과 시 "완화 성공" 보고

### Step 5: Audit (완화 후)

Templates: `audit/timeline-template.md`, `audit/postmortem-template.md`

1. 타임라인 기록: audit/timeline-template.md에 따라 감지~해결 전체 이벤트 기록
2. 증거 보존: 쿼리/명령어/결과 스냅샷, 메트릭 링크
3. 후속 조치 생성: 근본 원인 해결, 런북 업데이트
4. 포스트모템 초안: audit/postmortem-template.md에 따라 생성 (Executive Summary, Impact, Timeline, Root Cause, Action Items)
5. 검토 일정: 48시간(긴급), 2주(구조적), 6주(재발 방지)

## 7. Anti-Patterns

| 금지 행동 | 이유 |
|-----------|------|
| 완화 전 원인 파악 집착 | 고객 영향 시간 증가 |
| 여러 변경 동시 적용 | 효과 구분 불가 |
| 제어 평면 과다 호출 | 장애 악화 가능 |
| 재시작 전 로그 미확보 | 증거 소멸 |
| 장애 중 비가역적 조치 | 2차 장애 위험 |
| AWS Support 연락 지연 | 플랫폼 이슈시 시간 낭비 |

## 8. References

- DKR Schema: `references/scenario-registry.yaml`
- Log Sources: `references/log-source-map.md`
- Guardrails: `references/guardrails.yaml`
- Full Research: `docs/research/05-decision-knowledge-base.md`
