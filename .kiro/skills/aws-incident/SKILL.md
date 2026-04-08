---
name: aws-incident
description: AWS 장애 대응 슬래시 커맨드. 팀장(aws-team-leader)을 호출하여 인시던트 대응 파이프라인을 실행한다.
version: 0.1.0
category: Operations
tags: [aws, incident-response, command]
allowed-tools: [Read, Grep, Glob, Bash, Write, Agent, AskUserQuestion]
---

# /aws-incident

AWS 장애 대응 커맨드. 사용자의 장애 보고를 받아 **aws-team-leader**를 통해 전체 인시던트 대응 파이프라인을 실행한다.

## 사용법

```
/aws-incident <증상 또는 시나리오 설명>
```

### 예시
```
/aws-incident Lambda 429 에러 발생, Throttles 메트릭 급증
/aws-incident RDS CPU 90% 이상, 쿼리 응답 10초 이상
/aws-incident 배포 후 5xx 에러율 급증
/aws-incident ECS 태스크가 반복적으로 실패
/aws-incident IAM 자격증명 유출 의심, GuardDuty 알림
```

## 실행 흐름

이 커맨드는 다음 순서로 실행된다:

### 1. 팀장 지시 로드
다음 파일을 읽어 팀장의 지시에 따라 행동한다:
- `.claude/skills/aws-team-leader/SKILL.md`

### 2. 도메인 지식 로드
라우팅 테이블과 시나리오 정보를 참조한다:
- `.claude/skills/aws-incident-response/SKILL.md` (Section 9: 라우팅 테이블)

### 3. 팀장 프로토콜 실행
aws-team-leader SKILL.md의 지시를 따라:
1. **Triage** — 사용자 입력에서 키워드 추출 → 시나리오 매칭
2. **Diagnostician 배정** — Observe + Reason
3. **승인 게이트** — 리스크 기반 승인
4. **Executor 배정** — Act + Verify
5. **Reporter 배정** — Audit
6. **CDK 연계** — 필요 시 CDK 파이프라인
7. **최종 보고** — 인시던트 요약 + 산출물 경로

## 산출물

실행 완료 후 다음 디렉토리에 결과가 저장된다:
```
.ops/incidents/{YYYY-MM-DDTHH-MM}-{scenario-id}/
├── observe.yaml
├── diagnosis.yaml
├── execution.yaml
├── verification.yaml
├── audit-report.yaml
├── cdk-analysis.yaml    (CDK 연계 시)
├── cdk-changes.yaml     (CDK 연계 시)
└── cdk-report.yaml      (CDK 연계 시)
```
