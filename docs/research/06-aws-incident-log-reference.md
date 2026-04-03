# AWS 장애 상황별 로그 및 관측 신호 참조

> 조사일: 2026-04-03
> 목적: AWS 장애 발생 시 어디서 어떤 로그·메트릭·추적·이벤트를 확인해야 하는지, 그리고 어떻게 조회하는지를 종합 정리
> 대상: oh-my-aws AI Agent가 장애 조사 시 참조하는 "로그 룩업 테이블"

---

## 1. 개요

### 1.1 AWS 관측 신호의 5가지 영역

장애 조사에 필요한 관측(Observability) 신호는 로그에만 국한되지 않는다. 다음 5가지 영역을 종합적으로 봐야 한다.

| 영역 | 역할 | 대표 서비스 |
|------|------|------------|
| **Logs** | 이벤트 발생 기록, 에러 메시지, 요청/응답 상세 | CloudWatch Logs, S3 Access Logs, VPC Flow Logs, CloudTrail |
| **Metrics** | 시계열 수치 데이터 (CPU, 지연, 에러율, 처리량) | CloudWatch Metrics, Container Insights, Application Signals |
| **Traces** | 분산 요청의 end-to-end 경로 추적 | AWS X-Ray |
| **Events** | 제어平面 변경, 서비스 상태, 보안 이벤트 | CloudTrail, EventBridge, AWS Health |
| **Topology** | 리소스 간 의존 관계, 네트워크 경로 | Reachability Analyzer, VPC Flow Logs, X-Ray Service Map |

### 1.2 장애 조사 공통 순서 (모든 시나리오에 적용)

```
Step 1: 시간 창 확정 (UTC 기준, T-15m ~ T+15m → 증거에 따라 확장)
Step 2: 상관 키 확보 (requestId, x-amzn-requestid, traceId, principal ARN, source IP)
Step 3: 제어면(CloudTrail) + 데이터면(서비스 로그) 동시 수집
Step 4: 보안 사건인 경우 증거 보존 먼저 (스냅샷, 변경 금지)
Step 5: 서비스별 심층 조사 (아래 섹션 참조)
```

---

## 2. AWS 서비스별 로그 소스 맵

### 2.1 로그 소스 전체 맵

| 서비스 | 로그 종류 | 저장 위치 | 활성화 방법 | 접근 방법 |
|--------|----------|----------|------------|----------|
| **Lambda** | 실행 로그 (stdout/stderr) | CloudWatch Logs `/aws/lambda/<함수명>` | 기본 활성화 | CW Logs Insights |
| **Lambda** | Invocation 이벤트 | - (X-Ray/EventBridge로 추적) | X-Ray 활성화 필요 | X-Ray API |
| **API Gateway** | Access Logs | CloudWatch Logs `API-Gateway-Execution-Logs_<API_ID>/<Stage>` | Stage 설정에서 활성화 | CW Logs Insights |
| **API Gateway** | Execution Logs | 위와 동일 | Stage 설정에서 활성화 | CW Logs Insights |
| **ECS/Fargate** | 컨테이너 stdout/stderr | CloudWatch Logs `/ecs/<태스크정의명>` (awslogs 드라이버) | 태스크 정의 logConfiguration | CW Logs Insights |
| **ECS/Fargate** | 서비스 이벤트 | ECS 서비스 이벤트 (API로 조회) | 기본 기록, 90일 보존 | `aws ecs describe-services` |
| **RDS** | Error Log | CloudWatch Logs `/aws/rds/instance/<인스턴스명>/error` | 파라미터 그룹 + CloudWatch Logs 내보내기 활성화 | CW Logs Insights |
| **RDS** | Slow Query Log | CloudWatch Logs `/aws/rds/instance/<인스턴스명>/slowquery` | 파라미터 그룹 설정 | CW Logs Insights |
| **RDS** | General Log | CloudWatch Logs `/aws/rds/instance/<인스턴스명>/general` | 파라미터 그룹 설정 (성능 영향 주의) | CW Logs Insights |
| **ALB/NLB** | Access Logs | **S3 버킷** (지정 경로) | 로드밸런서 속성에서 활성화 | S3 → Athena 또는 S3 Select |
| **CloudFront** | Standard Access Logs | **S3 버킷** | Distribution 설정에서 활성화 | S3 → Athena |
| **CloudFront** | Real-Time Logs | CloudWatch Logs (또는 Kinesis) | Distribution 설정에서 활성화 | CW Logs Insights |
| **VPC** | Flow Logs | CloudWatch Logs **또는** S3 | VPC/서브넷/ENI에서 활성화 | CW Logs Insights 또는 S3 → Athena |
| **S3** | Server Access Logs | **S3 버킷** (다른 버킷에 저장) | 버킷 속성에서 활성화 | S3 → Athena |
| **CloudTrail** | Management Events | S3 + CloudWatch Logs (선택) | Trail 생성 | S3 → Athena 또는 CloudTrail API |
| **CloudTrail** | Data Events (S3/Lambda 등) | S3 | Trail에서 데이터 이벤트 활성화 | S3 → Athena |
| **CloudTrail** | Insight Events | S3 | Trail에서 Insight 활성화 | CloudTrail API |
| **WAF** | Web ACL Logs | S3 / CloudWatch Logs / Kinesis Data Firehose | Web ACL에서 활성화 | S3 → Athena 또는 CW Logs |
| **Route 53** | Resolver Query Logs | CloudWatch Logs | Resolver 쿼리 로깅 활성화 | CW Logs Insights |
| **EKS** | 컨테이너 로그 | CloudWatch Logs (`/aws/eks/...`) | Container Insights 또는 Fluent Bit | CW Logs Insights |

### 2.2 핵심 포인트: "CloudWatch Logs에 없는 로그들"

많은 AWS 로그가 **CloudWatch Logs가 아닌 S3에 저장**된다. 장애 조사 시 이 두 경로를 모두 알아야 한다.

```
CloudWatch Logs에 있는 것:
  Lambda 실행 로그 / API Gateway 로그 / ECS 컨테이너 로그 /
  RDS 로그 / VPC Flow Logs (선택) / WAF 로그 (선택)

S3에 있는 것 (Athena로 조회):
  ALB/NLB Access Logs / CloudFront Access Logs / S3 Server Access Logs /
  CloudTrail 이벤트 / VPC Flow Logs (선택)
```

