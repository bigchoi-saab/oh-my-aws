# Session Checkpoint Protocol

## 체크포인트 파일
인시던트 디렉토리에 `checkpoint.yaml`을 유지한다.

## 스키마
```yaml
incident_id: string
scenario_id: string
current_phase: enum [triage, observe, diagnose, approve, execute, verify, report, cdk-analyze, cdk-engineer, cdk-deploy, cdk-report, infra-triage, infra-plan, infra-create, infra-modify, infra-verify, infra-report, error, rollback, escalation, complete]
completed_artifacts:
  - filename: string
    timestamp: string
last_user_decision: string  # 마지막 승인/거부 내용
next_action: string          # 다음에 해야 할 일 (사람이 읽을 수 있는 설명)
resumed_count: integer       # 세션 재개 횟수
error_context:               # 에러/롤백 시 상세 컨텍스트 (해당 시에만)
  error_type: enum [agent_failure, verify_failure, unknown_scenario]
  failed_action: string
  rollback_in_progress: boolean
  retry_count: integer
```

## 기록 규칙
- 각 phase 완료 시 checkpoint.yaml 업데이트
- 사용자 승인/거부 결정도 기록
- agent 산출물 파일명 + timestamp 기록
- error/rollback/escalation phase 진입 시 error_context 필드 기록
- rollback_in_progress: true인 상태에서 세션 중단 시, 재개 후 롤백 계속 진행

## 재개 규칙
- 인시던트 디렉토리에 checkpoint.yaml이 존재하면 재개 모드
- checkpoint.current_phase 확인 → 해당 단계부터 실행
- current_phase가 error/rollback/escalation이면 error_context를 확인하여 적절한 복구 수행
- rollback_in_progress가 true이면 롤백을 계속 진행 (중복 실행 방지)
- completed_artifacts에 나열된 파일 존재 여부 검증
- 누락된 산출물이 있으면 해당 단계 재실행
- known-gaps.yaml이 존재하면 urgent 항목부터 확인
- 체크포인트가 없으면 기존 동작 그대로 진행 (하위 호환)
