# AWS Log Source Map

> 목적: AWS 장애 조사 시 어디서 어떤 로그를 어떻게 조회하는지 빠르게 참조
> 원본: `docs/research/06-aws-incident-log-reference.md`

---

## 핵심 구분: CloudWatch Logs vs S3

```
CloudWatch Logs (CW Logs Insights로 직접 쿼리):
  Lambda 실행 로그 / API Gateway 로그 / ECS 컨테이너 로그 /
  RDS 로그 / VPC Flow Logs (선택) / WAF 로그 (선택) /
  Route 53 Resolver Query Logs / EKS 컨테이너 로그

S3 저장 (Athena 또는 S3 Select로 쿼리):
  ALB/NLB Access Logs / CloudFront Standard Access Logs /
  S3 Server Access Logs / CloudTrail 이벤트 / VPC Flow Logs (선택)
```

---

## 서비스별 로그 소스

| 서비스 | 로그 종류 | 저장 위치 | 기본 활성화 | 접근 방법 |
|--------|----------|----------|------------|----------|
| **Lambda** | 실행 로그 (stdout/stderr) | CW Logs `/aws/lambda/<함수명>` | O | CW Logs Insights |
| **Lambda** | X-Ray 트레이스 | X-Ray API | X-Ray 활성화 필요 | X-Ray API/콘솔 |
| **API Gateway** | Access Logs | CW Logs `API-Gateway-Execution-Logs_<API_ID>/<Stage>` | Stage에서 활성화 필요 | CW Logs Insights |
| **API Gateway** | Execution Logs | 위와 동일 | Stage에서 활성화 필요 | CW Logs Insights |
| **ECS/Fargate** | 컨테이너 stdout/stderr | CW Logs `/ecs/<태스크정의명>` (awslogs 드라이버) | 태스크 정의 설정 필요 | CW Logs Insights |
| **ECS/Fargate** | 서비스 이벤트 | ECS API (90일 보존) | O | `aws ecs describe-services` |
| **RDS** | Error Log | CW Logs `/aws/rds/instance/<인스턴스명>/error` | 파라미터 그룹 + CW 내보내기 설정 필요 | CW Logs Insights |
| **RDS** | Slow Query Log | CW Logs `/aws/rds/instance/<인스턴스명>/slowquery` | 파라미터 그룹 설정 필요 | CW Logs Insights |
| **RDS** | General Log | CW Logs `/aws/rds/instance/<인스턴스명>/general` | 성능 영향 있음, 주의 | CW Logs Insights |
| **ALB/NLB** | Access Logs | **S3 버킷** (지정 경로) | 로드밸런서 속성에서 활성화 필요 | S3 → Athena |
| **CloudFront** | Standard Access Logs | **S3 버킷** | Distribution 설정에서 활성화 필요 | S3 → Athena |
| **CloudFront** | Real-Time Logs | CW Logs 또는 Kinesis | Distribution 설정에서 활성화 필요 | CW Logs Insights |
| **VPC** | Flow Logs | CW Logs **또는** S3 (선택) | VPC/서브넷/ENI에서 활성화 필요 | CW Logs Insights 또는 Athena |
| **S3** | Server Access Logs | **S3 버킷** (별도 버킷에 저장) | 버킷 속성에서 활성화 필요 | S3 → Athena |
| **CloudTrail** | Management Events | S3 + CW Logs (선택) | Trail 생성 필요 | CloudTrail API 또는 Athena |
| **CloudTrail** | Data Events (S3/Lambda) | S3 | Trail에서 Data Events 활성화 필요 | S3 → Athena |
| **WAF** | Web ACL Logs | S3 / CW Logs / Kinesis Firehose | Web ACL에서 활성화 필요 | Athena 또는 CW Logs |
| **Route 53** | Resolver Query Logs | CW Logs | Resolver 쿼리 로깅 활성화 필요 | CW Logs Insights |
| **EKS** | 컨테이너 로그 | CW Logs `/aws/eks/...` | Container Insights 또는 Fluent Bit 필요 | CW Logs Insights |

---

## Lambda — CloudWatch Logs Insights 쿼리

```sql
-- 타임아웃 탐지
fields @timestamp, @requestId, @message, @logStream
| filter @message like "Status: timeout" or @message like /Task timed out/
| sort @timestamp desc
| limit 100
```

```sql
-- Duration / 메모리 분석 (REPORT 라인)
filter @type = "REPORT"
| stats avg(@duration) as avgDur, max(@duration) as maxDur,
        max(@maxMemoryUsed/1024/1024) as maxMemMB,
        pct(@duration, 95) as p95
  by bin(5m)
```

```sql
-- 콜드 스타트 탐지
filter @type = "REPORT" and @initDuration > 0
| stats max(@initDuration) as maxInit, avg(@initDuration) as avgInit, count() as coldStarts
  by bin(5m)
```

```sql
-- 쓰로틀링 탐지
fields @timestamp, @message
| filter @message like /Rate exceeded/ or @message like /TooManyRequestsException/
| sort @timestamp desc
| limit 100
```

---

## RDS — CloudWatch Logs Insights 쿼리

```sql
-- 슬로우 쿼리 탐지 (PostgreSQL)
fields @timestamp, @message
| parse @message /duration: (?<duration>.*?) ms\s+statement: (?<statement>.*?)$/
| filter duration > 1000
| sort duration desc
| limit 50
```

```sql
-- 에러 로그에서 심각 메시지
fields @timestamp, @message
| filter @message like /FATAL|PANIC|ERROR/
| sort @timestamp desc
| limit 100
```

```sql
-- Deadlock 탐지
fields @timestamp, @message
| filter @message like /deadlock detected/
| sort @timestamp desc
```

---

## VPC Flow Logs — CloudWatch Logs Insights 쿼리

```sql
-- REJECT 탐지 (SG/NACL 차단)
fields @timestamp, srcAddr, dstAddr, srcPort, dstPort, protocol, action
| filter action = "REJECT"
| sort @timestamp desc
| limit 100
```

```sql
-- 특정 대상 포트로의 REJECT 집계
stats count(*) as rejects by dstPort, protocol
| filter action = "REJECT"
| sort rejects desc
```

---

## API Gateway — CloudWatch Logs Insights 쿼리

```sql
-- 5xx 에러 탐지
fields @timestamp, status, ip, path, httpMethod, responseLatency, integrationLatency
| filter status >= 500
| sort @timestamp desc
| limit 100
```

```sql
-- 상태코드 분포
stats count(*) by status
| sort status
```

---

## 장애 조사 공통 순서

```
Step 1: 시간 창 확정 (UTC 기준, T-15m ~ T+15m → 증거에 따라 확장)
Step 2: 상관 키 확보 (requestId, x-amzn-requestid, traceId, principal ARN, source IP)
Step 3: 제어면(CloudTrail) + 데이터면(서비스 로그) 동시 수집
Step 4: 보안 사건인 경우 증거 보존 먼저 (스냅샷, 변경 금지)
Step 5: 서비스별 심층 조사
```

---

## ECS 태스크 exitCode 해석

| exitCode | 의미 | 조치 |
|----------|------|------|
| `0` | 정상 종료 | 의도된 종료인지 확인 |
| `1` | 애플리케이션 에러 | 컨테이너 로그에서 예외 확인 |
| `137` | SIGKILL (OOM 또는 수동 stop) | 메모리 사용량 + 태스크 메모리 한계 비교 |
| `139` | Segmentation Fault | 애플리케이션 코드/의존성 버그 |
| `143` | SIGTERM (정상 종료 요청) | 배포/스케일다운에 의한 것인지 확인 |
