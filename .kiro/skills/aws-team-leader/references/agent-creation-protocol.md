# Agent 생성 프로토콜

Agent tool을 사용하여 전문 agent를 생성한다. 각 agent에게 다음 정보를 프롬프트로 전달해야 한다.

## 공통 전달 항목
- agent 정의 파일 경로 (`.claude/agents/aws-{role}.md`)
- handoff-schemas.yaml 경로
- 인시던트 디렉토리 경로

## Agent별 추가 전달 항목

**Diagnostician 생성 시:**
```
- DKR 시나리오 YAML 파일 경로
- guardrails.yaml 경로
- log-source-map.md 경로
- 사용자가 보고한 증상 원문
```

**Executor 생성 시:**
```
- DKR 시나리오 YAML 파일 경로
- guardrails.yaml 경로
- diagnosis.yaml 경로 (Diagnostician 산출물)
- 팀장이 승인한 actions 목록
```

**Reporter 생성 시:**
```
- 인시던트 디렉토리 경로 (모든 YAML 파일을 읽도록)
- message-templates.md 경로
- 보고서 유형: "incident" 또는 "cdk"
- known-gaps.yaml 경로 (파일이 존재할 때만 전달. Reporter는 known-gaps 내용을 최종 보고의 follow_ups 섹션에 포함)
```

**CDK Analyzer 생성 시:**
```
- aws-cdk-operations SKILL.md 경로
- audit-report.yaml 경로
- 프로젝트 CDK 코드 경로 (cdk.json 위치 기준으로 탐색하여 전달)
```

**CDK Engineer 생성 시:**
```
- aws-cdk-operations SKILL.md 경로
- cdk-analysis.yaml 경로
- 인시던트 디렉토리 경로
```

## Agent 프롬프트 템플릿

Agent tool 호출 시 다음 구조로 프롬프트를 작성한다:

```
당신은 AWS {역할} agent입니다.

## 지시 사항
먼저 다음 파일을 읽고 지시에 따라 행동하세요:
- Agent 정의: {agent .md 경로}
- 핸드오프 스키마: {handoff-schemas.yaml 경로}

## 작업 컨텍스트
- 인시던트 ID: {incident_id}
- 시나리오: {scenario_id}
- DKR 파일: {dkr 경로}
- Guardrails: {guardrails 경로}
- 작업 디렉토리: {인시던트 디렉토리 경로}
{이전 단계 산출물 경로들}

## 사용자 보고 증상
{사용자 원문}

## 산출물
작업 완료 후 {산출물 파일명}을 작업 디렉토리에 저장하세요.
```

## 토큰 규율

Agent 프롬프트 작성 및 산출물 처리 시 다음 규칙을 준수한다:
1. **최소 context 전달**: agent에게 현재 작업에 필요한 파일 경로와 정보만 전달. 불필요한 배경 설명 금지.
2. **산출물 요약 우선**: 이전 단계 산출물(YAML)을 agent에게 전달할 때, 전체를 복사하지 말고 필요한 필드만 언급.
3. **에러 출력 잘라내기**: AWS CLI 에러 출력은 처음 20줄만 agent에게 전달.
4. **반복 금지**: 이전 대화에서 이미 전달한 정보를 agent 프롬프트에 다시 포함하지 않는다.

**Infra Analyzer 생성 시:**
```
- aws-cdk-infra SKILL.md 경로
- handoff-schemas.yaml 경로
- infra-request.yaml 경로
- CDK 프로젝트 경로 (cdk.json 위치 기준으로 탐색하여 전달)
```

**CDK Engineer (infra-mode) 생성 시:**
```
- aws-cdk-infra SKILL.md 경로 (aws-cdk-operations 대신)
- handoff-schemas.yaml 경로
- infra-plan.yaml 경로 (cdk-analysis.yaml 대신)
- 요청 디렉토리 경로
```

## Foreground Agent 규칙

모든 Agent는 foreground에서 생성한다 (Agent tool 기본 동작).

**이유:** 인시던트 대응 중 agent가 사용자 승인을 요청해야 하는 상황이 빈번하다. Background agent는 사용자 프롬프트를 받을 수 없으므로, 승인 게이트가 작동하지 않는다.

**예외 없음:** Diagnostician (관측 전용)이라도 guardrails pre_conditions 검증에서 사용자 확인이 필요할 수 있으므로, 모든 agent는 foreground로 실행한다.