---

## 3. 장애 시나리오별 조사 시퀀스

### 3.1 Lambda 타임아웃 / 쓰로틀링

#### 봐야 할 로그·신호

| 순서 | 신호 | 위치 | 조회 방법 |
|------|------|------|----------|
| **1** | 타임아웃 메시지 | CloudWatch Logs `/aws/lambda/<함수명>` | CW Logs Insights |
| **2** | Duration / 메모리 사용량 | CloudWatch Metrics `AWS/Lambda` | `aws cloudwatch get-metric-statistics` |
| **3** | Throttles / ConcurrentExecutions | CloudWatch Metrics `AWS/Lambda` | CW 대시보드 또는 API |
| **4** | 콜드 스타트 (Init Duration) | CloudWatch Logs REPORT 라인 | CW Logs Insights |
| **5** | 하위 서비스 호출 지연 | AWS X-Ray Traces | X-Ray 콘솔 또는 API |
| **6** | VPC 내 함수인 경우 네트워크 | VPC Flow Logs | CW Logs Insights 또는 Athena |
| **7** | IAM 권한 거부 | CloudTrail `InvokeFunction` 이벤트 | CloudTrail API 또는 Athena |

#### CloudWatch Logs Insights 쿼리

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
| bin(5m)
```

```sql
-- 콜드 스타트 탐지
filter @type = "REPORT" and @initDuration > 0
| stats max(@initDuration) as maxInit, avg(@initDuration) as avgInit, count() as coldStarts
| bin(5m)
```

#### CloudWatch Metrics

| 메트릭 | 네임스페이스 | 차원 | 통계 | 임계 예시 |
|--------|-------------|------|------|----------|
| `Duration` | `AWS/Lambda` | `FunctionName` | `p95`, `p99` | p95 > timeout × 0.8 |
| `Errors` | `AWS/Lambda` | `FunctionName` | `Sum` | > 0 |
| `Throttles` | `AWS/Lambda` | `FunctionName` | `Sum` | > 0 |
| `ConcurrentExecutions` | `AWS/Lambda` | (전역) | `Max` | ≈ Account Quota |
| `IteratorAge` | `AWS/Lambda` | `FunctionName`, `EventSourceMappingUUID` | `Max` | 급증 추세 |

#### CLI로 확인

```bash
# Lambda 설정 확인 (timeout, memory)
aws lambda get-function-configuration --function-name <FN> \
  --query '{Timeout: Timeout, MemorySize: MemorySize, Runtime: Runtime}'

# 계정 동시성 한계 확인
aws lambda get-account-settings \
  --query 'AccountLimit.ConcurrentExecutions'

# 함수 Reserved Concurrency 확인
aws lambda get-function-concurrency --function-name <FN>

# X-Ray: 에러/폴트 트레이스 요약
aws xray get-trace-summaries \
  --start-time "2026-04-03T00:00:00Z" \
  --end-time "2026-04-03T00:15:00Z" \
  --filter-expression 'service("<FN>") { fault = true OR error = true }'
```

#### 해석 가이드

| 패턴 | 의미 | 다음 단계 |
|------|------|----------|
| `Status: timeout` + 코드 스택트레이스 없음 | 런타임 타임아웃 (코드 문제 아님) | Duration 분석 → 하위 서비스 지연 확인 |
| `Throttles > 0` + `ConcurrentExecutions` 근접 | 동시성 한계 도달 | Reserved/Provisioned Concurrency 확인 |
| `@initDuration` 높음 (Java > 5초) | 콜드 스타트 | SnapStart / Provisioned Concurrency 검토 |
| `@maxMemoryUsed` ≈ `MemorySize` | 메모리 압박 → CPU도 병목 가능 | 메모리 증설 테스트 |
| CW에 Throttles 없는데 실패 | Lambda 자체가 아니라 하위 API가 쓰로틀 | X-Ray로 하위 서비스 확인 |

---

### 3.2 RDS 성능 저하

#### 봐야 할 로그·신호

| 순서 | 신호 | 위치 | 조회 방법 |
|------|------|------|----------|
| **1** | CPU / 메모리 / 스토리지 메트릭 | CloudWatch Metrics `AWS/RDS` | CW 대시보드 또는 API |
| **2** | Slow Query Log | CloudWatch Logs `/aws/rds/instance/<인스턴스명>/slowquery` | CW Logs Insights |
| **3** | Error Log | CloudWatch Logs `/aws/rds/instance/<인스턴스명>/error` | CW Logs Insights |
| **4** | 커넥션 수 | CloudWatch `DatabaseConnections` | CW Metrics |
| **5** | I/O 지연 | CloudWatch `ReadLatency`, `WriteLatency` | CW Metrics |
| **6** | Performance Insights (활성화 시) | RDS Performance Insights API | `aws pi get-resource-metrics` |
| **7** | Deadlock / Lock Wait | RDS 로그 (PostgreSQL: `log_lock_waits`) | CW Logs Insights |

#### 전제 조건: 로그가 "유용하려면"

RDS 로그가 장애 조사에 쓸모 있으려면 **파라미터 그룹 설정**이 먼저 되어야 한다.

```bash
# PostgreSQL 예시 - 필수 파라미터
log_min_duration_statement = 1000    # 1초 이상 쿼리 기록
log_lock_waits = on                  # 락 대기 기록
log_connections = on                 # 연결 기록
log_disconnections = on              # 연결 해제 기록
log_temp_files = 0                   # 임시 파일 사용 기록

# CloudWatch Logs 내보내기 활성화 (콘솔 또는 CLI)
aws rds modify-db-instance \
  --db-instance-identifier <INSTANCE> \
  --cloudwatch-logs-export-configuration '{"EnableLogTypes":["error","slowquery","general"]}'
```

#### CloudWatch Logs Insights 쿼리

```sql
-- 슬로우 쿼리 탐지 (PostgreSQL 형식)
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

#### CloudWatch Metrics

