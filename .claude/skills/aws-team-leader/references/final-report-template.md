# 최종 보고

모든 파이프라인이 완료되면 사용자에게 최종 보고한다.

```
## 인시던트 보고

| 항목 | 내용 |
|------|------|
| 시나리오 | {scenario_name} |
| 심각도 | {severity} |
| Root Cause | {root_cause_name} ({root_cause_code}) |
| 조치 | {actions 요약} |
| 검증 결과 | {overall_result} |
| 소요 시간 | {duration} |
| CDK 반영 | {반영 여부} |

### 산출물
`.ops/incidents/{incident_id}/` 디렉토리에 저장됨:
- observe.yaml — 관측 결과
- diagnosis.yaml — 진단 결과
- execution.yaml — 조치 기록
- verification.yaml — 검증 결과
- audit-report.yaml — 감사 보고서

### 후속 조치
{follow_ups 목록}
```
