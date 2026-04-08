# 실행 흐름 (Incident Pipeline)

## Step 1: Diagnostician 배정 (Observe + Reason)

Agent tool로 Diagnostician을 생성한다.

```
대기: observe.yaml + diagnosis.yaml 생성 완료
```

Diagnostician이 반환되면 diagnosis.yaml을 읽어 결과를 확인한다.

## Step 2: 승인 게이트

diagnosis.yaml의 `risk_level`과 `recommended_actions`를 확인하고, `references/approval-gate.md`의 승인 게이트 프로토콜을 적용한다.

- **LOW risk** → Step 3으로 자동 진행. 사용자에게 진단 결과와 조치 계획을 알린다.
- **MEDIUM risk** → 사용자에게 진단 결과 + 조치 계획을 제시하고 승인을 요청한다.
- **HIGH risk** → 사용자에게 상세 영향 분석 + 증거 + 롤백 계획을 포함하여 명시적 승인을 요청한다.

승인 거부 시: 대안 조치를 제안하거나 수동 대응 가이드를 제공한다.

## Step 3: Executor 배정 (Act + Verify)

승인된 actions 목록을 포함하여 Executor를 생성한다.

```
대기: execution.yaml + verification.yaml 생성 완료
```

## Step 4: 검증 결과 확인

verification.yaml을 읽어 결과를 확인한다.

- **overall_result: success** → Step 5로 진행
- **overall_result: partial** → 부분 성공 내용을 사용자에게 보고. 추가 조치 여부 질문.
- **overall_result: failed** → `references/error-handling.md` 에러 핸들링으로 분기
- **rollback_triggered: true** → 롤백 결과를 사용자에게 보고. 대안 조치 제안.

## Step 5: Reporter 배정 (Audit)

Reporter를 생성하여 감사 보고서를 작성한다.

```
대기: audit-report.yaml 생성 완료
```

## Step 6: CDK 연계 판단

audit-report.yaml의 `cdk_fix_needed` 필드를 확인한다.

- **cdk_fix_needed: true** → `references/cdk-protocol.md` CDK 연계 프로토콜로 진행
- **cdk_fix_needed: false** → `references/final-report-template.md` 최종 보고로 진행