| 메트릭 | 네임스페이스 | 차원 | 통계 | 임계 예시 |
|--------|-------------|------|------|----------|
| `CPUUtilization` | `AWS/RDS` | `DBInstanceIdentifier` | `Average`, `Max` | > 80% |
| `FreeStorageSpace` | `AWS/RDS` | `DBInstanceIdentifier` | `Minimum` | < 10GB |
| `DatabaseConnections` | `AWS/RDS` | `DBInstanceIdentifier` | `Average`, `Max` | > max_connections × 0.8 |
| `ReadLatency` / `WriteLatency` | `AWS/RDS` | `DBInstanceIdentifier` | `Average`, `p99` | > 50ms |
| `ReadIOPS` / `WriteIOPS` | `AWS/RDS` | `DBInstanceIdentifier` | `Average` | > Provisioned IOPS |
| `FreeableMemory` | `AWS/RDS` | `DBInstanceIdentifier` | `Minimum` | < 512MB |
| `DiskQueueDepth` | `AWS/RDS` | `DBInstanceIdentifier` | `Average`, `Max` | > 10 |

#### CLI로 확인

```bash
# RDS 인스턴스 상태
aws rds describe-db-instances --db-instance-identifier <INSTANCE> \
  --query 'DBInstances[0].{Status:DBInstanceStatus, Class:DBInstanceClass, Storage:AllocatedStorage, MultiAZ:MultiAZ}'

# Performance Insights - 상위 SQL (활성화 시)
aws pi get-resource-metrics \
  --service-type RDS \
  --identifier db:<INSTANCE> \
  --metric-queries '[{Metric:{MetricName:"db.load.avg"}}]' \
  --start-time "2026-04-03T00:00:00Z" \
  --end-time "2026-04-03T00:15:00Z" \
  --period-in-seconds 300
```

#### 해석 가이드

| 패턴 | 의미 | 다음 단계 |
|------|------|----------|
| CPU 80%+ + 슬로우 쿼리 집중 | CPU 바운드 쿼리 | `EXPLAIN ANALYZE` → 인덱스 확인 |
| `FreeableMemory` 하락 + temp 파일 로그 | 메모리 부족 → 디스크 스필 | `work_mem` 파라미터 증설 |
| `DatabaseConnections` 급증 | 커넥션 풀 고갈 | RDS Proxy / PgBouncer 검토 |
| `ReadLatency` 스파이크 + IOPS 포화 | 스토리지 병목 | gp3 → io1 전환 또는 IOPS 증설 |
| Deadlock 메시지 반복 | 트랜잭션 경합 | 트랜잭션 순서 정렬, 행 수준 잠금 |
| `FreeStorageSpace` 지속 감소 | 스토리지 고갈 | 자동 확장 활성화 또는 수동 확장 |

---

### 3.3 API Gateway 5xx 에러

#### 봐야 할 로그·신호

| 순서 | 신호 | 위치 | 조회 방법 |
|------|------|------|----------|
| **1** | Access Logs (상태코드 분포) | CloudWatch Logs `API-Gateway-Execution-Logs_<API_ID>/<Stage>` | CW Logs Insights |
| **2** | 4xx/5xx 메트릭 | CloudWatch Metrics `AWS/ApiGateway` | CW Metrics |
| **3** | Execution Logs (요청-응답 상세) | CloudWatch Logs (위와 동일) | CW Logs Insights |
| **4** | 백엔드 로그 (Lambda/ECS) | 해당 서비스 로그 | CW Logs Insights |
| **5** | X-Ray 분산 추적 | AWS X-Ray | X-Ray API |
| **6** | WAF 차단 여부 | WAF Logs (S3 또는 CW Logs) | Athena 또는 CW Logs |

#### 전제 조건: 로그 활성화

```bash
# API Gateway Stage 로깅 활성화
aws apigateway update-stage \
  --rest-api-id <API_ID> \
  --stage-name <STAGE> \
  --patch-operations \
    '[{"op":"replace","path":"/accessLogSettings/destinationArn","value":"arn:aws:logs:..."}]'
    '[{"op":"replace","path":"/accessLogSettings/format","value":"$context.requestId $context.status $context.responseLatency $context.integrationLatency"}]'
```

#### CloudWatch Logs Insights 쿼리

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

```sql
-- 지연 시간 상위 요청
fields @timestamp, path, responseLatency, integrationLatency
| filter responseLatency > 1000
| sort responseLatency desc
| limit 50
```

#### CloudWatch Metrics

| 메트릭 | 네임스페이스 | 차원 | 통계 | 임계 예시 |
|--------|-------------|------|------|----------|
| `5XXError` | `AWS/ApiGateway` | `ApiName`, `Stage` | `Sum` | > 0 |
| `4XXError` | `AWS/ApiGateway` | `ApiName`, `Stage` | `Sum` | 트렌드 비교 |
| `Latency` | `AWS/ApiGateway` | `ApiName`, `Stage` | `p95`, `p99` | > SLA |
| `IntegrationLatency` | `AWS/ApiGateway` | `ApiName`, `Stage` | `p95`, `p99` | 백엔드 병목 지표 |
| `Count` | `AWS/ApiGateway` | `ApiName`, `Stage` | `Sum` | 트래픽 급감/급증 |

#### 해석 가이드

| 패턴 | 의미 | 다음 단계 |
|------|------|----------|
| 5xx + `IntegrationLatency` 높음 | 백엔드(Lambda/ECS) 지연/타임아웃 | 백엔드 로그 확인 |
| 5xx + `IntegrationLatency` 낮음 | API Gateway 자체 설정 문제 (매핑, 권한) | Execution Logs에서 설정 에러 확인 |
| 502 + 백엔드 스택트레이스 | 백엔드 응답 포맷/런타임 에러 | Lambda 코드 에러 확인 |
| 429 패턴 | Usage Plan / Throttle 한계 | Rate/Burst 설정 확인 |
| 403 + WAF 로그에 차단 기록 | WAF 규칙에 의한 차단 | WAF 규칙 검토 |

---

### 3.4 ECS 태스크 실패 / 크래시 루프

#### 봐야 할 로그·신호

| 순서 | 신호 | 위치 | 조회 방법 |
|------|------|------|----------|
| **1** | 태스크 중지 사유 + exitCode | ECS API `DescribeTasks` (90일 보존) | `aws ecs describe-tasks` |
| **2** | 서비스 이벤트 메시지 | ECS 서비스 이벤트 | `aws ecs describe-services` |
| **3** | 컨테이너 애플리케이션 로그 | CloudWatch Logs `/ecs/<태스크정의명>` | CW Logs Insights |
| **4** | CPU/메모리 사용률 | CloudWatch Metrics `AWS/ECS` 또는 `ECS/ContainerInsights` | CW Metrics |
| **5** | 헬스 체크 실패 | ECS + ALB Target Group | CW Metrics |
| **6** | 배포 서킷 브레이커 | ECS 서비스 이벤트 | `aws ecs describe-services` |

