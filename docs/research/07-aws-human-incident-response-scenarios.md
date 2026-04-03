# AWS 운영자 장애 대응 시나리오 — Human Operator Best Practice

> 조사일: 2026-04-03
> 목적: AWS 장애 발생 시 인간 운영자(SRE, DevOps, On-Call Engineer)가 실제로 수행하는 업무를 글로벌 Best Practice 기준으로 시나리오별 정리
> 대상: oh-my-aws AI Agent가 "인간 운영자가 어떻게 행동하는가"를 이해하고, 동일한 워크플로우를 자동화·보조하는 기준

---

## 1. 장애 대응 기본 프레임워크

### 1.1 장애 수명주기 (Incident Lifecycle)

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│Detection │──▶│ Triage   │──▶│Diagnosis │──▶│Mitigation│──▶│Resolution│──▶│Post-Mortem│
│  감지     │   │  분류     │   │  원인분석 │   │  완화     │   │  복구     │   │  사후분석  │
└──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
   1-10분         10-30분        20-90분        10-60분       30분~수시간      당일~2주
```

| 단계 | 소요 시간 | 운영자 액션 | 지연 원인 |
|------|----------|------------|----------|
| **Detection (감지)** | 1-10분 | 알림 수신 → Acknowledge | 약한 SLO 알람, 노이즈, 비즈니스 메트릭 누락 |
| **Triage (분류)** | 10-30분 | 영향 범위 파악, 심각도 선언 | 불명확한 blast radius, 충돌하는 대시보드 |
| **Diagnosis (원인분석)** | 20-90분 | 로그/메트릭/추적 조회, 가설 검증 | 다중 서비스 연관, 일시적 신호, 최근 변경사항 파악 어려움 |
| **Mitigation (완화)** | 10-60분 | 트래픽 우회, 장애 격리, 롤백 | 수동 승인, 페일오버 준비 부족, 용량 콜드스타트 |
| **Resolution (복구)** | 30분~수시간 | 정상 상태 복원, 백로그 소화 | 데이터 일관성 검증, 신중한 페일백 |
| **Post-Mortem (사후분석)** | 당일~2주 | 비난 없는 회고, 액션 아이템, 런북 업데이트 | 우선순위 경쟁, 조직적 관성 |

### 1.2 심각도 분류 (Severity Classification)

| 등급 | 정의 | 응답 시간 | 운영자 행동 |
|------|------|----------|------------|
| **SEV1 (Critical)** | 고객 영향 확실, 핵심 기능 마비 | 즉시 응답, 15분 내 워룸 | IC 선임, 전담팀 구성, 경영진/고객 커뮤니케이션 |
| **SEV2 (High)** | 고객 영향 일부, 성능 저하 | 30분 내 응답 | 담당자 중심 조사, 필요시 워룸 |
| **SEV3 (Medium)** | 잠재적 위험, 제한적 영향 | 4시간 내 응답 | 티켓 기반 처리, 정상 업무 병행 |
| **SEV4 (Low)** | 사소한 이슈, 개선 요청 | 24시간 내 응답 | 백로그에 적재 |

### 1.3 역할 분담 (Incident Response Roles)

```
┌─────────────────────────────────────────────────────┐
│                  Incident Commander (IC)             │
│  장애 총괄, 의사결정, 우선순위 지정, 에스컬레이션      │
├──────────┬──────────┬──────────┬──────────┬─────────┤
│ Ops Lead │Comms Lead│  Scribe  │AWS Liaison│Service  │
│기술 조사  │고객/내부  │ 타임라인  │AWS Support│Owner    │
│원인분석   │커뮤니케이션│ 기록     │케이스 관리│서비스별  │
│완화 조치  │상태 페이지│ 결정 추적│기술 지원  │전문가    │
│복구 실행  │업데이트   │ 증거 수집│           │         │
└──────────┴──────────┴──────────┴──────────┴─────────┘
```

| 역할 | 책임 | SEV1 필수 여부 |
|------|------|--------------|
| **Incident Commander (IC)** | 장애 총괄, 의사결정, 에스컬레이션, 자원 배분 | 필수 |
| **Ops Lead** | 기술적 조사, 원인 분석, 완화/복구 실행 | 필수 |
| **Comms Lead** | 내부/외부 커뮤니케이션, 상태 페이지 업데이트 | SEV1 필수 |
| **Scribe** | 타임라인 기록, 결정사항 추적, 증거 보존 | SEV1 권장 |
| **AWS Liaison** | AWS Support 케이스 관리, AWS 기술 지원 요청 | 대규모 장애 시 |
| **Service Owner** | 해당 서비스 전문 지식 제공, 영향 평가 | 필요 시 |

### 1.4 커뮤니케이션 리듬

| 대상 | 주기 | 내용 |
|------|------|------|
| **워룸 내부 (체크포인트)** | SEV1: 15분마다 / SEV2: 30분마다 | 영향 현황, 조치 상태, 차단 요인, 다음 마일스톤 |
| **상태 페이지 (외부)** | 최초 10-15분 내, 이후 20-30분마다 | "무슨 현상인가" + "무엇을 알고 있는가" + "무엇을 하고 있는가" + "다음 업데이트 시간" |
| **이해관계자 (내부)** | 30분마다 또는 주요 진전 시 | 영향 범위, 예상 복구 시간, 비즈니스 영향 |
| **AWS Support** | 진전 시 즉시 | 요청 ID, 영향받는 리소스, 리전/AZ, 고객 영향 메트릭 |

#### 상태 페이지 업데이트 템플릿

```
[시간] 업데이트
■ 현상: [고객이 겪는 구체적 증상]
■ 영향 범위: [영향받는 서비스/리전/사용자 비율]
■ 현재 상태: [조사 중 / 완화 조치 중 / 복구 확인 중]
■ 조치 내용: [구체적으로 하고 있는 작업]
■ 다음 업데이트: [시간]

