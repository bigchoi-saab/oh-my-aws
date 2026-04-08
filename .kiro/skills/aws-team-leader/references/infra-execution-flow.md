# 실행 흐름 (Infrastructure Pipeline)

## Step 1: Infra Analyzer 배정

Agent tool로 Infra Analyzer를 생성한다.

```
대기: infra-plan.yaml 생성 완료
```

Infra Analyzer가 반환되면 infra-plan.yaml을 읽어 결과를 확인한다.

### 실패 처리
Infra Analyzer가 실패하면 1회 재시도. 재시도에도 실패하면:
```
"⚠️ Infra Analyzer가 요청을 분석하지 못했습니다.
 원인: {error_summary}

 수동 대응 옵션:
 1. 요청을 더 구체적으로 재작성
 2. CDK 코드를 직접 수정"
```

## Step 2: 승인 게이트

infra-plan.yaml의 내용을 사용자에게 제시하고 승인을 요청한다.

### 환경별 리스크 수준
| 환경 | 리스크 | 승인 방식 |
|------|--------|----------|
| dev | MEDIUM | 계획 제시 → 사용자 확인 |
| staging | HIGH | 상세 영향 분석 + 명시적 승인 |
| prod | HIGH | 상세 영향 분석 + 명시적 승인 |

### 승인 요청 형식
```
"인프라 구현 계획:
 대상 스택: {target_stack}
 유형: {request_type}
 [create 시] 생성할 construct: {new_constructs 요약}
 [modify 시] 변경 내용: {planned_changes 요약}
 영향 범위: {impact_assessment}
 환경: {target_environment}

 이 계획으로 CDK 코드를 {생성/수정}할까요? (Y/N)"
```

승인 거부 시: 요청을 수정하거나 파이프라인을 종료한다.

## Step 3: CDK Engineer 배정

승인된 infra-plan.yaml을 포함하여 CDK Engineer를 생성한다.
- infra-mode로 동작 (mode: infra 감지)
- create-mode 또는 modify-mode 자동 분기

```
대기: cdk-changes.yaml (mode: infra) 생성 완료
```

## Step 4: 검증 결과 확인

cdk-changes.yaml을 읽어 결과를 확인한다.

- **deploy_ready: true** → Step 5로 진행
- **deploy_ready: false** → 실패 사유를 사용자에게 보고
  - synth 실패: 에러 내용 제시 + 수정 제안
  - diff에서 예상 외 변경: 변경 내용 제시 + 사용자 판단 요청

## Step 5: Deploy 승인 (항상 HIGH Risk)

cdk-changes.yaml의 diff 결과를 사용자에게 제시한다:
```
"⚠️ CDK Deploy 승인 요청

 cdk diff 결과:
 {cdk_diff_output}

 수정 파일:
 {files_modified}

 이 변경을 배포할까요? (Y/N)
 (N 선택 시 코드 변경은 유지되며, 나중에 수동으로 배포할 수 있습니다)"
```

배포 승인 시: 사용자에게 deploy 명령어를 안내한다.

## Step 6: Reporter 배정 (선택)

사용자가 원하면 Reporter agent를 생성하여 인프라 변경 보고서를 작성한다.
보고서 유형: "infra" (incident와 구분)

```
대기: cdk-report.yaml 생성 완료
```