#### CloudWatch Logs Insights 쿼리

```sql
-- 컨테이너 에러 탐지
fields @timestamp, @message
| filter @message like /CannotPullContainerError|ResourceInitializationError|OutOfMemory|OOMKilled/
| sort @timestamp desc
| limit 200
```

```sql
-- 헬스 체크 실패 패턴
fields @timestamp, @message
| filter @message like /health check/ or @message like /unhealthy/
| sort @timestamp desc
| limit 100
```

#### CLI로 확인 (가장 먼저 할 것)

```bash
# 태스크 중지 사유 (90일 보존이므로 장애 직후 바로 확인)
aws ecs describe-tasks --cluster <CLUSTER> --tasks <TASK_ARN> \
  --query 'tasks[0].{StoppedReason:stoppedReason, ExitCode:containers[0].exitCode, LastStatus:lastStatus}'

# 서비스 이벤트 (배포 실패, 서킷 브레이커 등)
aws ecs describe-services --cluster <CLUSTER> --services <SERVICE> \
  --query 'services[0].events[:10]'
```

#### exitCode 해석

| exitCode | 의미 | 조치 |
|----------|------|------|
| `0` | 정상 종료 | 의도된 종료인지 확인 |
| `1` | 애플리케이션 에러 | 컨테이너 로그에서 예외 확인 |
| `137` | SIGKILL (OOM 또는 수동 stop) | 메모리 사용량 + 태스크 메모리 한계 비교 |
| `139` | Segmentation Fault | 애플리케이션 코드/의존성 버그 |
| `143` | SIGTERM (정상 종료 요청) | 배포/스케일다운에 의한 것인지 확인 |

#### CloudWatch Metrics

| 메트릭 | 네임스페이스 | 차원 | 통계 | 의미 |
|--------|-------------|------|------|------|
| `CPUUtilization` | `AWS/ECS` | `ClusterName`, `ServiceName` | `Average`, `Max` | CPU 병목 |
| `MemoryUtilization` | `AWS/ECS` | `ClusterName`, `ServiceName` | `Average`, `Max` | 메모리 압박 |
| `RunningTaskCount` | `ECS/ContainerInsights` | `ClusterName`, `ServiceName` | `Average` | 태스크 수 급감 = 크래시 |
| `RestartCount` | `ECS/ContainerInsights` | `ClusterName`, `ServiceName` | `Sum` | 크래시 루프 지표 |
| `PendingTaskCount` | `AWS/ECS` | `ClusterName`, `ServiceName` | `Sum` | > 0이면 리소스 부족 |

#### 해석 가이드

| 패턴 | 의미 | 다음 단계 |
|------|------|----------|
| exit 137 + MemoryUtilization 높음 | OOM Kill | 태스크 메모리 한계 증설 |
| 반복 헬스체크 실패 + 서킷 브레이커 | 배포 설정 불일치 | 이전 태스크 정의로 롤백 |
| `CannotPullContainerError` | ECR 이미지 접근 실패 | IAM 권한, ECR 정책, 네트워크 확인 |
| `ResourceInitializationError` | Secrets Manager / SSM Parameter 접근 실패 | IAM 권한, Secret 존재 여부 |
| RunningTaskCount 급감 | 대규모 크래시 | 최근 배포 변경사항 확인 |

---

### 3.5 VPC 연결 불가 / 네트워크 장애

#### 봐야 할 로그·신호

| 순서 | 신호 | 위치 | 조회 방법 |
|------|------|------|----------|
| **1** | Reachability Analyzer | VPC 콘솔 또는 API | `aws ec2 describe-network-insights-analyses` |
| **2** | VPC Flow Logs | CloudWatch Logs 또는 S3 | CW Logs Insights 또는 Athena |
| **3** | Security Group / NACL 규칙 | EC2 API | `aws ec2 describe-security-groups` |
| **4** | Route Table | EC2 API | `aws ec2 describe-route-tables` |
| **5** | NAT Gateway 메트릭 | CloudWatch `AWS/NATGateway` | CW Metrics |
| **6** | DNS 해석 | Route 53 Resolver Query Logs | CW Logs Insights |
| **7** | ENI conntrack (연결 추적) | EC2 ENA 메트릭 | CW Metrics |

#### 전제 조건: VPC Flow Logs 활성화

```bash
# CloudWatch Logs에 Flow Logs 전송
aws ec2 create-flow-logs \
  --resource-type VPC \
  --resource-ids <VPC_ID> \
  --traffic-type ALL \
  --log-destination-type cloud-watch-logs \
  --log-group-name /aws/vpc/flow-logs/<VPC_NAME> \
  --log-format '${version} ${account-id} ${interface-id} ${srcaddr} ${dstaddr} ${srcport} ${dstport} ${protocol} ${packets} ${bytes} ${start} ${end} ${action} ${log-status} ${vpc-id} ${subnet-id} ${instance-id} ${tcp-flags}'
```

#### VPC Flow Logs 버전별 필드

| 버전 | 핵심 필드 | 용도 |
|------|----------|------|
| **v2** (기본) | srcaddr, dstaddr, srcport, dstport, protocol, packets, bytes, action | 기본 연결 분석 |
| **v3** | v2 + vpc-id, subnet-id, instance-id, tcp-flags, pkt-srcaddr, pkt-dstaddr | NAT/라우팅 경로 분석 |
| **v5** | v3 + pkt-src-aws-service, pkt-dst-aws-service, flow-direction, traffic-path | AWS 서비스 경로 분석 |

#### CloudWatch Logs Insights 쿼리 (Flow Logs)

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

```sql
-- DNS (UDP 53) 차단 탐지
fields @timestamp, srcAddr, dstAddr
| filter dstPort = 53 and action = "REJECT"
| sort @timestamp desc
```

#### Athena 쿼리 (S3에 저장된 Flow Logs)