[해결 시]
■ 해결 확인: [시간]
■ 원인: [검증된 원인 — 추측 금지]
■ 복구 상태: 모니터링 중
■ 사후분석: [예정 일시]에 공유 예정
```

---

## 2. 장애 시나리오별 운영자 대응 절차

### 2.1 데이터 평면 장애 (Data Plane Failure)

**상황**: 서비스가 응답하지만 에러율/지연 급증. 고객 영향 발생.

```
운영자가 실제로 하는 일:

T+0분: 알림 수신
  → PagerDuty/Opsgenie 알림 확인
  → "이게 진짜인가?" — 노이즈인지 실제 장애인지 판단
  → CloudWatch 대시보드, Datadog, Grafana 빠르게 스캔
  → 고객 영향 확인 (에러율, 응답 시간, 트래픽 급감)

T+0-5분: 초기 분류
  → SEV 선언 (고객 영향 확인 시 SEV1/SEV2)
  → Slack 인시던트 채널에 알림
  → IC 선임 (보통 온콜 엔지니어가 겸임, 필요시 에스컬레이션)

T+5-15분: 영향 범위 좁히기
  → 어떤 AZ에 집중되었는가? (CloudWatch Metrics AZ 차원)
  → 어떤 엔드포인트/경로인가?
  → 최근 배포/변경이 있었는가? (CodePipeline, CDK 배포 이력)
  → AWS Health Dashboard 확인 (플랫폼 이슈 여부)

T+15-30분: 트래픽 우회 (완화)
  → 비정상 AZ 트래픽을 정상 AZ로 우회
    · ALB: 비정상 타겟 자동 제거 (Health Check 기반)
    · Route 53: Weighted/Failover 레코드로 정상 리전으로 우회
    · ARC: Zonal Shift 실행
  → 비핵심 기능 비활성화 (Feature Flag로 제어)
  → "안정화 우선, 원인 분석은 나중에"

T+30-60분: 원인 분석
  → 최근 배포와의 상관관계 확인
  → CloudWatch Logs Insights로 에러 패턴 분석
  → X-Ray로 지연 병목 위치 확인
  → 하위 서비스 의존성 상태 확인

T+60분+: 복구 및 정상화
  → 완화 조치 효과 확인 (메트릭 정상화 모니터링)
  → 비활성화했던 기능 순차적 복원
  → 트래픽 비율 점진적으로 원래 상태로
  → 30분간 모니터링 후 "해결" 선언
```

**자동 vs 수동 분리**:

| 작업 | 자동화 가능 | 현재 수동인 이유 |
|------|-----------|----------------|
| AZ 헬스체크 기반 타겟 제거 | ✅ 자동 | ALB Health Check이 자동 처리 |
| ARC Zonal Shift | ✅ 반자동 | 트리거는 자동, 실행은 런북 확인 후 수동이 많음 |
| 비핵심 기능 비활성화 | ⚠️ 반자동 | Feature Flag 존재 시 빠르지만, 어떤 기능을 끌지는 판단 필요 |
| Route 53 페일오버 | ✅ 자동 | Health Check 기반 자동 페일오버 설정 시 |
| 영향 범위 파악 | ⚠️ 반자동 | 대시보드는 있지만, 해석은 인간 판단 필요 |
| 원인 분석 | ❌ 주로 수동 | 다중 서비스 상관, 로그 해석, 가설 검증 필요 |

---

### 2.2 제어 평면 장애 (Control Plane Failure)

**상황**: AWS API (create/update/delete)가 실패. 실행 중인 워크로드는 부분적으로 생존.

```
운영자가 실제 하는 일:

T+0분: 알림 수신
  → "인프라 프로비저닝 실패" / "CDK 배포 실패" / "Auto Scaling 그룹 조정 불가"
  → 실행 중인 워크로드는 아직 살아있는가? 확인
  → AWS Health Dashboard → 해당 리전 서비스 상태 확인

T+0-15분: 정적 안정성 모드 전환
  → ★ 핵심 원칙: "제어 평면이 죽었을 때, 데이터 평면은 계속 돌아야 한다"
  → 비필수적인 배포/인프라 변경 즉시 중지
    · CI/CD 파이프라인 일시 정지
    · Terraform/CDK apply 금지
    · Auto Scaling 정책 변경 금지
  → 사전 프로비저닝된 용량으로 운영 (Static Stability)
    · 최소 인스턴스 수 미리 확보해 둠
    · Provisioned Concurrency 활성 상태 확인

T+15-60분: 제어 평면 없이 운영
  → 새 리소스 생성 없이 기존 리소스로 버티기
  → 데이터 평면 제어만으로 조치 (ALB 가중치 조정, DNS 레코드 수정 등)
  → 긴급한 경우 다른 리전으로 트래픽 우회

T+60분+: 제어 평면 복구 대기 + 복구
  → AWS Health Dashboard에서 서비스 복구 모니터링
  → 복구 후 지연된 변경사항을 순차적으로 적용 (한꺼번에 X)
  → CI/CD 파이프라인 재개
```

**핵심 Best Practice (AWS Well-Architected)**:

```
제어 평면 장애에 대한 설계 원칙:
1. 데이터 평면과 제어 평면을 분리하여 설계
2. 정적 안정성(Static Stability): 제어 평상 없이도 서비스 유지 가능해야 함
3. 장애 중 제어 평면 쓰기 금지 — 악화시킬 수 있음
4. 사전 프로비저닝된 용량 확보 (최소 인스턴스, PC, Reserved 등)
```

---

### 2.3 종속성 장애 / 연쇄 실패 (Dependency / Cascading Failure)

**상황**: 하위 서비스 하나의 지연이 재시도 폭풍을 유발하여 상위 서비스들까지 연쇄 마비.

```
운영자가 실제로 하는 일:

T+0분: 알림 수신
  → 여러 서비스에서 동시 에러 급증
  → "모든 게 느려졌다" / "타임아웃 폭발"
  → 에러가 한 서비스에서 시작되어 전파된 패턴인지 확인

T+5-15분: 장애 발원지 식별
  → X-Ray 서비스 맵에서 빨간색/노란색 노드 찾기
  → "뿌리(Root Cause) 노드" 식별
  → CloudWatch Logs에서 타임라인 재구성
    · "A 서비스에서 먼저 에러 발생 → B에서 재시도 증가 → C에서 연결 고갈"

T+15-30분: 재시도 폭풍 차단 (가장 중요!)
  → ★ 핵심 조치: 재시도를 줄여야 전체 시스템이 회복됨
  → 장애 발원지로의 호출에 서킷브레이커 적용
  → 재시도 횟수 제한, 백오프+지터 추가
  → 비핵심 소비자(Consumer) 비활성화
    · 배치 작업 일시 중지
    · 분석/리포팅 워크로드 중지
  → "핵심 트랜잭션만 보호, 나머지는 희생"

T+30-60분: 캐시/대체 경로 활용
  → 장애 서비스 대신 캐시된 데이터 제공 (Stale but available)
  → 읽기 전용 모드로 전환 가능한지 평가
  → 대체 서비스/경로로 우회 (Circuit Breaker Fallback)

T+60분+: 점진적 복원
  → 장애 서비스가 복구되면 트래픽을 점진적으로 복원
  → 한꺼번에 트래픽을 쏘지 않고, 10% → 25% → 50% → 100%
  → 재시도 제한을 원래 수준으로 천천히 복원
  → Bulkhead 격리가 제대로 동작했는지 사후 확인
```

**Best Practice (Google SRE / AWS Reliability Pillar)**:

```
연쇄 실패 방지 원칙:
1. Retry with Exponential Backoff + Jitter (지터 없으면 Thundering Herd)
2. Circuit Breaker: 연속 실패 N회 후 자동 차단, 주기적 Probe로 복구 감지
3. Bulkhead: 서비스별 스레드/연결 풀 분리 → 하나가 고갈해도 다른 건 영향 없게
4. Timeout: 모든 외부 호출에 명시적 타임아웃 설정 (기본값에 의존 금지)
5. Graceful Degradation: 핵심 경로만 보호, 부가 기능은 비활성화
```

---

### 2.4 RDS 페일오버

**상황**: RDS Multi-AZ 페일오버 발생. 애플리케이션에서 DB 연결 실패.

```
운영자가 실제로 하는 일:

