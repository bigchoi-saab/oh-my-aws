# Scope Lock Protocol

## 원칙
인시던트 대응 중에는 현재 시나리오의 완화/검증/보고에만 집중한다.
범위 밖 발견사항은 기록만 하고 현재 파이프라인을 중단하지 않는다.

## Known Gaps 파일
인시던트 디렉토리에 `known-gaps.yaml`을 유지한다.

## Known Gaps 스키마
```yaml
gaps:
  - id: string        # gap-001, gap-002, ...
    discovered_at: ISO8601
    discovered_by: string   # agent명
    phase: string           # 어떤 phase에서 발견
    category: enum [other-incident, improvement, security, monitoring, architecture]
    description: string
    priority: enum [urgent, normal, low]
    related_resource: string  # 선택
```

## 기록 규칙
- 현재 시나리오와 직접 관련 없는 문제를 발견하면 known-gaps.yaml에 추가
- 기록 후 즉시 현재 작업으로 복귀
- 사용자에게 "범위 밖 문제를 발견했으나 known-gaps에 기록했습니다" 알림

## Urgent Gap 처리
- priority가 urgent인 gap (예: 비인가 변경, 보안 위협)은 기록 즉시 사용자에게 알림
- 단, 현재 파이프라인은 중단하지 않는다. 알림만 제공.

## 예시 상황
- Lambda throttle 대응 중 RDS slow query 발견 → known-gaps에 기록 (normal)
- 인시던트 조사 중 IAM 과잉 권한 발견 → known-gaps에 기록 (normal)
- CloudTrail에서 비인가 변경 발견 → urgent로 기록 + 사용자에게 즉시 알림

## 최종 보고에 포함
audit-report.yaml의 follow_ups에 known-gaps 항목을 포함한다.
팀장은 Reporter 생성 시 known-gaps.yaml 경로를 추가로 전달한다 (파일이 존재할 때만).
