# AWS Incident Response - Requirements

## Overview

AWS 장애 발생 시 Observe-Reason-Act-Verify-Audit 파이프라인으로 초동 조치를 자동화/보조하는 AI Agent Skill.

## User Stories

### Phase 1 (MVP) — Compute Core

- [ ] US-P1-01: Lambda 타임아웃 진단 및 완화 (`lambda-timeout`)
- [ ] US-P1-02: Lambda 쓰로틀링 진단 및 완화 (`lambda-throttle`)

### Phase 2 (확장) — Full Compute + Database

- [ ] US-P2-01: Lambda 콜드 스타트 지연 완화 (`lambda-cold-start`)
- [ ] US-P2-02: ECS 태스크 크래시 루프 진단 및 롤백 (`ecs-crash-loop`)
- [ ] US-P2-03: EC2 인스턴스 응답 불가 진단 (`ec2-unreachable`)
- [ ] US-P2-04: RDS 성능 저하 진단 및 완화 (`rds-perf-degradation`)
- [ ] US-P2-05: RDS Multi-AZ 페일오버 모니터링 (`rds-failover`)
- [ ] US-P2-06: DynamoDB 쓰로틀링 진단 및 용량 조정 (`dynamodb-throttle`)
- [ ] US-P2-07: VPC 연결 불가 진단 (`vpc-unreachable`)
- [ ] US-P2-08: S3 403 Forbidden 진단 (`s3-access-denied`)
- [ ] US-P2-09: CloudFront 캐시/5xx 진단 및 무효화 (`cloudfront-issue`)
- [ ] US-P2-10: 배포 후 5xx 에러 급증 진단 및 롤백 (`post-deploy-5xx`)

### Phase 4 (완성) — Platform + Security

- [ ] US-P4-01: 인증서/자격증명 만료 진단 (`cert-expiry`)
- [ ] US-P4-02: AZ 수준 장애 감지 및 Zonal Shift (`az-failure`)
- [ ] US-P4-03: 리전 전체 장애 DR 전환 보조 (`region-outage`)
- [ ] US-P4-04: 제어 평면 장애 정적 안정성 전환 (`control-plane-failure`)
- [ ] US-P4-05: 연쇄 실패/재시도 폭풍 차단 (`cascade-failure`)
- [ ] US-P4-06: IAM 자격증명 유출 탐지 및 비활성화 (`iam-compromise`)
- [ ] US-P4-07: S3 버킷 공개 노출 탐지 및 차단 (`s3-public-exposure`)
- [ ] US-P4-08: 비인가 네트워크 변경 탐지 (`network-unauthorized`)

## Non-Functional Requirements

- **MTTR 목표**: 초동 완화 10분 내 실행 (진단 없이 가역적 조치)
- **승인 게이트**: MEDIUM/HIGH 조치는 반드시 사용자 승인 후 실행
- **증거 보존**: 모든 조치 전 메트릭/로그 스냅샷 확보
- **롤백 준비**: 모든 MEDIUM/HIGH 조치는 롤백 명령 사전 준비 필수
- **감사 로그**: 모든 조사/조치 결정사항 타임라인 기록
