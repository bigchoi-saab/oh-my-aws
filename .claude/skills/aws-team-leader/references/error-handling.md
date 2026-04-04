# 에러 핸들링

## Agent 실패
1. Agent가 에러를 반환하면 1회 재시도한다.
2. 재시도에도 실패하면 사용자에게 상황을 보고한다:
```
"⚠️ {agent_name} agent가 작업을 완료하지 못했습니다.
 원인: {error_summary}
 
 수동 대응 옵션:
 1. {수동 명령어 안내}
 2. 다른 시나리오로 재시도
 3. 에스컬레이션"
```

## Verify 실패 (롤백 판단)
1. verification.yaml에서 `overall_result: failed` 확인
2. 실패한 check 내용을 사용자에게 보고
3. 리스크 기반 롤백 (`references/approval-gate.md` 기준):
   - LOW → 자동 롤백 실행
   - MEDIUM → 롤백 제안 + 확인
   - HIGH → 상황 보고 + 사용자 판단

## 알 수 없는 시나리오
라우팅 테이블에서 매칭되지 않는 경우:
1. 사용자에게 추가 정보 요청
2. 가장 유사한 시나리오 3개를 제시하여 선택 요청
3. 그래도 매칭 불가 시: 수동 조사 모드 안내 (Diagnostician만 배정하여 관측 수집)