```sql
-- REJECT 상위 대상 포트
SELECT dstport, protocol, COUNT(*) AS rejects, SUM(bytes) AS total_bytes
FROM vpc_flow_logs
WHERE action = 'REJECT'
  AND from_unixtime(start) BETWEEN timestamp '2026-04-03 00:00:00'
                               AND timestamp '2026-04-03 00:15:00'
GROUP BY dstport, protocol
ORDER BY rejects DESC
LIMIT 20;
```

```sql
-- DNS 차단 분석
SELECT srcaddr, dstaddr, COUNT(*) AS reject_count
FROM vpc_flow_logs
WHERE dstport = 53
  AND action = 'REJECT'
  AND from_unixtime(start) > current_timestamp - interval '15' minute
GROUP BY srcaddr, dstaddr
ORDER BY reject_count DESC;
```

#### CloudWatch Metrics (네트워크)

| 메트릭 | 네임스페이스 | 차원 | 통계 | 의미 |
|--------|-------------|------|------|------|
| `ErrorPortAllocation` | `AWS/NATGateway` | `NatGatewayId` | `Sum` | NAT 포트 고갈 |
| `PacketsDropCount` | `AWS/NATGateway` | `NatGatewayId` | `Sum` | NAT 패킷 드롭 |
| `ConnectionAttemptCount` | `AWS/NATGateway` | `NatGatewayId` | `Sum` | NAT 연결 시도 |
| `conntrack_allowance_exceeded` | `AWS/EC2` (ENA) | `InstanceId` | `Sum` | 연결 추적 한계 초과 |
| `bw_in_allowance_exceeded` | `AWS/EC2` (ENA) | `InstanceId` | `Sum` | 대역폭 한계 초과 |

#### 해석 가이드

| 패턴 | 의미 | 다음 단계 |
|------|------|----------|
| Reachability Analyzer = "Not Reachable" + explanation SG | Security Group 차단 | SG 규칙 수정 |
| Reachability Analyzer = "Reachable" but Flow Logs = REJECT | 런타임 정책 드리프트 | NACL, VPC Endpoint Policy 확인 |
| 특정 dstPort에 REJECT 집중 | SG/NACL에 해당 포트 누락 | 인바운드 규칙 추가 |
| NAT `ErrorPortAllocation` > 0 | NAT 포트 고갈 | NAT Gateway 확장 또는 분산 |
| DNS (53) REJECT | DNS 해석 불가 | VPC DNS 설정 확인 |
| `conntrack_allowance_exceeded` > 0 | 연결 추적 한계 | 연결 수 줄이거나 인스턴스 크기 확장 |

---

### 3.6 CloudFront 캐시 / 지연 / 에러

#### 봐야 할 로그·신호

| 순서 | 신호 | 위치 | 조회 방법 |
|------|------|------|----------|
| **1** | CloudWatch 메트릭 (에러율, 캐시 적중률) | CloudWatch Metrics `AWS/CloudFront` | CW Metrics |
| **2** | Standard Access Logs | **S3 버킷** | S3 → Athena |
| **3** | Real-Time Logs (활성화 시) | CloudWatch Logs | CW Logs Insights |
| **4** | 원본(Origin) 서버 로그 | ALB/S3/Lambda 로그 | 해당 서비스 로그 |
| **5** | WAF 로그 | S3 또는 CW Logs | Athena 또는 CW Logs |
| **6** | `X-Cache` 헤더 | Access Logs 필드 | Athena 쿼리 |

#### Athena 쿼리 (CloudFront Standard Logs)

```sql
-- 에러 상태코드 상위 요청
SELECT date, time, x_edge_result_type, sc_status, cs_host, cs_uri_stem,
       time_taken, time_to_first_byte
FROM cloudfront_logs
WHERE date >= current_date - interval '1' day
  AND sc_status >= 400
ORDER BY time_taken DESC
LIMIT 100;
```

```sql
-- 캐시 적중/미적중 분석
SELECT x_edge_cache_status, COUNT(*) AS cnt,
       AVG(time_taken) AS avg_time_taken
FROM cloudfront_logs
WHERE date >= current_date - interval '1' day
GROUP BY x_edge_cache_status
ORDER BY cnt DESC;
```

```sql
-- OriginLatency 상위 (원본 지연)
SELECT cs_uri_stem, origin_fbl, time_taken
FROM cloudfront_logs
WHERE date >= current_date - interval '1' day
  AND sc_status >= 500
ORDER BY origin_fbl DESC
LIMIT 50;
```

#### CloudWatch Metrics

| 메트릭 | 네임스페이스 | 통계 | 의미 |
|--------|-------------|------|------|
| `CacheHitRate` | `AWS/CloudFront` | `Average` | 캐시 적중률 (%) |
| `OriginLatency` | `AWS/CloudFront` | `p95`, `p99` | 원본 응답 지연 |
| `4xxErrorRate` | `AWS/CloudFront` | `Average` | 클라이언트 에러율 |
| `5xxErrorRate` | `AWS/CloudFront` | `Average` | 서버/원본 에러율 |
| `Requests` | `AWS/CloudFront` | `Sum` | 총 요청 수 |

#### 해석 가이드

| 패턴 | 의미 | 다음 단계 |
|------|------|----------|
| 5xx + `OriginLatency` 높음 | 원본 서버 문제 | 원본(ALB/S3/Lambda) 로그 확인 |
| 5xx + `OriginLatency` 낮음 | 에지에서 발생한 에러 | WAF/Geo 제한/서명 URL 정책 확인 |
| `CacheHitRate` 급감 | 캐시 미스 급증 | `Cache-Control` 헤더, TTL 설정 확인 |
| 특정 국가/경로에 403 집중 | Geo/WAF 정책 불일치 | WAF 규칙 + Geo Restriction 확인 |

---

### 3.7 S3 Access Denied (403)

#### 봐야 할 로그·신호

| 순서 | 신호 | 위치 | 조회 방법 |
|------|------|------|----------|
| **1** | 호출자 identity 확인 | STS API | `aws sts get-caller-identity` |
| **2** | CloudTrail S3 이벤트 | CloudTrail (S3 또는 API) | CloudTrail API 또는 Athena |
| **3** | IAM Policy 평가 | IAM API | `aws iam simulate-principal-policy` |
| **4** | Bucket Policy | S3 API | `aws s3api get-bucket-policy` |
| **5** | KMS Key Policy (암호화 시) | KMS API | `aws kms get-key-policy` |
| **6** | S3 Server Access Logs | **S3 버킷** (활성화 시) | S3 → Athena |

