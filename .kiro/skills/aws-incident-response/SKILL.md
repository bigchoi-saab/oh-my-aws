---
name: aws-incident-response
description: AWS 장애 대응 도메인 지식. 시나리오 라우팅, DKR 스키마, 관측 신호 맵, 운영자 모델을 정의한다. 실행은 aws-team-leader가 agent를 통해 조율한다.
version: 0.2.0
category: Operations
tags: [aws, incident-response, sre, devops, operations, lambda, rds, ecs, vpc, cloudfront, dynamodb]
prerequisites: [AWS CLI configured, CloudWatch access, appropriate IAM permissions]
allowed-tools: [Read, Grep, Glob]
note: "이 skill은 aws-team-leader를 통해서만 사용됨. 직접 실행하지 않고 도메인 지식 참조용."
---

# AWS Incident Response Agent Skill

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

## 4. Scenario Registry (지원 장애 유형)

### 4.1 Compute
| ID | 시나리오 | 심각도 | 자동 조치 가능 |
|----|----------|--------|---------------|
| `lambda-timeout` | Lambda 타임아웃 | HIGH | O (설정 변경) |
| `lambda-throttle` | Lambda 동시성 쓰로틀링 | HIGH | O (동시성 조정) |
| `lambda-cold-start` | Lambda 콜드 스타트 지연 | MEDIUM | O (PC/SnapStart) |
| `ecs-crash-loop` | ECS 태스크 반복 실패 | CRITICAL | O (롤백) |
| `ec2-unreachable` | EC2 인스턴스 응답 불가 | HIGH | 부분적 |

### 4.2 Database
| ID | 시나리오 | 심각도 | 자동 조치 가능 |
|----|----------|--------|---------------|
| `rds-perf-degradation` | RDS 성능 저하 | HIGH | 부분적 |
| `rds-failover` | RDS Multi-AZ 페일오버 | CRITICAL | 모니터링 |
| `dynamodb-throttle` | DynamoDB 쓰로틀링 | HIGH | O (용량 조정) |

### 4.3 Network
| ID | 시나리오 | 심각도 | 자동 조치 가능 |
|----|----------|--------|---------------|
| `vpc-unreachable` | VPC 연결 불가 | CRITICAL | 부분적 |
| `s3-access-denied` | S3 403 Forbidden | MEDIUM | 진단 |
| `cloudfront-issue` | CloudFront 캐시/5xx 문제 | MEDIUM | O (무효화) |

### 4.4 Deployment
| ID | 시나리오 | 심각도 | 자동 조치 가능 |
|----|----------|--------|---------------|
| `post-deploy-5xx` | 배포 후 5xx 에러 급증 | CRITICAL | O (롤백) |
| `cert-expiry` | 인증서/자격증명 만료 | HIGH | 부분적 |

### 4.5 Platform
| ID | 시나리오 | 심각도 | 자동 조치 가능 |
|----|----------|--------|---------------|
| `az-failure` | AZ 수준 장애 | CRITICAL | O (Zonal Shift) |
| `region-outage` | 리전 전체 장애 | CRITICAL | 부분적 (DR) |
| `control-plane-failure` | 제어 평면 장애 | HIGH | 정적 안정성 |
| `cascade-failure` | 연쇄 실패 / 재시도 폭풍 | CRITICAL | O (서킷브레이커) |

### 4.6 Security
| ID | 시나리오 | 심각도 | 자동 조치 가능 |
|----|----------|--------|---------------|
| `iam-compromise` | IAM 자격증명 유출 | CRITICAL | O (비활성화) |
| `s3-public-exposure` | S3 버킷 공개 노출 | HIGH | O (차단) |
| `network-unauthorized` | 비인가 네트워크 변경 | HIGH | 진단 |

## 5. Decision Knowledge Record (DKR) Schema

각 시나리오는 다음 구조로 정규화된다:

```yaml
schema: decision-knowledge-record/v1
metadata:     # id, name, category, service, severity, tags, source_refs
triggers:     # alarm, metric_threshold, log_pattern, event_bridge
symptoms:     # 감지 방법, CloudWatch 쿼리, API 호출
diagnosis:    # decision_tree (step → question → check → branches)
root_causes:  # code, name, probability, related_symptoms
remediation:  # actions (aws_cli, cdk, ssm_automation), rollback, risk, approval
guardrails:   # pre_conditions (block/warn), post_conditions (auto_rollback)
verification: # checks, stability_window, success_criteria
escalation:   # auto_remediate, approval_required, timeout, notify
```

