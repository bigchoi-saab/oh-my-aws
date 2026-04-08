# 승인 게이트 프로토콜

모든 조치(Act)와 롤백(Rollback)에 적용되는 리스크 기반 승인 체계.

## LOW Risk (자동 실행)
```
조치: 로그 쿼리, 메트릭 수집, 대시보드 링크, 타임라인 기록, 증거 수집
행동: 자동 실행 → 결과 알림
사용자 개입: 불필요
```

## MEDIUM Risk (확인 후 실행)
```
조치: Lambda timeout/memory 변경, DynamoDB 용량 조정, CloudFront 캐시 무효화, ECS 태스크 수 조정
행동: 조치 계획 제시 → 사용자 확인 → 실행
제시 형식:
  "조치: {action_name}
   명령어: {command}
   예상 영향: {estimated_impact}
   롤백: {rollback_command}
   실행할까요? (Y/N)"
```

## HIGH Risk (명시적 승인)
```
조치: 배포 롤백, 트래픽 이동(Zonal Shift), IAM 자격증명 비활성화, Reserved Concurrency 변경, VPC 라우트/SG 변경
행동: 상세 분석 보고 → 영향 범위 + 증거 + 롤백 계획 → 명시적 승인
제시 형식:
  "⚠️ HIGH RISK 조치 승인 요청

   조치: {action_name}
   근거: {evidence 요약}
   명령어: {command}
   영향 범위: {blast_radius}
   예상 비용: {cost_impact}
   롤백 계획: {rollback_command}
   예상 소요: {duration}

   이 조치를 승인하시겠습니까? (Y/N)"
```

## 롤백도 동일 기준 적용
Verify 실패 시 롤백 판단도 같은 리스크 기준을 따른다:
- LOW risk 조치의 롤백 → 자동 실행
- MEDIUM risk 조치의 롤백 → 롤백 제안 + 사용자 확인
- HIGH risk 조치의 롤백 → 상황 보고만, 사용자가 판단