#### CloudTrail 쿼리 (S3 AccessDenied)

```sql
-- CloudTrail S3 AccessDenied 이벤트
fields @timestamp, eventName, errorCode, userIdentity.arn as principal,
       requestParameters.bucketName as bucket,
       requestParameters.key as objectKey,
       sourceIPAddress
| filter eventSource = "s3.amazonaws.com" and errorCode like /AccessDenied/
| sort @timestamp desc
| limit 200
```

#### 정책 평가 체인 (순서대로 확인)

```
1. IAM Identity Policy → 명시적 Allow 있는가?
2. Permissions Boundary → 허용 범위 내인가?
3. SCP (Organizations) → 계정 레벨에서 차단?
4. RCP (Organizations) → 리소스 레벨 제한?
5. Bucket Policy → 명시적 Deny? Cross-account 허용?
6. Object Ownership / ACL → 객체 소유자가 다른가?
7. VPC Endpoint Policy → 엔드포인트에서 차단?
8. Access Point Policy → 액세스 포인트 정책?
9. KMS Key Policy → 암호화된 객체 복호화 권한?
10. Session Policy (AssumeRole) → 세션 정책에서 제한?
```

#### CLI로 확인

```bash
# 호출자 identity
aws sts get-caller-identity

# Bucket Policy
aws s3api get-bucket-policy --bucket <BUCKET>

# IAM Policy 시뮬레이션
aws iam simulate-principal-policy \
  --policy-source-arn <ROLE_ARN> \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::<BUCKET>/<KEY>

# KMS Key Policy (암호화된 경우)
aws kms get-key-policy --key-id <KEY_ID> --policy-name default

# S3 Object Ownership
aws s3api get-bucket-ownership-controls --bucket <BUCKET>
```

#### 해석 가이드

| 패턴 | 의미 | 다음 단계 |
|------|------|----------|
| IAM Policy에 s3:GetObject 없음 | IAM 권한 누락 | IAM Policy에 Action 추가 |
| Bucket Policy에 명시적 Deny | 의도적 또는 실수 차단 | Deny 조건 검토 |
| Cross-account + 한쪽만 허용 | 양쪽 모두 허용 필요 | Bucket Policy + IAM Policy 양쪽 수정 |
| KMS Key Policy에 복호화 권한 없음 | KMS 암호화된 객체 접근 불가 | Key Policy에 kms:Decrypt 권한 추가 |
| AssumeRole session policy 제한 | 세션 생성 시 제한 | Trust Policy + Session Policy 확인 |

---

## 4. 교차 서비스 상관 관계

### 4.1 공통 상관 키

여러 서비스의 로그를 연결할 때 사용하는 키:

| 상황 | 키 | 포함된 로그 |
|------|-----|------------|
| API Gateway → Lambda | `x-amzn-requestid` / `requestId` | API GW Access Logs + Lambda Logs |
| 전체 요청 추적 | `traceId` / `@traceId` | X-Ray + 모든 서비스 로그 (활성화 시) |
| 보안 감사 | `principal ARN` | CloudTrail + 모든 서비스 로그 |
| 네트워크 경로 | `source IP` + `destination IP:Port` | VPC Flow Logs + WAF + ALB Logs |
| ECS 태스크 추적 | `taskArn` | ECS Events + Container Logs |

### 4.2 CloudWatch Logs Insights 교차 쿼리

```sql
-- 여러 로그 그룹에서 동시 검색 (CLI/API에서 SOURCE 사용)
SOURCE logGroups(accountIdentifiers:['111122223333'],
  namePrefix:['/aws/lambda/','API-Gateway-Execution-Logs_'])
| filter @message like /ERROR|Exception|Timeout/
| stats count(*) by @log, bin(5m)
```

### 4.3 Contributor Insights (Top Talkers 분석)

장애 시 어떤 IP, 사용자, 경로가 가장 많이 실패하는지 빠르게 파악:

```json
{
  "Schema": "CloudWatchContributorInsightsRule",
  "LogGroupNames": ["/aws/lambda/my-function"],
  "Contributor": { "Dimensions": [["@requestId"]], "ValueField": "@duration" },
  "AggregateOn": "Sum"
}
```

### 4.4 시간 비교 쿼리 (diff)

장애 발생 전후를 비교하여 새로운 패턴을 발견:

```sql
-- 장애 기간과 정상 기간 비교
diff @message
| filter @message like /ERROR/
| stats count(*) as errorCount by bin(5m)
```

---

## 5. AWS X-Ray 분산 추적 활용

### 5.1 장애 조사 워크플로우

```
1. GetTraceSummaries → 장애 시간 창의 폴트/에러/쓰로틀 트레이스 목록
2. BatchGetTraces → 특정 트레이스의 전체 세그먼트 상세
3. 서비스 맵에서 에지(Edge) 색상 확인:
   - 빨강: fault (5xx)
   - 노랑: error (4xx)
   - 보라: throttle
   - 녹색: 정상
```

### 5.2 필터 표현식 예시

```
# 특정 서비스의 폴트/에러
service("api-gateway") { fault = true OR error = true }

# 특정 환경의 느린 요청
annotation.env = "prod" AND duration > 1

# 두 서비스 간 지연
edge("api-gateway", "lambda").duration > 0.5

# 특정 상태 코드
http.status_code >= 500
```

### 5.3 샘플링 주의사항

| 상황 | 문제 | 대응 |
|------|------|------|
| 낮은 트래픽 서비스 | 기본 샘플링이 버스트를 놓칠 수 있음 | 장애 시 샘플링 비율 일시 상향 |
| Parent-based 샘플링 | 상위 서비스가 샘플링되지 않으면 하위도 추적 안 됨 | critical path는 고비율 유지 |
| 장애 발생 직후 | 샘플링된 데이터만으로 전체 파악 어려웅 | 메트릭(전수) + 트레이스(샘플) 병행 |

### 5.4 CLI로 조회