DKR 스키마 전체: `docs/research/05-decision-knowledge-base.md` 섹션 3
Lambda 시나리오 정규화 예시: 같은 문서 섹션 4

## 6. Observability Signal Map

장애 조사에 필요한 5가지 관측 영역:

| 영역 | 역할 | 서비스 |
|------|------|--------|
| **Logs** | 이벤트/에러 기록 | CloudWatch Logs, S3 Access Logs, VPC Flow Logs, CloudTrail |
| **Metrics** | 시계열 수치 | CloudWatch Metrics, Container Insights |
| **Traces** | 분산 요청 추적 | AWS X-Ray |
| **Events** | 제어면 변경/상태 | CloudTrail, EventBridge, AWS Health |
| **Topology** | 리소스 의존관계 | Reachability Analyzer, X-Ray Service Map |

핵심: CloudWatch Logs에 없는 로그들 (S3에 저장):
- ALB/NLB Access Logs, CloudFront Logs, S3 Server Access Logs, CloudTrail Events

상세 로그 맵: `docs/research/06-aws-incident-log-reference.md`

## 7. Human Operator Model (Agent가 모방할 대상)

### 7.1 Golden Timeline
```
Phase A (T+0~5분):  감지 → 선언 → 변경 동결 → 인시던트 레코드 생성
Phase B (T+5~15분): Blast Radius 측정 → 심각도 확정 → 역할 배정
Phase C (T+15~45분): 가역적 완화 실행 (롤백 > 트래픽 우회 > Feature Flag > Rate Limit)
Phase D (T+45분~):  지속 복구 확인 → 가드 모드 유지 → 예비 RCA
Phase E (종료):     해결 메시지 → 포스트모템 예약 → 후속 조치 생성
```

### 7.2 Incident Command Roles
- **IC (Incident Commander)**: 총괄, 의사결정, 에스컬레이션
- **Ops Lead**: 기술 조사, 완화/복구 실행
- **Comms Lead**: 내부/외부 커뮤니케이션
- **Scribe**: 타임라인 기록, 증거 보존
- **SME**: 서비스별 전문 지식

### 7.3 Agent가 대체/보조할 수 있는 영역
| 역할 | Agent 대체 가능 | 근거 |
|------|----------------|------|
| 증상 수집/분류 | **대체** | 로그/메트릭 쿼리 자동화 |
| Blast Radius 측정 | **대체** | 토폴로지 + 메트릭 상관분석 |
| 최근 변경 추적 | **대체** | CloudTrail + 배포 이력 자동 조회 |
| 원인 진단 | **보조** | Decision Tree 기반 가설-검증 |
| 완화 조치 실행 | **보조** (승인 필요) | CLI/API 실행, 인간 승인 게이트 |
| 커뮤니케이션 | **보조** | 템플릿 기반 상태 메시지 생성 |
| 타임라인 기록 | **대체** | 자동 기록 |
| 포스트모템 초안 | **보조** | 타임라인 + 결정사항 기반 초안 |

## 8. Anti-Patterns (Agent가 피해야 할 것)

| 금지 행동 | 이유 |
|-----------|------|
| 완화 전 원인 파악 집착 | 고객 영향 시간 증가 |
| 여러 변경 동시 적용 | 효과 구분 불가 |
| 제어 평면 과다 호출 | 장애 악화 가능 |
| 재시작 전 로그 미확보 | 증거 소멸 |
| 장애 중 비가역적 조치 | 2차 장애 위험 |
| AWS Support 연락 지연 | 플랫폼 이슈시 시간 낭비 |

## 9. Scenario Routing (증상 → 시나리오 매칭)

사용자 입력에서 키워드/증상을 추출하여 적절한 DKR 시나리오를 자동 선택한다.

### 라우팅 테이블