T+0분: 알림 수신
  → "RDS 페일오버 이벤트 감지" / "DB 연결 에러 급증"
  → 애플리케이션 에러 로그에서 DB 관련 에러 확인

T+0-5분: 페일오버 상태 확인
  → RDS 콘솔 또는 CLI에서 인스턴스 상태 확인
    $ aws rds describe-db-instances --db-instance-identifier <INSTANCE> \
      --query 'DBInstances[0].{Status:DBInstanceStatus, MultiAZ:MultiAZ}'
  → 페일오버 진행 중인지, 완료되었는지 확인
  → 새 Writer 엔드포인트 확인

T+5-15분: 네트워크 경로 검증
  → Route Table: 새 Writer가 있는 AZ로 라우팅 가능한가?
  → Security Group: 새 AZ의 서브넷에 대한 접근 허용되어 있는가?
  → NACL: 서브넷 간 통신 허용?
  → DNS: Writer 엔드포인트가 새 인스턴스를 가리키는가?

T+15-30분: 애플리케이션 연결 복구
  → ★ 가장 흔한 문제: 오래된 커넥션 풀이 이전 Writer를 가리킴
  → 애플리케이션 재시작 또는 커넥션 풀 강제 갱신
  → DNS 캐시 만료 대기 또는 수동 플러시
  → 커넥션 수가 정상 수준으로 돌아왔는지 확인

T+30-60분: 안정화 확인
  → 쿼리 지연이 정상 범위인지 확인
  → 복제 지연(Replica Lag)이 0에 수렴하는지 확인
  → 애플리케이션 에러율이 정상화되었는지 확인

T+60분+: 정상 운영 복귀
  → 페일오버 원인 분석 (자동인가? 수동 트리거인가?)
  → 원래 AZ로 페일백 필요성 평가
```

**흔한 지연 원인**:

| 지연 원인 | 설명 | 소요 시간 |
|----------|------|----------|
| 커넥션 풀 Stale Pinning | 앱이 이전 DB 엔드포인트에 연결을 유지 | 5-30분 |
| DNS 캐시 | 클라이언트가 이전 IP를 캐싱 | TTL까지 대기 (보통 15-60초) |
| Route Table 불일치 | 새 AZ의 서브넷 라우팅 누락 | 10-30분 (발견 시점까지) |
| 쿼리 부하 재집중 | 모든 커넥션이 동시에 재연결 | 5-15분 |

---

### 2.5 Lambda 쓰로틀링 스파이크

**상황**: Lambda 함수에 429 TooManyRequestsException 발생. 동시성 한계 도달.

```
운영자가 실제로 하는 일:

T+0분: 알림 수신
  → Lambda Throttles > 0 알람
  → API Gateway에서 503/429 응답 증가

T+0-5분: 동시성 수준 확인
  → 계정 레벨 한계인가, 함수 레벨 한계인가?
    $ aws lambda get-account-settings --query 'AccountLimit.ConcurrentExecutions'
    $ aws lambda get-function-concurrency --function-name <FN>
  → CloudWatch에서 ConcurrentExecutions vs AccountQuota 비교

T+5-15분: 원인 파악
  → 트래픽 급증인가? (정상 스파이크)
  → 재시도 폭풍인가? (포이즌 필 메시지)
  → 다른 함수가 동시성을 독점하고 있는가?

T+15-30분: 즉각적 완화
  → [계정 한계] Service Quotas에서 동시성 증가 요청
  → [함수 한계] Reserved Concurrency 증설
    $ aws lambda put-function-concurrency \
      --function-name <FN> --reserved-concurrent-executions <NEW_LIMIT>
  → [트래픽 버퍼링] SQS 이벤트 소스의 MaxConcurrency 조정
  → [비중요 함수] 다른 함수의 Reserved Concurrency를 낮춰 중요 함수에 할당

T+30-60분: 근본 대응
  → Provisioned Concurrency 설정 (콜드스타트 방지 + 동시성 보장)
  → 함수 실행 시간(Duration) 최적화 — 단축하면 같은 동시성으로 더 많은 요청 처리
  → SQS/DynamoDB Stream으로 비동기 버퍼링 도입

T+60분+: 예방 체계 구축
  → 동시성 모니터링 알람 설정 (AccountQuota의 70% 경고)
  → 중요 함수별 Reserved Concurrency 격리
  → 부하 테스트로 실제 한계 사전 파악
```

---

### 2.6 ECS 서비스 저하 / 크래시 루프

**상황**: ECS 태스크가 반복적으로 실패하고 서비스가 Steady State에 도달하지 못함.

```
운영자가 실제로 하는 일:

T+0분: 알림 수신
  → ECS 서비스 이벤트: "service <NAME> was unable to start tasks"
  → RunningTaskCount 급감