```bash
# 폴트/에러 트레이스 요약
aws xray get-trace-summaries \
  --start-time "2026-04-03T00:00:00Z" \
  --end-time "2026-04-03T00:15:00Z" \
  --filter-expression 'fault = true OR error = true'

# 특정 트레이스 전체 상세
aws xray batch-get-traces \
  --trace-ids "1-6604a3a0-xxxxxxxxxxxxxxxxxxxxxxxx"
```

---

## 6. AWS Health + EventBridge 통합

### 6.1 AWS Health API로 서비스 장애 확인

장애 원인이 AWS 플랫폼 자체인지 먼저 배제:

```bash
# 활성 AWS Health 이벤트 조회
aws health describe-events \
  --filter '{"services":["LAMBDA","ECS","RDS","S3","EC2","CLOUDFRONT"],
             "eventStatusCodes":["open","upcoming"]}'

# 영향받는 리소스 확인
aws health describe-affected-entities \
  --filter '{"eventArns":["arn:aws:health:ap-northeast-2::event/..."]}'
```

### 6.2 EventBridge 자동 라우팅

```json
{
  "source": ["aws.health"],
  "detail-type": ["AWS Health Event"],
  "detail": {
    "service": ["LAMBDA"],
    "eventTypeCategory": ["issue"],
    "eventScopeCode": ["ACCOUNT_SPECIFIC"]
  }
}
```

---

## 7. CloudWatch 알람 패턴

### 7.1 장애 탐지용 표준 알람

| 서비스 | 알람 | 메트릭 | 조건 |
|--------|------|--------|------|
| Lambda | 타임아웃 | `Duration p95` | > timeout × 0.8 |
| Lambda | 쓰로틀링 | `Throttles Sum` | > 0, 2분 연속 |
| Lambda | 에러율 | `Errors / Invocations` | > 1% |
| API Gateway | 5xx | `5XXError Sum` | > 0 |
| ECS | 크래시 | `RunningTaskCount Min` | < desired × 0.5 |
| RDS | CPU | `CPUUtilization Average` | > 80%, 5분 연속 |
| RDS | 스토리지 | `FreeStorageSpace Minimum` | < 10GB |
| ALB | 비정상 타겟 | `UnHealthyHostCount Max` | > 0 |
| SQS | 처리 지연 | `ApproximateAgeOfOldestMessage Max` | > 300초 |
| DynamoDB | 쓰로틀링 | `ThrottledRequests Sum` | > 0 |

### 7.2 복합 알람 (Composite Alarms)

```bash
# API 5xx + Lambda 에러 동시 발생 시 알람
aws cloudwatch put-composite-alarm \
  --alarm-name "api-backend-degradation" \
  --alarm-rule 'ALARM("api-5xx") AND ALARM("lambda-errors")' \
  --alarm-description "API 5xx and Lambda errors correlated"
```

```bash
# ALB 지연 + RDS 지연 상관
aws cloudwatch put-composite-alarm \
  --alarm-name "backend-db-degradation" \
  --alarm-rule 'ALARM("alb-target-latency-p95") AND ALARM("rds-read-latency")'
```

---

## 8. 증거 보존 및 감사

### 8.1 장애 발생 시 최우선 수집 항목

```
1순위: CloudTrail Management Events (누가 무엇을 언제 변경했는가)
2순위: 서비스 로그 (CloudWatch Logs - 타임아웃 시에 로그가 사라질 수 있음)
3순위: 메트릭 스냅샷 (CloudWatch 데이터는 15개월 보존)
4순위: VPC Flow Logs (보안 사건 시)
5순위: 트레이스 데이터 (X-Ray, 30일 보존)
```

### 8.2 보안 사건 시 주의사항

```bash
# EC2 침해 의심 시: 볼륨 스냅샷 (종료 방지)
aws ec2 create-snapshots --instance-specification InstanceId=<INSTANCE_ID>
aws ec2 modify-instance-attribute --instance-id <INSTANCE_ID> --no-disable-api-termination

# IAM 크리덴셜 침해 시: 즉시 비활성화
aws iam delete-access-key --access-key-id <KEY_ID> --user-name <USER>
aws iam delete-login-profile --user-name <USER>

# CloudTrail에서 해당 크리덴셜 사용 중지 확인 (비활성화 후에도 로그 확인)
aws cloudtrail lookup-events --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=<KEY_ID>
```

---

## 9. 요약: 장애 시나리오별 "첫 15분" 조사 체크리스트

### Lambda 타임아웃/쓰로틀링
- [ ] CW Logs Insights: `Status: timeout` 쿼리
- [ ] CW Metrics: Duration p95, Throttles, ConcurrentExecutions
- [ ] Lambda 설정: timeout, memory, concurrency 확인
- [ ] X-Ray: 하위 서비스 지연 확인

### RDS 성능 저하
- [ ] CW Metrics: CPU, FreeStorageSpace, DatabaseConnections, ReadLatency
- [ ] CW Logs: Slow Query Log에서 장시간 쿼리
- [ ] RDS Error Log에서 FATAL/PANIC/ERROR
- [ ] Performance Insights (활성화 시): 상위 SQL

### API Gateway 5xx
- [ ] CW Metrics: 5XXError, Latency, IntegrationLatency
- [ ] CW Logs: status >= 500 요청 필터링
- [ ] IntegrationLatency로 API GW vs 백엔드 구분
- [ ] 백엔드(Lambda/ECS) 로그로 원인 추적

### ECS 태스크 실패
- [ ] `aws ecs describe-tasks`: stoppedReason + exitCode
- [ ] `aws ecs describe-services`: 서비스 이벤트
- [ ] CW Logs: CannotPullContainer, OOMKilled, health check
- [ ] CW Metrics: RunningTaskCount, MemoryUtilization

### VPC 네트워크 장애
- [ ] Reachability Analyzer 실행
- [ ] VPC Flow Logs: REJECT 패턴 분석
- [ ] Route Table / SG / NACL 확인
- [ ] NAT Gateway 메트릭: ErrorPortAllocation

### CloudFront 에러/지연
- [ ] CW Metrics: 5xxErrorRate, OriginLatency, CacheHitRate
- [ ] Athena: Access Logs에서 sc_status >= 400
- [ ] X-Cache 상태로 캐시 동작 확인
- [ ] 원본 서버 로그 확인

