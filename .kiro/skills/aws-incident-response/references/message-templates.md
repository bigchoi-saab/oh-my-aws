# AWS Incident Response - Communication Templates

> Source: docs/research/07-human-aws-incident-operations-playbook.md Section 6

## Update Cadence by Severity

| Severity | Internal | External | Escalation |
|----------|----------|----------|------------|
| **SEV1** | 15분 | 15-30분 | Executive + cross-team 즉시 |
| **SEV2** | 30분 | 30-60분 | Service owners + management |
| **SEV3** | 60분 | Event-based | Team-level |

## Status Labels

모든 업데이트에 다음 라벨 중 하나를 사용:
`Investigating` → `Identified` → `Mitigating` → `Monitoring` → `Resolved`

---

## Template 1: Incident Declaration (내부)

```
[Incident Declared]
Severity: {SEV1|SEV2|SEV3}
Start: {YYYY-MM-DD HH:MM} KST ({HH:MM} UTC)
Impact: {고객이 겪는 구체적 증상 + 영향 비율}
Scope: {리전}, {영향받는 서비스/엔드포인트}
Roles: IC=@{name}, Ops=@{name}, Comms=@{name}, Scribe=@{name}
Current action: {현재 진행 중인 조치}
Next update: {HH:MM} KST
```

### SEV1 Example
```
[Incident Declared]
Severity: SEV1
Start: 2026-04-03 14:05 KST (05:05 UTC)
Impact: Checkout API unavailable for ~35% of traffic
Scope: ap-northeast-2, ap-northeast-1, /payments/authorize
Roles: IC=@kim, Ops=@lee, Comms=@park, Scribe=@choi
Current action: initiating traffic shift to eu-west-1
Next update: 14:20 KST
```

### SEV2 Example
```
[Incident Declared]
Severity: SEV2
Start: 2026-04-03 14:05 KST (05:05 UTC)
Impact: Elevated 5xx on checkout API (~22% failure)
Scope: ap-northeast-2, /payments/authorize
Roles: IC=@kim, Ops=@lee, Comms=@park
Current action: rollback to previous release
Next update: 14:20 KST
```

---

## Template 2: Status Update (내부/외부)

```
[Status Update]
Time: {HH:MM} KST
Status: {Investigating|Identified|Mitigating|Monitoring}
What changed: {마지막 업데이트 이후 변경된 사항}
Current risk: {현재 잔여 위험}
Next actions: {다음에 할 조치}
Next update: {HH:MM} KST
```

### Example
```
[Status Update]
Time: 14:20 KST
Status: Mitigating
What changed: Rollback completed; 5xx reduced from 22% to 4%
Current risk: queue backlog and elevated latency remain
Next actions: retry limit reduction, controlled backlog drain
Next update: 14:35 KST
```

---

## Template 3: Resolved Notice

```
[Resolved]
Resolved at: {HH:MM} KST
Customer impact window: {start}-{end} KST
Summary: {복구 방법 한 줄 요약}
Follow-up: Postmortem scheduled for {date} {time} KST
```

### Example
```
[Resolved]
Resolved at: 15:10 KST
Customer impact window: 14:05-15:02 KST
Summary: Service restored after rollback and retry tuning
Follow-up: Postmortem scheduled for 2026-04-05 10:00 KST
```

---

## Template 4: Executive Brief (SEV1 전용)

```
SEV1 update @ {HH:MM} KST
- Customer impact: {고객 영향 구체적 수치}
- Business impact: {비즈니스 영향 (매출, 전환율 등)}
- Current strategy: {현재 대응 전략}
- Confidence: {low|medium|high} ({근거})
- Next hard decision point: {HH:MM} KST ({조건부 의사결정 내용})
```

### Example
```
SEV1 update @ 14:30 KST
- Customer impact: checkout unavailable for ~35% of traffic in two regions
- Business impact: payment conversion currently down ~18%
- Current strategy: traffic shift + rollback + dependency isolation
- Confidence: medium (restoration trend positive)
- Next hard decision point: 14:45 KST (full feature disable if not <5% errors)
```

---

## Template 5: Incident Handoff (교대 시)

```
[Incident Handoff]
Time: {HH:MM} KST
Severity: {SEV}
Current status: {Status Label}
Impact now: {현재 영향 수치}
What is done: {완료된 조치 목록}
What remains: {남은 작업}
Open risks: {잔여 위험}
Next decision point: {HH:MM} KST
New IC: @{name}
```

### Example
```
[Incident Handoff]
Time: 16:00 KST
Severity: SEV2
Current status: Monitoring
Impact now: <1% 5xx (baseline 0.2%)
What is done: rollback, traffic shift 20%, retry cap 3->1
What remains: backlog drain completion, region re-balance
Open risks: latent timeout spikes under peak load
Next decision point: 16:20 KST
New IC: @park
```

---

## Template 6: External Status Page

```
[시간] 업데이트
■ 현상: {고객이 겪는 구체적 증상}
■ 영향 범위: {영향받는 서비스/리전/사용자 비율}
■ 현재 상태: {조사 중 / 완화 조치 중 / 복구 확인 중}
■ 조치 내용: {구체적으로 하고 있는 작업}
■ 다음 업데이트: {시간}

[해결 시]
■ 해결 확인: {시간}
■ 원인: {검증된 원인 — 추측 금지}
■ 복구 상태: 모니터링 중
■ 사후분석: {예정 일시}에 공유 예정
```

---

## Usage Notes

- **매 업데이트에 "다음 업데이트 시간" 반드시 포함** — 커뮤니케이션 예측 가능성이 신뢰의 핵심
- **추측 금지**: 원인이 확인되지 않았으면 "조사 중"이라고만 적기
- **SEV1은 Executive Brief를 별도로** — 기술 세부사항 없이 비즈니스 영향 중심
- **Handoff는 교대 시 필수** — 컨텍스트 유실이 장애 연장의 주요 원인