T+0-5분: 태스크 중지 사유 확인 (★ 시간 싸움 — 90일 보존)
  → 가장 먼저 할 것: stoppedReason + exitCode 확인
    $ aws ecs describe-tasks --cluster <CLUSTER> --tasks <TASK_ARN> \
      --query 'tasks[0].{StoppedReason:stoppedReason, ExitCode:containers[0].exitCode}'
  → 서비스 이벤트 메시지 확인
    $ aws ecs describe-services --cluster <CLUSTER> --services <SERVICE> \
      --query 'services[0].events[:5]'

T+5-15분: exitCode 기반 분기
  → exit 137 → OOM Kill 의심 → 메모리 사용량 확인
  → exit 1 → 애플리케이션 에러 → 컨테이너 로그 확인
  → CannotPullContainerError → ECR/IAM/네트워크 문제
  → ResourceInitializationError → Secrets Manager/SSM 접근 실패
  → Health Check 반복 실패 → 배포 설정 불일치

T+15-30분: 즉각적 복구
  → ★ 핵심: "진짜 원인 찾기 전에 먼저 안정화"
  → 이전(마지막 정상) 태스크 정의로 롤백
    $ aws ecs update-service --cluster <CLUSTER> --service <SERVICE> \
      --task-definition <LAST_GOOD_TASK_DEF>
  → 서킷 브레이커가 활성화되어 있다면 자동 롤백 대기
  → 최소 Healthy 태스크 수 확보 후 원인 분석 시작

T+30-60분: 원인 분석
  → 마지막 배포에서 무엇이 변경되었는가?
    · 이미지 태그/다이제스트 변경?
    · 환경변수/시크릿 변경?
    · CPU/메모리 제한 변경?
    · 헬스체크 엔드포인트/간격 변경?
  → 컨테이너 로그에서 에러 패턴 확인
  → 새 이미지가 로컬에서 정상 동작하는지 확인

T+60분+: 예방 체계
  → ECS 배포 서킷 브레이커 활성화
  → Blue/Green 또는 Canary 배포 도입
  → 태스크 정의 변경 시 자동 diff 검증
```

---

### 2.7 VPC / 네트워크 장애

**상황**: 서비스 간 통신 불가. VPC 내/외부 연결 문제.

```
운영자가 실제로 하는 일:

T+0분: 알림 수신
  → "Connection timed out" / "Connection refused" 에러 급증
  → 특정 서브넷/AZ에 집중된 패턴인가?

T+0-5분: 장애 계층 식별 (★ 핵심: "어느 레이어인가?")
  → DNS 해석 문제인가? → Route 53 Resolver 확인
  → 라우팅 문제인가? → Route Table 확인
  → 정책 차단인가? → SG/NACL 확인
  → NAT/IGW 문제인가? → 외부 통신 경로 확인
  → 엔드포인트 문제인가? → VPC Endpoint 상태 확인

T+5-15분: Reachability Analyzer 실행 (★ 가장 빠른 진단)
  → 소스 → 대상 간 연결성 분석
    $ aws ec2 describe-network-insights-analyses
  → 결과가 "Not Reachable"이면 설명(Explanation) 확인:
    · SG 차단? NACL 차단? Route 누락? 엔드포인트 정책?

T+15-30분: VPC Flow Logs 분석
  → REJECT 패턴 확인: 어떤 srcAddr → dstAddr:dstPort가 차단되는가?
  → 특정 포트에 REJECT 집중 → SG/NACL 규칙 누락
  → NAT 경로 이상 → NAT Gateway 메트릭 확인
  → DNS(53) REJECT → DNS 해석 경로 문제

T+30-60분: 최근 변경사항 확인 + 복구
  → CloudTrail에서 최근 VPC/SG/NACL/Route 변경 이력
  → 의심되는 변경사항 롤백
  → 경로별로 점진적 복원 (핵심 경로 우선)

T+60분+: 전체 경로 검증
  → 모든 서비스 간 연결성 재확인
  → Reachability Analyzer로 "Reachable" 확인
  → VPC Flow Logs에서 REJECT 소멸 확인
```

---

### 2.8 리전 전체 장애 (Region-Wide Outage)

**상황**: AWS 리전 전체 서비스 장애. (과거 us-east-1 장애 사례 다수)

```
운영자가 실제로 하는 일:

T+0분: 알림 수신
  → 여러 서비스에서 동시 장애 보고
  → AWS Health Dashboard에서 리전 이벤트 확인
  → Twitter/X에서 #AWSdown 확인 (공식보다 빠를 수 있음)

T+0-10분: SEV1 선언 + 워룸 구성
  → IC 선임, 전담팀 구성
  → 상태 페이지 업데이트 (10분 내)
  → AWS Support에 High-Severity 케이스 오픈

