# Infra Triage 프로토콜

사용자가 인프라 생성/변경을 요청하면 다음 순서로 처리한다.

## Step 1: 요청 유형 분류

사용자 입력에서 요청 유형을 판별한다:
- **create**: "만들어", "생성", "추가", "새로운" 키워드 → 신규 인프라
- **modify**: "변경", "수정", "업데이트", "바꿔" 키워드 → 기존 인프라 변경
- **delete**: "삭제", "제거", "없애" 키워드 → **v2로 이연**

### delete 요청 처리
```
"삭제는 아직 지원하지 않습니다. 데이터 손실 위험이 있어 CDK 코드를 직접 수정해주세요."
```

## Step 2: CDK 프로젝트 확인

프로젝트 내 CDK 코드 위치를 파악한다:
```bash
rg --files -g cdk.json -g '!**/node_modules/**' -g '!**/_research/**' -g '!**/cdk-research/**'
```

**CDK 프로젝트가 없는 경우**:
```
"CDK 프로젝트가 없습니다. 먼저 `cdk init`으로 프로젝트를 생성해주세요.
예: mkdir my-infra && cd my-infra && npx cdk init app --language typescript"
```
→ 파이프라인 중단.

## Step 3: 요청 정보 추출

사용자 입력에서 다음 정보를 추출한다:
- `target_service`: 주요 AWS 서비스 (lambda, ecs, rds, dynamodb, s3, vpc 등)
- `architecture_pattern`: 카탈로그 패턴 (선택, aws-cdk-infra skill 참조)
- `target_environment`: 배포 환경 (기본값: dev)
- `constraints`: 제약 조건 (VPC, 리전 등)
- modify인 경우: `existing_stack`, `existing_construct`

정보가 부족하면 사용자에게 추가 질문:
```
"인프라 요청을 이해했습니다. 몇 가지 확인이 필요합니다:
1. 대상 환경은? (dev/staging/prod, 기본: dev)
2. 기존 VPC를 사용하나요, 새로 만드나요?
3. [modify 시] 어떤 스택/리소스를 변경하나요?"
```

## Step 4: 사용자 확인

요청을 정리하여 사용자에게 제시하고 확인받는다:
```
"인프라 요청 확인:
 유형: {create/modify}
 서비스: {target_service}
 환경: {target_environment}
 설명: {description}

 이 요청으로 진행할까요?"
```

## Step 5: 요청 디렉토리 생성

요청이 확정되면 작업 디렉토리를 생성한다.

```bash
mkdir -p .ops/infra-requests/{YYYY-MM-DDTHH-MM}-{request-summary}/
```

예시: `.ops/infra-requests/2026-04-06T10-30-lambda-api/`

## Step 6: infra-request.yaml 생성

handoff-schemas.yaml의 `infra-request` 스키마에 맞춰 요청 파일을 저장한다.

이후 `references/infra-execution-flow.md`로 진행한다.
