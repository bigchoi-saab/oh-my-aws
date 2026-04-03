# AWS Incident Response - Tasks

## Phase 1 Tasks (MVP)

### Foundation

- [ ] SKILL.md golden source 작성 + Kiro derivation 검증
  - 트리거 조건, 시나리오 레지스트리, DKR 스키마, 가드레일 참조 포함
  - `.kiro/skills/aws-incident-response/SKILL.md` 로 Kiro가 읽는 버전 생성

### DKR (Decision Knowledge Records)

- [ ] `lambda-timeout.yaml` DKR 작성
  - symptoms, diagnosis decision tree, root_causes, remediation actions (CLI + CDK)
  - guardrails (pre/post checks), verification checks, escalation criteria
  - 경로: `.kiro/skills/aws-incident-response/scenarios/lambda-timeout.yaml`

- [ ] `lambda-throttle.yaml` DKR 작성
  - Reserved Concurrency, Provisioned Concurrency, Account limit 분기
  - 경로: `.kiro/skills/aws-incident-response/scenarios/lambda-throttle.yaml`

### References

- [x] `guardrails.yaml` — 3-tier 승인 게이트 시스템
  - 경로: `.kiro/skills/aws-incident-response/references/guardrails.yaml`

- [x] `log-source-map.md` — 서비스별 로그 소스 및 CloudWatch Insights 쿼리
  - 경로: `.kiro/skills/aws-incident-response/references/log-source-map.md`

### Kiro Specs (this directory)

- [x] `requirements.md` — 20개 시나리오 Phase 매핑 및 NFR
- [x] `design.md` — 파이프라인 아키텍처 + DKR 스키마 + Kiro 2-layer 구조
- [x] `tasks.md` — Phase 1 태스크 체크리스트 (이 파일)

### Agent Configuration

- [ ] Agent JSON configuration 작성
  - Kiro agent 설정: skill 연결, MCP tool 매핑, autoApprove 패턴
  - 경로: `.kiro/agents/aws-incident-response.json`

## Phase 2 Tasks (확장)

- [ ] `lambda-cold-start.yaml` DKR
- [ ] `ecs-crash-loop.yaml` DKR
- [ ] `ec2-unreachable.yaml` DKR
- [ ] `rds-perf-degradation.yaml` DKR
- [ ] `rds-failover.yaml` DKR
- [ ] `dynamodb-throttle.yaml` DKR
- [ ] `vpc-unreachable.yaml` DKR
- [ ] `s3-access-denied.yaml` DKR
- [ ] `cloudfront-issue.yaml` DKR
- [ ] `post-deploy-5xx.yaml` DKR

## Phase 4 Tasks (완성)

- [ ] `cert-expiry.yaml` DKR
- [ ] `az-failure.yaml` DKR
- [ ] `region-outage.yaml` DKR
- [ ] `control-plane-failure.yaml` DKR
- [ ] `cascade-failure.yaml` DKR
- [ ] `iam-compromise.yaml` DKR
- [ ] `s3-public-exposure.yaml` DKR
- [ ] `network-unauthorized.yaml` DKR