| 입력 키워드/증상 | 매칭 시나리오 ID | DKR 파일 | 우선순위 |
|-----------------|-----------------|---------|---------|
| "Task timed out", "Lambda timeout", "Duration 급증" | `lambda-timeout-cold-start` | `lambda-timeout.yaml` | 1 |
| "429", "TooManyRequests", "Throttles", "동시성" | `lambda-throttle-concurrency-exhaustion` | `lambda-throttle.yaml` | 1 |
| "SQS 메시지 누적", "DLQ 증가", "포이즌 필", "재시도 폭주" | `lambda-sqs-poison-pill-retry-storm` | `lambda-sqs-poison-pill.yaml` | 1 |
| "콜드 스타트", "Init Duration", "cold start" | `lambda-timeout-cold-start` | `lambda-timeout.yaml` | 2 |
| "unable to start tasks", "exit 137", "OOM", "ECS 크래시" | `ecs-crash-loop` | `ecs-crash-loop.yaml` | 1 |
| "EC2 응답 없음", "Status Check Failed", "SSH 불가" | `ec2-unreachable` | — (Phase 4) | 2 |
| "RDS CPU", "쿼리 느림", "DatabaseConnections", "SlowQuery" | `rds-perf-degradation` | `rds-perf-degradation.yaml` | 1 |
| "RDS 페일오버", "Multi-AZ failover", "DB 연결 끊김" | `rds-failover` | `rds-failover.yaml` | 1 |
| "ProvisionedThroughput", "DynamoDB 쓰로틀", "WCU/RCU" | `dynamodb-throttle` | `dynamodb-throttle.yaml` | 1 |
| "Connection timed out", "Connection refused", "VPC", "SG 차단" | `vpc-unreachable` | `vpc-unreachable.yaml` | 1 |
| "S3 403", "Access Denied", "버킷 접근" | `s3-access-denied` | — (Phase 4) | 2 |
| "CloudFront 5xx", "캐시 문제", "Origin 에러" | `cloudfront-issue` | — (Phase 4) | 2 |
| "배포 후", "5xx 급증", "deploy 실패", "롤백" | `post-deploy-5xx` | `post-deploy-5xx.yaml` | 1 |
| "인증서 만료", "TLS 에러", "certificate expired" | `cert-expiry` | `cert-expiry.yaml` | 2 |
| "AZ 장애", "특정 AZ", "Zonal Shift" | `az-failure` | `az-failure.yaml` | 1 |
| "리전 장애", "Region outage", "AWS 전체 장애" | `region-outage` | `region-outage.yaml` | 1 |
| "제어 평면", "API 실패", "배포 불가" | `control-plane-failure` | — (Phase 4) | 2 |
| "연쇄 실패", "재시도 폭풍", "cascade", "모든 서비스 느림" | `cascade-failure` | `cascade-failure.yaml` | 1 |
| "IAM 유출", "credential compromise", "GuardDuty" | `iam-compromise` | `iam-compromise.yaml` | 1 |
| "S3 공개", "public access", "버킷 노출" | `s3-public-exposure` | — (Phase 4) | 2 |
| "비인가 네트워크", "SG 변경", "unauthorized" | `network-unauthorized` | — (Phase 4) | 2 |

### 라우팅 로직

```
1. 사용자 입력에서 키워드 추출
2. 라우팅 테이블에서 매칭되는 시나리오 ID 선택
3. 복수 매칭 시: 우선순위 1 > 2, 동일 우선순위면 심각도 높은 것 우선
4. 매칭 실패 시: 사용자에게 증상 추가 설명 요청
5. 선택된 시나리오의 DKR YAML 로드 → 파이프라인 실행
```

## 10. Pipeline Execution

파이프라인 실행은 `aws-team-leader`가 전문 agent(Diagnostician, Executor, Reporter)를 통해 조율한다.
이 문서는 도메인 지식 참조용이며, 직접 실행 지시를 포함하지 않는다.

파이프라인 구조 및 agent 배정은 `.kiro/skills/aws-team-leader/SKILL.md`를 참조.

## 11. Reference Documents

| 문서 | 위치 | 내용 |
|------|------|------|
| CDK + AI Agent 인프라 | `docs/research/01-aws-cdk-ai-agent-infra.md` | CDK 기반 인프라 관리 |
| Skill Best Practice | `docs/research/02-ai-agent-cdk-skill-best-practices.md` | Skill 시스템 설계 |
| AI Agent 사례 연구 | `docs/research/03-aws-incident-ai-agent-case-studies.md` | 글로벌 사례 |
| CDK 인프라 패턴 | `docs/research/04-cdk-infra-management-cases.md` | CDK 패턴 |
| Decision Knowledge Base | `docs/research/05-decision-knowledge-base.md` | DKR 스키마 + Lambda 정규화 |
| 로그/관측 참조 | `docs/research/06-aws-incident-log-reference.md` | 로그 룩업 테이블 |
| 운영자 시나리오 | `docs/research/07-aws-human-incident-response-scenarios.md` | 시나리오별 인간 대응 |
| 운영 플레이북 | `docs/research/07-human-aws-incident-operations-playbook.md` | 골든 타임라인 |
| AWS 보안 플레이북 | `_research/aws-customer-playbook-framework/` | 보안 인시던트 대응 |
| AWS IR 플레이북 | `_research/aws-incident-response-playbooks/` | NIST 기반 IR 템플릿 |