T+10-30분: 리전 우회 실행
  → Route 53 페일오버: 장애 리전 → 대기 리전으로 트래픽 전환
  → ARC Routing Controls: 리전 단위 라우팅 제어
  → 핵심 기능 우선 복원, 비핵심 기능은 비활성화
  → 쓰기 작업 전략 결정:
    · 단일 Writer 유지? (데이터 일관성 우선)
    · 다중 Writer 허용? (가용성 우선, 충돌 해결 필요)

T+30-60분: 대기 리전 안정화
  → 대기 리전의 용량 충분한지 확인
  → Auto Scaling 그룹 확장
  → 데이터 복제 상태 확인 (RDS, DynamoDB Global Table, S3 Cross-Region Replication)
  → 쓰기 트래픽 허용 여부 결정

T+60분+: 장애 리전 복구 대기
  → AWS Health Dashboard에서 복구 공지 모니터링
  → 복구 후 페일백 계획 수립:
    · 데이터 일관성 검증
    · 백로그 소화
    · 점진적 트래픽 복원 (10% → 25% → 50% → 100%)
  → 페일백은 "다음 영업일"에 진행하는 것도 고려

T+해결 후: 사후 분석
  → DR 전략 유효성 검증 (RTO/RPO 달성 여부)
  → 페일오버 런북 업데이트
  → 리전 간 데이터 일관성 최종 검증
```

**실제 사례에서 배운 교훈**:

| 사례 | 교훈 |
|------|------|
| **2020년 us-east-1 Kinesis 장애** (23시간) | 관리형 서비스도 장애 난다. 리전 간 독립성이 핵심 |
| **2021년 us-east-1 네트워크 장애** | 단일 리전 의존도가 높은 서비스가 큰 타격. Multi-Region 필수 |
| **2023년 us-east-1 Lambda 장애** | 서버리스도 장애 난다. 정적 안정성 설계 필요 |
| **Ably (Multi-Region 운영사)** | us-east-1 장애 시 eu-west-1이 자동 승격. 사전 구축된 페일오버가 핵심 |
| **Short.io** | us-east-1 장애 시 상태 페이지 마저 같은 리전에 있어 업데이트 불가. 상태 페이지는 다른 리전/서비스에 두기 |

---

### 2.9 AZ 수준 장애 (AZ-Level Failure)

**상황**: 특정 AZ(가용 영역) 내 인프라 장애.

```
운영자가 실제로 하는 일:

T+0분: 알림 수신
  → 특정 AZ의 타겟/인스턴스 헬스체크 실패
  → 에러가 특정 AZ에 집중 (CloudWatch AZ 차원)

T+0-10분: AZ 격리
  → 비정상 AZ 트래픽 제거:
    · ALB: 타겟 헬스체크 기반 자동 제거
    · ARC Zonal Shift: 해당 AZ로의 트래픽 차단
    · Auto Scaling: 해당 AZ의 인스턴스 교체 시도, 실패 시 다른 AZ에서 확장
  → DB 페일오버 필요성 평가 (Writer가 장애 AZ에 있는가?)

T+10-30분: 종속성 정렬
  → DB, 캐시, 큐가 같은 AZ에 종속되어 있지 않은지 확인
  → 큐/스트림 소비자가 다른 AZ에서 정상 동작하는지 확인
  → NAT Gateway: 장애 AZ의 NAT Gateway가 유일한 경로인 경우 대체 경로 확인

T+30-60분: 용량 재균형
  → 나머지 정상 AZ에서 충분한 용량 확보
  → Auto Scaling 그룹이 정상 AZ에서 확장 가능한지 확인
  → 정상 AZ의 리소스 한계(인스턴스 한도 등) 확인

T+60분+: AZ 복구 후 재도입
  → AWS에서 해당 AZ 정상화 발표 후에만 트래픽 재도입
  → 소량 트래픽부터 점진적 증가
  → AZ별 메트릭 모니터링 강화
```

---

### 2.10 S3 / CloudFront 가용성 문제

**상황**: S3 5xx/SlowDown 에러, CloudFront 502/503/504.

```
운영자가 실제로 하는 일:

T+0분: 알림 수신
  → S3 5xxErrorRate 상승 또는 CloudFront 5xxErrorRate 상승
  → 고객이 "업로드 실패" / "페이지 로딩 안 됨" 보고

T+0-10분: 에지 vs 원본 구분 (★ 가장 중요)
  → CloudFront가 문제인가, 원본(S3/ALB)이 문제인가?
  → CloudWatch 메트릭 비교:
    · CloudFront OriginLatency 높음 → 원본 문제
    · CloudFront OriginLatency 낮음 + 5xx → 에지/WAF/정책 문제
  → Athena에서 CloudFront Access Logs 확인:
    · x_edge_result_type 분석
    · X-Cache 상태 확인

