# Triage 프로토콜

사용자가 장애 상황을 보고하면 다음 순서로 처리한다.

## Step 1: 증상 추출
사용자 입력에서 키워드, 서비스명, 에러 메시지, 메트릭 이름을 추출한다.

## Step 2: 시나리오 매칭
`.claude/skills/aws-incident-response/SKILL.md` Section 9의 **라우팅 테이블**을 참조하여 시나리오를 매칭한다.

```
라우팅 로직:
1. 키워드 매칭 → 시나리오 ID 후보 선택
2. 복수 매칭 시: 우선순위 1 > 2, 동일 우선순위면 심각도 높은 것 우선
3. 매칭 실패 시: 사용자에게 추가 정보 요청
```

## Step 3: DKR 경로 결정
매칭된 시나리오 ID로 DKR 파일 경로를 결정한다:
```
.claude/skills/aws-incident-response/references/scenarios/{scenario-id}.yaml
```

## Step 4: 사용자 확인
매칭 결과를 사용자에게 제시하고 확인받는다:
```
"증상: {추출된 키워드}
매칭 시나리오: {시나리오 이름} ({시나리오 ID})
심각도: {severity}

이 시나리오로 진행할까요?"
```

## 인시던트 디렉토리 생성

시나리오가 확정되면 작업 디렉토리를 생성한다.

```bash
mkdir -p .ops/incidents/{YYYY-MM-DDTHH-MM}-{scenario-id}/
```

예시: `.ops/incidents/2026-04-03T14-30-lambda-throttle/`

이 디렉토리에 모든 agent 산출물이 저장된다.