### S3 Access Denied
- [ ] `aws sts get-caller-identity`: 실제 호출자 확인
- [ ] CloudTrail: S3 AccessDenied 이벤트
- [ ] IAM → Bucket Policy → KMS → SCP 정책 체인 확인
- [ ] Cross-account인 경우 양쪽 정책 모두 확인

---

## 10. 참고 자료

### AWS 공식 문서

- [CloudWatch Logs Insights 쿼리 구문](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax.html)
- [CloudWatch Logs Insights 쿼리 예제](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-examples.html)
- [CloudWatch Logs Insights SOURCE 구문](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-Source.html)
- [CloudWatch Logs Insights FilterIndex](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_QuerySyntax-FilterIndex.html)
- [CloudWatch Logs diff 비교](https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/CWL_AnalyzeLogData_Compare.html)
- [CloudWatch Contributor Insights](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/ContributorInsights.html)
- [Lambda 모니터링 메트릭](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics-types.html)
- [API Gateway 메트릭](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-metrics-and-dimensions.html)
- [ECS 메트릭](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/available-metrics.html)
- [RDS 메트릭](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/rds-metrics.html)
- [DynamoDB 메트릭](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/metrics-dimensions.html)
- [ALB 메트릭](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html)
- [CloudFront 메트릭](https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/programming-cloudwatch-metrics.html)
- [S3 메트릭](https://docs.aws.amazon.com/AmazonS3/latest/userguide/metrics-dimensions.html)
- [SQS 메트릭](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-available-cloudwatch-metrics.html)
- [VPC Flow Log 레코드](https://docs.aws.amazon.com/vpc/latest/userguide/flow-log-records.html)
- [VPC Flow Log 예제](https://docs.aws.amazon.com/vpc/latest/userguide/flow-logs-records-examples.html)
- [Athena VPC Flow Logs 테이블](https://docs.aws.amazon.com/athena/latest/ug/vpc-flow-logs-create-table-statement.html)
- [NAT Gateway 메트릭](https://docs.aws.amazon.com/vpc/latest/userguide/metrics-dimensions-nat-gateway.html)
- [EC2 ENA 네트워크 성능](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/monitoring-network-performance-ena.html)
- [X-Ray GetTraceSummaries API](https://docs.aws.amazon.com/xray/latest/api/API_GetTraceSummaries.html)
- [X-Ray BatchGetTraces API](https://docs.aws.amazon.com/xray/latest/api/API_BatchGetTraces.html)
- [X-Ray 필터 표현식](https://docs.aws.amazon.com/xray/latest/devguide/xray-console-filters.html)
- [X-Ray 샘플링](https://docs.aws.amazon.com/xray/latest/devguide/xray-console-sampling.html)
- [AWS Health DescribeEvents API](https://docs.aws.amazon.com/health/latest/APIReference/API_DescribeEvents.html)
- [AWS Health EventBridge 스키마](https://docs.aws.amazon.com/health/latest/ug/aws-health-events-eventbridge-schema.html)
- [Container Insights ECS 메트릭](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-ECS.html)
- [Container Insights EKS 메트릭](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Container-Insights-metrics-EKS.html)
- [Application Signals 메트릭](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AppSignals-MetricsCollected.html)
- [CloudWatch 알람 Best Practices](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Best_Practice_Recommended_Alarms_AWS_Services.html)
- [CloudWatch Anomaly Detection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/CloudWatch_Anomaly_Detection.html)

### AWS re:Post Knowledge Center

- [Lambda 함수 장애 조사](https://repost.aws/knowledge-center/lambda-troubleshoot-function-failures)
- [Lambda 타임아웃 확인](https://repost.aws/knowledge-center/lambda-verify-invocation-timeouts)
- [Lambda 쓰로틀링 조사](https://repost.aws/knowledge-center/lambda-troubleshoot-throttling)
- [API Gateway 5xx 에러](https://repost.aws/knowledge-center/api-gateway-5xx-error)
- [API Gateway CloudWatch Logs](https://repost.aws/knowledge-center/api-gateway-errors-cloudwatch-logs)
- [ECS 태스크 중지](https://repost.aws/knowledge-center/ecs-task-stopped)
- [ECS 배포 실패](https://repost.aws/knowledge-center/ecs-troubleshoot-deployment-failures)
- [VPC 네트워크 연결 조사](https://repost.aws/knowledge-center/vpc-troubleshoot-network-connectivity)
- [CloudFront 로깅](https://repost.aws/knowledge-center/cloudfront-logging-requests)
- [CloudFront 지연 조사](https://repost.aws/knowledge-center/cloudfront-troubleshoot-latency)
- [CloudFront 403 에러](https://repost.aws/knowledge-center/cloudfront-troubleshoot-403-errors)
- [S3 403 AccessDenied 조사](https://repost.aws/knowledge-center/s3-troubleshoot-403)
- [RDS PostgreSQL CloudWatch Logs 분석](https://repost.aws/knowledge-center/analyze-cloudwatch-logs-rds-postgresql)

### AWS Prescriptive Guidance

- [CloudWatch 로깅/모니터링 구현](https://docs.aws.amazon.com/prescriptive-guidance/latest/implementing-logging-monitoring-cloudwatch/welcome.html)
- [CloudWatch 검색 및 분석](https://docs.aws.amazon.com/prescriptive-guidance/latest/implementing-logging-monitoring-cloudwatch/cloudwatch-search-analysis.html)
- [애플리케이션 로깅 Best Practices](https://docs.aws.amazon.com/prescriptive-guidance/latest/logging-monitoring-for-application-owners/logging-best-practices.html)
- [이벤트 속성 가이드](https://docs.aws.amazon.com/prescriptive-guidance/latest/logging-monitoring-for-application-owners/event-attributes.html)

### AWS Well-Architected

- [Operational Excellence - 관측성 구현](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/implement-observability.html)
- [애플리케이션 원격 측정](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_observability_application_telemetry.html)
- [워크로드 로그 분석](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_workload_observability_analyze_workload_logs.html)
- [워크로드 추적 분석](https://docs.aws.amazon.com/wellarchitected/latest/operational-excellence-pillar/ops_workload_observability_analyze_workload_traces.html)

### GitHub

- [AWS Incident Response Playbooks (aws-samples)](https://github.com/aws-samples/aws-incident-response-playbooks)
- [AWS Customer Playbook Framework (aws-samples)](https://github.com/aws-samples/aws-customer-playbook-framework)