T+10-30분: 원인별 대응
  → [S3 5xx/SlowDown]:
    · Hot Prefix: 특정 키 접두사에 요청 집중 → prefix 분산
    · 요청률 버스트: exponential backoff + jitter 적용
    · AWS Health: S3 리전 서비스 상태 확인
  → [CloudFront 502/504]:
    · 원본 응답 지연: 원본 서버(ALB/Lambda) 로그 확인
    · TLS 인증서 만료: ACM 인증서 상태 확인
    · 원본 타임아웃: CloudFront Origin Response Timeout 조정
  → [CloudFront 403]:
    · WAF 차단: WAF Logs에서 규칙 매치 확인
    · Geo Restriction: 특정 국가 차단 정책 확인
    · Signed URL/Policy: 서명 만료 확인

T+30-60분: 완화 조치
  → 캐시 TTL 증가로 원본 호출 감소
  → CloudFront 무효화(Invalidation) 생성 (오래된 캐시 문제 시)
  → 클라이언트 재시도 백오프 적용 (Self-inflicted load 방지)

T+60분+: 정상화
  → 에러율 정상 범위 복원 확인
  → 캐시 적중률 정상화 확인
  → 재시도 패턴 정상화 확인
```

---

## 3. 장애 대응 시 "절대 하면 안 되는 것"

| 행동 | 이유 | 올바른 대안 |
|------|------|-----------|
| **장애 중 원인 파악에 집착** | 완화가 먼저. 원인은 나중에 | "안정화 → 완화 → 원인" 순서 |
| **여러 변경을 동시에 적용** | 어떤 것이 효과가 있었는지 모름 | 한 번에 하나씩, 변경 간 5분 대기 |
| **비난(Blame)하는 분위기** | 문제 은평, 보고 지연 유발 | Blameless Post-Mortem 문화 |
| **장애 중 "왜 안 되지?" 반복** | 제어 평면에 부하 가중 | 데이터 평면으로만 조치, 제어 평면은 최소화 |
| **상태 페이지 업데이트 안 함** | 고객 불신, SNS 폭발 | 정기 업데이트 (20-30분마다) |
| **장애 복구 직후 바로 정상 운영** | 2차 장애 위험 | "Resolved + Monitoring" 기간 30분 유지 |
| **AWS Support에 늦게 연락** | 플랫폼 이슈일 경우 시간 낭비 | 플랫폼 이슈 의심 시 즉시 케이스 오픈 |
| **로그를 수집하지 않고 재시작** | 원인 증거 소멸 | 재시작 전 로그/메트릭 스냅샷 확보 |

---

## 4. 사후 분석 (Post-Mortem) 워크플로우

### 4.1 Blameless Post-Mortem 원칙

```
핵심 가치:
1. "누가 잘못했는가?"가 아니라 "시스템이 왜 이것을 막지 못했는가?"
2. 모든 참여자가 안전하게 의견 제출
3. 프로세스/시스템 개선에 집중, 개인 비난 금지
4. "5 Whys" 기법으로 근본 원인 추적
```

### 4.2 Post-Mortem 문서 구조

```markdown
# Post-Mortem: [장애 제목]

## 요약
- 날짜/시간 (UTC)
- 영향 범위 (서비스, 고객 수, 지속 시간)
- 타임라인 요약

## 타임라인 (상세)
| 시간 (UTC) | 이벤트 |
|-----------|--------|
| T+0 | 알림 수신 |
| T+5 | SEV1 선언 |
| T+15 | 원인 의심 서비스 식별 |
| T+30 | 완화 조치 실행 |
| T+45 | 복구 확인 |
| T+60 | Resolved 선언 |

## 근본 원인 (Root Cause)
[5 Whys 분석 결과]

## 완화 및 복구 내용
[무엇을 했는가, 무엇이 효과가 있었는가]

## 개선 액션 아이템
| 항목 | 우선순위 | 담당자 | 기한 | 상태 |
|------|---------|--------|------|------|
| 알람 임계값 조정 | High | @name | 1주 내 | Open |
| 런북 업데이트 | High | @name | 3일 내 | Open |
| 서킷브레이커 도입 | Medium | @name | 2주 내 | Open |
| 부하 테스트 실시 | Medium | @name | 1달 내 | Open |

