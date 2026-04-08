# AWS Incident Response Agent - Implementation Guide

## 1. 구현 우선순위 로드맵

### Phase 1: Skill + DKR 시나리오 (즉시 사용 가능)
- [x] SKILL.md 메인 지시 파일
- [x] scenario-registry.yaml 레지스트리
- [ ] Lambda 타임아웃/쓰로틀링 DKR (docs/research/05에 이미 정규화됨 → YAML 변환)
- [ ] RDS 성능 저하 DKR
- [ ] 배포 후 5xx DKR
- [ ] ECS 크래시 루프 DKR

### Phase 2: Agent 분리 (Multi-Agent)
- [ ] `aws-incident-commander.md` - IC 역할, 오케스트레이션
- [ ] `aws-incident-diagnostician.md` - 진단 전문 (로그/메트릭 쿼리)
- [ ] `aws-incident-executor.md` - 완화 실행 (승인 게이트 포함)

### Phase 3: 도구 계층 (MCP Server 또는 Bash 래퍼)
- [ ] CloudWatch Logs Insights 쿼리 도구
- [ ] CloudWatch Metrics 조회 도구
- [ ] CloudTrail 최근 변경 조회 도구
- [ ] AWS Health 상태 조회 도구
- [ ] 리소스 토폴로지 조회 도구
- [ ] 완화 조치 실행 도구 (승인 게이트)

### Phase 4: UX 통합 (Slash Command)
- [ ] `/aws-incident` 명령어 등록
- [ ] 자동 감지 모드 (`--auto`)
- [ ] 인터랙티브 진단 모드 (`--diagnose`)

## 2. 핵심 설계 결정

### 2.1 승인 게이트 (Human-in-the-Loop)

```
위험도에 따른 자동화 수준:

LOW risk (자동 실행 + 알림):
  - 로그/메트릭 수집, 진단 쿼리 실행
  - CloudWatch 대시보드 링크 생성
  - 타임라인 기록

MEDIUM risk (제안 + 승인 후 실행):
  - Lambda 타임아웃/메모리 설정 변경
  - DynamoDB 용량 조정
  - CloudFront 캐시 무효화

HIGH risk (분석 결과 제시 + 명시적 승인):
  - 배포 롤백
  - 트래픽 우회 (Zonal Shift, Route 53)
  - IAM 자격증명 비활성화
  - Reserved Concurrency 변경
```

### 2.2 가드레일 체계

모든 조치 실행 전 반드시 확인:
1. **사전 조건 (Pre-condition)**: 메트릭 근거 존재하는가?
2. **비용 영향**: 비용 변경이 있다면 사용자에게 표시했는가?
3. **가역성 확인**: 롤백 명령이 준비되어 있는가?
4. **영향 범위**: 다른 리소스에 영향을 주는가?

조치 실행 후 반드시 확인:
1. **효과 검증**: 5분간 메트릭 모니터링
2. **부작용 감지**: Errors가 증가하지 않았는가?
3. **자동 롤백**: 악화 시 이전 설정으로 복원

### 2.3 DKR 파일 작성 규칙

1. 모든 진단 단계에 **구체적 CLI/API 명령어** 포함
2. 모든 조치에 **롤백 명령어** 포함
3. 모든 검증에 **CloudWatch 쿼리 또는 메트릭** 포함
4. **source_refs**: AWS 공식 문서 URL 필수 (저작권 안전)
5. **probability**: 실제 발생 빈도 기반 (high/medium/low)

### 2.4 모델 전략 (참고: OpsWorker 사례)

| 작업 | 적합 모델 | 이유 |
|------|-----------|------|
| 복잡한 RCA/추론 | Claude Opus/Sonnet | 깊은 분석 필요 |
| 빠른 메트릭 추출 | Claude Haiku | 저지연 반복 호출 |
| 인터랙티브 채팅 | Claude Haiku/Sonnet | 응답 속도 |
| 다중 시나리오 병렬 진단 | Agent 병렬 실행 | 처리량 |

## 3. 기존 리서치 활용 매핑

| 리서치 문서 | → 구현 산출물 |
|-------------|--------------|
| 05-decision-knowledge-base.md §2 (Lambda 증상) | → scenarios/lambda-timeout.yaml triggers/symptoms |
| 05-decision-knowledge-base.md §2.3 (진단 트리) | → scenarios/lambda-timeout.yaml diagnosis |
| 05-decision-knowledge-base.md §2.5 (조치 액션) | → scenarios/lambda-timeout.yaml remediation |
| 05-decision-knowledge-base.md §2.6 (가드레일) | → scenarios/lambda-timeout.yaml guardrails |
| 05-decision-knowledge-base.md §2.7 (검증) | → scenarios/lambda-timeout.yaml verification |
| 05-decision-knowledge-base.md §3 (DKR 스키마) | → 모든 시나리오 파일의 구조 |
| 06-aws-incident-log-reference.md | → references/log-source-map.md |
| 07-human-incident-response-scenarios.md | → 시나리오별 운영자 대응 절차 참조 |
| 07-human-incident-operations-playbook.md | → Agent 골든 타임라인, 커뮤니케이션 템플릿 |
| _research/aws-customer-playbook-framework/ | → 보안 시나리오 DKR 참조 |
| _research/aws-incident-response-playbooks/ | → NIST 기반 IR 프로세스 참조 |

## 4. 테스트 전략

### Dry-Run 모드
모든 조치를 `--dry-run` 모드로 먼저 실행하여 부작용 없이 검증

### Game Day 시나리오
1. Lambda 쓰로틀링 시뮬레이션 → Agent가 진단 + 완화 제안
2. 배포 롤백 시나리오 → Agent가 상관관계 탐지 + 롤백 제안
3. VPC 연결 장애 → Agent가 계층별 진단 실행

### 성공 기준
- 진단 정확도: 90% 이상 (근본 원인 정확 식별)
- 초동 조치 시간: 5분 이내 (첫 완화 조치 제안)
- 가드레일 준수: 100% (승인 없는 위험 조치 차단)
