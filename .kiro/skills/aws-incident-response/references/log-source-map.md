# AWS Service Log Source Map

> Agent가 장애 조사 시 참조하는 서비스별 로그/메트릭/이벤트 조회 룩업 테이블
> 원본: docs/research/06-aws-incident-log-reference.md

---

## 1. CloudWatch Logs에 있는 로그 (CW Logs Insights로 조회)

| 서비스 | 로그 그룹 | 활성화 | 주요 쿼리 |
|--------|----------|--------|----------|
| **Lambda** | `/aws/lambda/<함수명>` | 기본 | `filter @message like "Task timed out"` |
| **API Gateway** | `API-Gateway-Execution-Logs_<API_ID>/<Stage>` | Stage 설정 | `filter status >= 500` |
| **ECS/Fargate** | `/ecs/<태스크정의명>` | Task Definition logConfiguration | `filter @message like /OOMKilled/` |
| **RDS Error** | `/aws/rds/instance/<인스턴스명>/error` | 파라미터 그룹 + CW 내보내기 | `filter @message like /FATAL\|PANIC/` |
| **RDS Slow Query** | `/aws/rds/instance/<인스턴스명>/slowquery` | 파라미터 그룹 | `parse @message /duration: (?<duration>.*?) ms/` |
| **VPC Flow Logs** | `/aws/vpc/flow-logs/<VPC_NAME>` (선택) | VPC 설정 | `filter action = "REJECT"` |
| **WAF** | (선택 CW Logs) | Web ACL 설정 | 서비스별 |

## 2. S3에 있는 로그 (Athena로 조회)

| 서비스 | 로그 위치 | 활성화 | 조회 방법 |
|--------|----------|--------|----------|
| **ALB/NLB Access Logs** | S3 버킷 (지정 경로) | LB 속성 | S3 → Athena |
| **CloudFront Standard Logs** | S3 버킷 | Distribution 설정 | S3 → Athena |
| **S3 Server Access Logs** | S3 버킷 (다른 버킷) | 버킷 속성 | S3 → Athena |
| **CloudTrail Events** | S3 + CW Logs (선택) | Trail 생성 | Athena 또는 CloudTrail API |

## 3. API로만 조회 (CloudWatch Logs가 아님)

| 서비스 | 조회 방법 | 보존 기간 |
|--------|----------|----------|
| **ECS 서비스 이벤트** | `aws ecs describe-services` | 90일 |
| **ECS 태스크 중지 사유** | `aws ecs describe-tasks` | 90일 |
| **AWS Health 이벤트** | `aws health describe-events` | 90일 |
| **CloudTrail 이벤트** | CloudTrail API 또는 Athena | 90일 (LookupEvents) |
| **X-Ray 트레이스** | X-Ray API | 30일 |

## 4. 서비스별 주요 CloudWatch Metrics

### Lambda
| 메트릭 | 통계 | 임계값 |
|--------|------|--------|
| `Duration` | p95, p99 | > timeout × 0.8 |
| `Errors` | Sum | > 0 |
| `Throttles` | Sum | > 0 |
| `ConcurrentExecutions` | Max | ≈ Account Quota |
| `Invocations` | Sum | 트래픽 확인 |
| `IteratorAge` | Max | 급증 = 처리 지연 |

### RDS
| 메트릭 | 통계 | 임계값 |
|--------|------|--------|
| `CPUUtilization` | Average | > 80% |
| `FreeStorageSpace` | Minimum | < 10GB |
| `DatabaseConnections` | Max | > max_connections × 0.8 |
| `ReadLatency` / `WriteLatency` | p99 | > 50ms |
| `FreeableMemory` | Minimum | < 512MB |
| `DiskQueueDepth` | Average | > 10 |

### ECS
| 메트릭 | 통계 | 의미 |
|--------|------|------|
| `CPUUtilization` | Average | CPU 병목 |
| `MemoryUtilization` | Average | 메모리 압박 |
| `RunningTaskCount` | Average | 급감 = 크래시 |
| `RestartCount` (ContainerInsights) | Sum | 크래시 루프 |

### API Gateway
| 메트릭 | 통계 | 임계값 |
|--------|------|--------|
| `5XXError` | Sum | > 0 |
| `4XXError` | Sum | 트렌드 비교 |
| `Latency` | p95 | > SLA |
| `IntegrationLatency` | p95 | 백엔드 병목 지표 |

### DynamoDB
| 메트릭 | 통계 | 임계값 |
|--------|------|--------|
| `ThrottledRequests` | Sum | > 0 |
| `ConsumedReadCapacityUnits` | Sum | 프로비저닝 대비 |
| `ConsumedWriteCapacityUnits` | Sum | 프로비저닝 대비 |

### CloudFront
| 메트릭 | 통계 | 의미 |
|--------|------|------|
| `CacheHitRate` | Average | 캐시 적중률 |
| `OriginLatency` | p95 | 원본 응답 지연 |
| `5xxErrorRate` | Average | 서버 에러율 |
| `4xxErrorRate` | Average | 클라이언트 에러율 |

### 네트워크
| 메트릭 | 네임스페이스 | 의미 |
|--------|-------------|------|
| `ErrorPortAllocation` | AWS/NATGateway | NAT 포트 고갈 |
| `PacketsDropCount` | AWS/NATGateway | NAT 패킷 드롭 |
| `conntrack_allowance_exceeded` | AWS/EC2 (ENA) | 연결 추적 한계 |

## 5. 교차 서비스 상관 키

| 상황 | 키 | 포함된 로그 |
|------|-----|------------|
| API Gateway → Lambda | `x-amzn-requestid` / `requestId` | API GW + Lambda Logs |
| 전체 요청 추적 | `traceId` / `@traceId` | X-Ray + 모든 서비스 |
| 보안 감사 | `principal ARN` | CloudTrail + 모든 서비스 |
| 네트워크 경로 | `source IP` + `destination IP:Port` | VPC Flow Logs + WAF + ALB |
| ECS 태스크 추적 | `taskArn` | ECS Events + Container Logs |

## 6. 장애 조사 공통 순서

```
Step 1: 시간 창 확정 (UTC 기준, T-15m ~ T+15m → 증거에 따라 확장)
Step 2: 상관 키 확보 (requestId, traceId, principal ARN, source IP)
Step 3: 제어면(CloudTrail) + 데이터면(서비스 로그) 동시 수집
Step 4: 보안 사건인 경우 증거 보존 먼저 (스냅샷, 변경 금지)
Step 5: 서비스별 심층 조사 (위 테이블 참조)
```

## 7. AWS Health + EventBridge

```bash
# 활성 AWS Health 이벤트 조회
aws health describe-events \
  --filter '{"services":["LAMBDA","ECS","RDS","S3","EC2","CLOUDFRONT"],
             "eventStatusCodes":["open","upcoming"]}'

# 영향받는 리소스 확인
aws health describe-affected-entities \
  --filter '{"eventArns":["arn:aws:health:..."]}'
```