## 교훈 (Lessons Learned)
- 잘한 것: [긍정적 측면]
- 개선 필요: [부정적 측면]
- 운이 좋았던 점: [더 나빴을 수 있는 상황]
```

### 4.3 개선 액션 아이템 분류

| 카테고리 | 예시 | 일반적 기한 |
|----------|------|-----------|
| **모니터링/알람** | 누락된 메트릭 알람 추가, 임계값 조정 | 1-3일 |
| **런북/문서** | 장애 대응 런북 작성/갱신, 의사결정 트리 추가 | 3-7일 |
| **자동화** | 수동 조치를 자동화, 런북을 코드로 | 1-4주 |
| **아키텍처** | 서킷브레이커 도입, Bulkhead 격리, Multi-AZ 보강 | 2-8주 |
| **프로세스** | 에스컬레이션 기준 명확화, Game Day 실시 | 2-4주 |

---

## 5. oh-my-aws AI Agent가 지원할 수 있는 영역

### 5.1 인간 운영자 워크플로우와 Agent 자동화 매핑

| 운영자 행동 | 현재 (수동) | oh-my-aws Agent 지원 가능 |
|------------|-----------|------------------------|
| 알림 수신 → 초기 분류 | PagerDuty 알림 → 대시보드 확인 | Agent가 자동으로 메트릭/로그 수집, 영향 범위 분석 |
| SEV 선언 | 인간 판단 | Agent가 메트릭 기반으로 심각도 추천 |
| 워룸 구성 | Slack 채널 수동 생성 | Agent가 인시던트 채널 생성, 역할 할당 제안 |
| AWS Health 확인 | 콘솔 수동 확인 | Agent가 API로 자동 조회 |
| 로그/메트릭 조회 | CW Logs Insights 수동 쿼리 | Agent가 시나리오에 맞는 쿼리 자동 실행 (06번 문서 활용) |
| 원인 분석 | 여러 도구를 수동으로 오가며 | Agent가 X-Ray + Logs + Metrics를 종합 분석 |
| 완화 조치 수행 | CLI/콘솔에서 수동 실행 | Agent가 가드레일 내에서 안전한 조치 실행 (05번 문서 활용) |
| 상태 페이지 업데이트 | 수동 작성 | Agent가 템플릿 기반으로 초안 생성 |
| Post-Mortem 작성 | 회의 후 수동 작성 | Agent가 타임라인 자동 생성, 개선 제안 |

### 5.2 Agent가 "절대 대체하지 않아야 할" 영역

| 영역 | 이유 |
|------|------|
| **최종 의사결정** | 비즈니스 영향 판단은 인간이 해야 함 |
| **고객 커뮤니케이션** | 어조, 맥락, 약속은 인간이 승인해야 함 |
| **장애 중 위험한 조치** | 데이터 손실 위험이 있는 조치는 인간 승인 필수 |
| **Post-Mortem 비난 여부 판단** | 조직 문화적 판단은 인간의 영역 |
| **에스컬레이션 대상 결정** | 조직 정치, 인간 관계 고려 필요 |

---

## 6. 참고 자료

### AWS 공식

- [AWS Well-Architected Reliability Pillar](https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html)
  - Data Plane vs Control Plane 분리 (`REL11-BP04`)
  - Static Stability (`REL11-BP05`)
  - 정상 리소스로 페일오버 (`REL11-BP02`)
  - Multi-AZ/Multi-Region 전략 (`REL10-BP01`)
  - DR 전략 RTO/RPO (`REL13-BP02`)
  - 종속성 장애 완화 (`REL05-BP01/02/03/04/07`)
- [Route 53 DNS Failover](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/dns-failover-types.html)
- [AWS Application Recovery Controller (ARC)](https://docs.aws.amazon.com/r53recovery/latest/dg/what-is-route53-recovery.html)
- [AWS Incident Response Playbooks (GitHub)](https://github.com/aws-samples/aws-incident-response-playbooks)
- [AWS Incident Response Playbooks Workshop (GitHub)](https://github.com/aws-samples/aws-incident-response-playbooks-workshop)
- [AWS Security Incident Response Guide](https://docs.aws.amazon.com/security-ir/latest/userguide/develop-and-test-incident-response-plan.html)

### AWS 장애 사후 분석 (공식)

- [2023-06-13 Kinesis/CloudWatch 등 us-east-1 장애](https://aws.amazon.com/message/12721/)
- [2021-12-15 us-east-1 네트워크 장애](https://aws.amazon.com/message/41926/)
- [2020-11-25 Kinesis 장애](https://aws.amazon.com/message/11201/)
- [2023-06-07 us-east-1 Lambda 장애](https://aws.amazon.com/message/67457/)
- [2023-06-13 us-east-1 추가 장애](https://aws.amazon.com/message/061323/)

### 산업 Best Practice

- [Google SRE Book - Handling Overload](https://sre.google/sre-book/handling-overload/)
- [Google SRE Book - Incident Response](https://sre.google/sre-book/managing-incidents/)
- [PagerDuty - Incident Response Best Practices](https://www.pagerduty.com/resources/learn/incident-response-best-practices/)
- [Atlassian Incident Management](https://www.atlassian.com/incident-management)
- [Ably - Multi-Region Resilience During AWS Outage](https://ably.com/blog/multi-region-resilience-aws-outage)
- [Short.io - Post-Mortem on AWS Incident](https://blog.short.io/post-mortem-on-oct-20th-aws-incident/)
