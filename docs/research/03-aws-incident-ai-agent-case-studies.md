# AWS 장애 상황 AI Agent 해결 전세계 사례 조사

> 조사일: 2026-04-02
> 목적: AI Agent가 AWS 장애 상황을 해결한 전세계 실제 사례 및 도구/플랫폼 조사

---

## 1. AWS 장애 유형 및 일반적 장애 시나리오

### 1.1 장애 분류

| 카테고리 | 장애 유형 | 빈도 | AI 대응 적합성 |
|----------|-----------|------|----------------|
| **서비스 장애** | 리전 장애, AZ 장애, 서비스 중단 | 낮음/높음 | 높음 |
| **인프라 장애** | EC2 크래시, RDS 페일오버, Lambda 쓰로틀링 | 높음 | 매우 높음 |
| **네트워크** | VPC 오설정, Security Group 이슈, DNS 장애 | 중간 | 높음 |
| **비용 이상** | 리소스 과다 사용, 스토리지 비용 급증 | 중간 | 높음 |
| **보안** | IAM 정책 이슈, S3 버킷 노출, 인증 장애 | 낮음 | 매우 높음 |
| **애플리케이션** | 배포 실패, 메모리 누수, 타임아웃 | 높음 | 매우 높음 |

### 1.2 일반적 장애 패턴

```
1. 배포 후 장애: 새 코드 배포 → 서비스 에러율 급증
2. 리소스 한계: 트래픽 증가 → Lambda 쓰로틀링 / DynamoDB 제한
3. 설정 변경: IAM/S3/SG 변경 → 접근 불가
4. 의존성 장애:下游 서비스 장애 → 전파
5. 비용 폭발: 리소스 누락 → 예산 초과
```

---

## 2. 글로벌 AI Agent 장애 해결 플랫폼

### 2.1 AWS DevOps Agent (2026년 3월 출시)

**AWS가 직접 개발한 Agentic SRE 솔루션**

#### 핵심 아키텍처: "6C"

| C | 설명 | 기능 |
|---|------|------|
| **Context** | 애플리케이션 토폴로지 자동 구성 | Agent Spaces → 리소스 발견 → 의존성 매핑 |
| **Control** | 거버넌스 및 접근 제어 | IAM 권한, Audit Trail, Agent Space 격리 |
| **Convenience** | 제로 셋업 팀 접근 | 관리자 1회 설정 → 팀원 즉시 사용 |
| **Collaboration** | 자율적 팀 협업 | Slack 알림, ServiceNow 연동, 자동 조사 |
| **Continuous Learning** | 3-tier Skill 학습 | AWS Skill → 사용자 정의 Skill → 학습된 Skill |
| **Cost Effective** | 사용량 기반 과금 | 활성 작업 시간만 과금 |

#### 실제 사례: URL Shortener 장애 조사

```
시나리오: CloudWatch 알람 → 5xx 에러율 급증

AWS DevOps Agent 자율 조사 (4분 소요):
1. CloudFront → API Gateway → Lambda → DynamoDB 토폴로지 자동 추적
2. 가설: "Lambda 콜드 스타트? DynamoDB 쓰로틀링? API Gateway 타임아웃?"
3. CloudWatch 메트릭 → DynamoDB ConsumedWriteCapacityUnits 확인
4. 47분 전 배포된 커밋과 연관성 발견 (batch DynamoDB write 추가)
5. 근본 원인: DynamoDB Write Throttling by recent deployment
6. Slack으로 완전한 RCA 전송 + 완화 제안 (on-demand capacity 또는 rollback)
```

#### 성과 지표

| 지표 | 수치 |
|------|------|
| MTTR 감소 | 최대 75% |
| 조사 속도 | 80% 향상 |
| 근본 원인 정확도 | 94% |
| 인시던트 해결 속도 | 3-5x |

#### 고객 사례

**Western Governor's University (WGU)**
- 온라인 대학, 191,000+ 학생
- Dynatrace 통합 → 자동 Problem Record 라우팅
- 결과: MTTR 2시간 → 28분 (77% 개선)
- Lambda 함수 설정 오류 자동 발견

**Zenchef**
- 레스토랑 기술 플랫폼
- API 연동 이슈 자동 조사
- 인증 제외 → ECS 배포 집중 → 코드 리그레션 발견
- 결과: 1-2시간 → 20-30분 (75% 감소)

---

### 2.2 Datadog Bits AI SRE (2026년 1월)

**Datadog의 AI SRE Agent**

#### 특징

| 기능 | 설명 |
|------|------|
| **인과관계 분석** | 노이즈가 아닌 원인에 집중 |
| **다중 컴포넌트 조사** | 여러 서비스에 걸친 장애 분석 |
| **실제 인시던트 벤치마크** | 수백 개의 실제 장애 데이터로 학습 |
| **가설-테스트 패턴** | 인간 SRE처럼 가설 세우고 텔레메트리로 검증 |

#### 작동 원리

```
장애 발생 → 컨텍스트 수집 → 가설 형성 → 텔레메트리로 테스트
    → 유망한 증거 추적 → 근본 원인 분석 (RCA)
```

#### 성과
- **Time to Resolution 최대 95% 감소**
- 실제 Datadog 내부 인시던트 수백 건으로 벤치마크
- LLM Judge가 Agent 결론을 다기준으로 평가

---

### 2.3 OpsWorker (2026년 1월)

**Kubernetes/AWS 기반 AI SRE 플랫폼**

#### 아키텍처

```
AlertManager/Datadog/CloudWatch → API Gateway → SQS → Lambda
    → EventBridge → AI Agent Graph (Bedrock) → Slack 알림

모델 전략:
- Claude Sonnet: 복잡한 추론 및 RCA
- Amazon Nova: 빠른 추출 작업
- Claude Haiku: 저지연 채팅
```

#### 특징
- **100% 서버리스**: API Gateway + SQS + Lambda + DynamoDB
- **1분 이내 조사 완료**: 알림 → 자동 조사 → Slack 알림
- **Human-in-the-Loop**: 채팅으로 후속 질문 가능
- **피드백 루프**: Slack에서 분석 품질 피드백 → 모델 개선

---

### 2.4 PagerDuty AIOps + AWS 통합

**PagerDuty와 AWS의 AI Agent 통합**

| 기능 | 설명 |
|------|------|
| **AI Agent Integration** | PagerDuty AI Agent가 AWS 리소스에 직접 접근 |
| **자동 인시던트 라우팅** | AWS 알람 → PagerDuty → AI 분석 → 담당자 할당 |
| **Intelligent Alert Grouping** | 관련 알람 자동 그룹화 (노이즈 감소) |
| **Auto-Remediation** | 사전 정의된 Runbook 자동 실행 |

---

### 2.5 기타 주요 플랫폼

| 플랫폼 | 주요 기능 | AWS 통합 |
|--------|-----------|----------|
| **Dynatrace Davis AI** | 자동 근본 원인 분석, 스마트 알림 | AWS 통합 모니터링 |
| **New Relic AI** | AI-driven anomaly detection, Proactive Alerts | AWS CloudWatch 연동 |
| **Splunk ITSI** | AI 기반 서비스 인텔리전스 | AWS 데이터 수집 |
| **Grafana AI** | 예측적 알림, 자동 대시보드 | Amazon Managed Grafana |
| **AWS DevOps Guru** | ML 기반 운영 insight, anomaly detection | AWS 네이티브 |

---

## 3. AI Agent 장애 대응 아키텍처

### 3.1 Detection → Diagnosis → Remediation 파이프라인

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Detection    │ ──▶ │  Diagnosis   │ ──▶ │  Remediation │
│  (감지)       │     │  (진단)       │     │  (복구)       │
└──────────────┘     └──────────────┘     └──────────────┘
     │                     │                     │
     ▼                     ▼                     ▼
 CloudWatch Alarm     AI Agent 조사        자동/수동 조치
 EventBridge          토폴로지 추적         Runbook 실행
 PagerDuty Alert      로그 분석            Scale out/in
 Datadog Monitor      메트릭 상관관계       Rollback 배포
                      코드 변경 연관        장애 격리
```

### 3.2 Multi-Agent 시스템 (복잡한 장애)

```
┌─────────────┐
│ Orchestrator │  ← 장애 조사 총괄
│ Agent        │
└──────┬──────┘
       │
  ┌────┼────┐
  ▼    ▼    ▼
┌───┐┌───┐┌───┐
│Infra││App ││Sec │  ← 전문 Agent
│Agent││Agent││Agent│
└───┘└───┘└───┘
```

**Nitish Agarwal 연구에 따르면** Multi-Agent SRE 시스템은 MTTR을 최대 40% 감소시킬 수 있다.

### 3.3 Human-in-the-Loop 패턴

```
AI Agent 자율 조사 (80%)
    → 결과를 인간에게 제시
    → 인간이 판단하여 승인/수정 (20%)
    → AI가 실행
```

---

## 4. 기술 및 프레임워크

### 4.1 LangChain/LlamaIndex를 활용한 AWS 장애 관리

```python
# 개념적 구현
from langchain.agents import AgentExecutor
from langchain.tools import Tool

# AWS 도구 정의
tools = [
    Tool(name="cloudwatch_logs", func=query_cloudwatch_logs),
    Tool(name="ec2_describe", func=describe_ec2_instances),
    Tool(name="lambda_errors", func=get_lambda_errors),
    Tool(name="rds_metrics", func=get_rds_metrics),
    Tool(name="deploy_rollback", func=rollback_deployment),
]

# Agent 실행
agent = AgentExecutor(
    agent=agent,
    tools=tools,
    verbose=True,
    # 안전 가드레일
    max_iterations=10,
    early_stopping_method="generate",
)
```

### 4.2 RAG (Retrieval Augmented Generation) with AWS

```
AWS 문서 + Runbook + 과거 장애 기록
    → Vector Store (Bedrock Knowledge Base)
    → RAG로 검색
    → AI Agent가 컨텍스트와 함께 장애 분석
```

### 4.3 Function Calling / Tool Use 패턴

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "query_cloudwatch",
        "description": "CloudWatch 로그 쿼리",
        "parameters": {
          "log_group": "/aws/lambda/my-function",
          "query": "fields @timestamp, @message | filter @message like /ERROR/",
          "start_time": "-30m"
        }
      }
    }
  ]
}
```

---

## 5. AWS 자격증 시험 기반 장애 대응 시나리오 (AI Agent Runbook)

> AWS Associate/Pro 시험에 출제되는 장애 대응 패턴을 정리한 것으로,
> AI Agent가 장애 대응 시 "검증된 베스트 프랙티스"로 참조 가능

### 5.1 EC2 응답 불가 (Instance Unreachable)

```
증상: EC2 인스턴스가 응답하지 않음, SSH 연결 불가

진단 순서:
1. AWS 콘솔 → EC2 → Status Check 확인
   - System Status Check 실패 → AWS 인프라 이슈 (자동 복구 대기)
   - Instance Status Check 실패 → OS/애플리케이션 이슈
2. System Log (console output) 확인
3. 최근 변경 사항 확인 (배포, 설정 변경)

해결:
├─ Status Check 실패 (AWS 이슈)
│   → Auto Recovery 활성화된 인스턴스: 자동 복구 대기
│   → 미활성화: 수동으로 인스턴스 재부팅 또는 교체
├─ OS 레벨 장애
│   → Session Manager 연결 시도 (SSH 불가해도 SSM은 가능할 수 있음)
│   → 인스턴스 재부팅
│   → AMI에서 새 인스턴스 시작
└─ 애플리케이션 장애
    → ELB Health Check 실패 → 자동 교체 (Auto Scaling)
    → CodeDeploy/Elastic Beanstalk 롤백
```

### 5.2 RDS 성능 저하 (Database Performance Degradation)

```
증상: 쿼리 응답 시간 증가, 애플리케이션 타임아웃

진단 순서:
1. CloudWatch → RDS 메트릭 확인
   - CPUUtilization, FreeStorageSpace, DatabaseConnections
   - ReadIOPS/WriteIOPS, ReadLatency/WriteLatency
2. Enhanced Monitoring 활성화 확인
3. Performance Insights로 슬로우 쿼리 식별
4. PGAutoFix 또는 수동 파라미터 조정 필요성 확인

해결:
├─ CPU/메모리 병목
│   → 인스턴스 클래스 업그레이드 (스케일 업)
│   → Multi-AZ 페일오버 (보조 인스턴스로 전환)
├─ I/O 병목 (스토리지)
│   → 스토리지 자동 확장 활성화
│   → Provisioned IOPS로 전환 (gp3 → io1)
├─ 커넥션 풀 고갈
│   → max_connections 파라미터 조정
│   → 커넥션 풀링 (PgBouncer / RDS Proxy) 도입
├─ 슬로우 쿼리
│   → 인덱스 최적화
│   → 쿼리 튜닝 (EXPLAIN ANALYZE)
│   → Read Replica로 읽기 부하 분산
└─ 잠금 경합 (Lock Contention)
    → 트랜잭션 최적화
    → 행 수준 잠금 보장
```

### 5.3 Lambda 타임아웃 / 쓰로틀링

```
증상: Lambda 함수 타임아웃, 504 에러, ConcurrentExecutions 제한

진단 순서:
1. CloudWatch Logs → 에러 패턴 확인
2. CloudWatch Metrics → Duration, Invocations, Errors, Throttles, ConcurrentExecutions
3. X-Ray Traces → 실행 경로 및 병목 확인

해결:
├─ 콜드 스타트 (Cold Start)
│   → Provisioned Concurrency 활성화
│   → Lambda SnapStart 활성화 (Java)
│   → 코드/의존성 크기 최소화
├─ 실행 시간 초과 (Timeout)
│   → 타임아웃 설정 증가 (기본 3초 → 적절한 값)
│   → 코드 최적화 (I/O 병목 확인)
│   → Step Functions로 작업 분할
├─ 동시성 제한 (Throttling)
│   → Account-level Reserved Concurrency 요청 증가
│   → SQS/DynamoDB Stream으로 이벤트 버퍼링
│   → SQS Lambda 이벤트 소스로 배치 처리 + 재시도
├─ 메모리 부족 (OOM)
│   → 메모리 할당 증가 (128MB → 256MB+)
│   → 동시에 CPU도 증가 (Lambda 메모리 비례 CPU)
└─ VPC 내 Lambda 콜드 스타트 심화
    → Hyperplane ENI로 개선 (이미 적용됨)
    → VPC 외부로 이동 가능한지 검토
    → NAT Gateway 대신 VPC Endpoint 사용
```

### 5.4 S3 Access Denied (403 Forbidden)

```
증상: S3 버킷 접근 시 403 Forbidden 에러

진단 순서 (우선순위대로):
1. IAM Policy → 버킷에 대한 명시적 허용 여부
2. Bucket Policy → 명시적 거부(Deny) 여부
3. Bucket ACL → 기본 ACL 확인
4. Block Public Access 설정 → 외부 접근 차단 여부
5. IAM Role의 Trust Policy → 역할 수임 여부
6. Cross-Account → 버킷 소유자 계정과 접근 계정이 다른 경우

해결:
├─ IAM Policy 문제
│   → s3:GetObject, s3:PutObject 등 필요한 Action 추가
│   → Resource ARN 정확히 지정 (arn:aws:s3:::bucket-name/*)
├─ Bucket Policy 거부
│   → 명시적 Deny 제거 또는 Condition 추가
│   → Principal에 접근 계정/역할 추가
├─ Cross-Account 접근
│   → 버킷 소유자 계정의 Bucket Policy에 Cross-Account 허용
│   → 접근 계정의 IAM Policy에 버킷 허용
│   → 양쪽 모두 허용 필요 (교차 계정은 AND 조건)
├─ CORS 에러 (브라우저에서)
│   → Bucket CORS 설정 추가
│   → AllowedOrigins, AllowedMethods, AllowedHeaders 설정
└─ KMS 암호화된 객체
    → KMS Key Policy에 복호화 권한 추가
    → IAM Policy에 kms:Decrypt 권한 추가
```

### 5.5 CloudFront 캐시 문제

```
증상: 업데이트된 콘텐츠가 반영되지 않음, 오래된 버전 서비스

진단 순서:
1. CloudFront Cache Hit Rate 확인
2. 객체의 Cache-Control 헤더 확인
3. CloudFront 배포의 Default TTL 설정 확인
4. S3 원본의 실제 콘텐츠 업데이트 여부 확인

해결:
├─ 즉시 반영 필요
│   → CloudFront Cache Invalidation 생성 (/*  또는 특정 경로)
│   → 관련 경로 무효화: /images/*, /api/v2/*
├─ 예방적 설정
│   → Cache-Control: no-cache, no-store, max-age=0 (동적 콘텐츠)
│   → Cache-Control: max-age=86400 (정적 콘텐츠)
│   → 버전드 URL 사용 (/v1.2/main.js)
├── TTL 최적화
│   → Minimum TTL: 0, Default TTL: 86400, Maximum TTL: 31536000
│   → 정적/동적 경로별 Behavior 분리
└── 원본 오류
    → S3 버킷의 실제 객체가 업데이트되지 않았을 수 있음
    → 원본(S3/ALB)의 응답 헤더 확인
```

### 5.6 DynamoDB 쓰로틀링 (Throttling)

```
증상: DynamoDB 작업 시 ProvisionedThroughputExceededException

진단 순서:
1. CloudWatch → ConsumedReadCapacityUnits / ConsumedWriteCapacityUnits
2. ThrottledRequests 메트릭 확인
3. 테이블의 RCUs/WCUs 설정 vs 실제 소비량 비교
4. Hot Partition 여부 확인 (PartitionKey 불균형)

해결:
├─ Provisioned 모드
│   → RCUs/WCUs 증설 (수동 또는 Auto Scaling 활성화)
│   → DynamoDB Auto Scaling 설정 (TargetUtilization 70%)
├─ On-Demand 모드 전환
│   → 트래픽이 예측 불가한 경우 즉시 전환
│   → 비용은 약 2-3x 증가하지만 쓰로틀링 즉시 해소
├── Hot Partition 문제
│   → Partition Key 설계 재검토 (고카디널리티 키 사용)
│   → Sharding Key 추가 (랜덤 접두사)
│   → Write Shuffling 패턴 적용
├── 읽기 최적화
│   → DynamoDB Accelerator (DAX) 도입
│   → 최종 일관된 읽기(Eventually Consistent Read) 사용
│   → Query 대신 GetItem 사용 가능한지 검토
└── 배치 작업 최적화
    → BatchWriteItem / BatchGetItem 사용
    → 병렬 쓰기보다 배치 쓰기로 전환
```

### 5.7 VPC 연결 불가 (Network Unreachable)

```
증상: 인스턴스에서 외부/내부 통신 불가

진단 순서 (체크리스트):
□ 1. Security Group: 인바운드/아웃바운드 규칙
□ 2. Network ACL: 서브넷의 NACL 규칙 (기본 규칙 포함)
□ 3. Route Table: 대상 경로 (0.0.0.0/0 → IGW, 로컬 → VPC)
□ 4. Internet Gateway: VPC에 연결됨?
□ 5. NAT Gateway: 프라이빗 서브넷의 외부 접근용
□ 6. Elastic IP: NAT Gateway에 할당됨?
□ 7. DNS Resolution: VPC DNS 설정 (enableDnsSupport/enableDnsHostnames)
□ 8. VPC Peering/Transit Gateway: Cross-VPC 연결

해결:
├─ 퍼블릭 서브넷 인터넷 불가
│   → Route Table에 0.0.0.0/0 → igw-xxx 확인
│   → Security Group 아웃바운드 0.0.0.0/0 허용 확인
│   → 퍼블릭 IP (EIP) 할당 확인
├─ 프라이빗 서브넷 인터넷 불가
│   → Route Table에 0.0.0.0/0 → nat-xxx 확인
│   → NAT Gateway가 퍼블릭 서브넷에 위치?
│   → NAT Gateway에 EIP 할당됨?
├─ Cross-VPC 통신 불가
│   → VPC Peering 연결 상태 확인 (Active?)
│   → 양쪽 Route Table에 상대 VPC CIDR → pcx-xxx 추가
│   → DNS Resolution Peering 활성화
├─ DNS 해석 불가
│   → VPC 설정: enableDnsSupport = true
│   → VPC 설정: enableDnsHostnames = true (퍼블릭 호스트명)
│   → DHCP Options Set 확인
└── 보안 그룹 체인
    → SG 간 참조가 순환하지 않는지 확인
    → NACL이 상태 비저장(Stateless)임에 유의 (인바운드+아웃바운드 모두 필요)
```

### 5.8 배포 후 5xx 에러 (Post-Deployment Errors)

```
증상: 새 버전 배포 후 API 5xx 에러율 급증

진단 순서:
1. 배포 시간과 에러 발생 시간의 상관관계 확인
2. 이전 버전과의 차이점 분석
3. CloudWatch Logs → 애플리케이션 에러 로그
4. X-Ray → 에러 발생 지점 추적

해결:
├─ Lambda 배포
│   → $LATEST → 버전/별칭 관리로 즉시 이전 버전으로 전환
│   → CodeDeploy Canary 배포: 10% → 검증 → 100% 또는 자동 롤백
│   → PreInvoke hooks로 배포 전 검증
├─ ECS/Fargate 배포
│   → Circuit Breaker 활성화: 자동 롤백
│   → Blue/Green 배포 (CodeDeploy): 트래픽 전환 전 검증
│   → 최소 healthy percent 50% 유지 → 롤링 업데이트
├─ EC2 (Auto Scaling)
│   → ELB Health Check + Auto Scaling Group 교체
│   → Launch Template 이전 버전으로 롤백
│   → AMI 기반 롤백
└─ API Gateway
    → Stage → Deployment History → 이전 배포로 롤백
    → Canary Release 설정: 트래픽 비율 조절
```

### 5.9 SNS/SQS 메시지 처리 실패

```
증상: 메시지가 처리되지 않거나 손실됨

진단 순서:
1. SQS 대기열 길이 (ApproximateNumberOfMessages)
2. Dead Letter Queue 메시지 수
3. Lambda/SQS 연결 설정 확인
4. 메시지 가시성 타임아웃 (Visibility Timeout) 확인

해결:
├─ 메시지 손실
│   → SQS DLQ(Dead Letter Queue) 설정 확인
│   → SNS/SQS 구독 확인 (Protocol, Endpoint)
│   → FIFO 큐의 경우 MessageGroupId 확인
├─ 메시지 지연/적체
│   → Visibility Timeout 조정 (Lambda 타임아웃의 6x 권장)
│   → Consumer Auto Scaling (SQS 메트릭 기반)
│   → 배치 처리 크기 최적화
├─ 순서 보장 문제
│   → Standard Queue → FIFO Queue 전환
│   → Content-Based Deduplication 활성화
└─ Lambda 동시성 제한
    → Reserved Concurrency 증가
    → SQS 이벤트 소스의 MaxConcurrentExecutions 조정
```

### 5.10 AWS Certificate Manager (ACM) / TLS 문제

```
증상: HTTPS 접근 시 인증서 오류, 브라우저 경고

진단 순서:
1. ACM 인증서 상태 (ISSUED / PENDING_VALIDATION / EXPIRED)
2. 인증서 만료일 확인
3. Route 53 DNS 검증 레코드 확인
4. CloudFront/ALB에 인증서가 올바르게 연결됨?

해결:
├─ 인증서 만료
│   → ACM 자동 갱신: DNS 검증 레코드가 Route 53에 존재하는지 확인
│   → 이메일 검증 인증서 → DNS 검증으로 전환 권장
├─ DNS 검증 실패
│   → Route 53 Hosted Zone에 CNAME 레코드 존재 확인
│   → 전파 대기 (최대 30분)
├─ 인증서 리전 불일치
│   → CloudFront: us-east-1 리전의 인증서 필요
│   → ALB: 해당 리전의 인증터 필요
└── 체인 인증서 문제
    → ACM 인증서는 풀 체인 자동 관리
    → 커스텀 인증서(IAM) → ACM으로 마이그레이션 권장
```

### 5.11 AI Agent 장애 대응 우선순위 매트릭스

| 위험도 | 시나리오 | 자동 대응 | 인간 승인 |
|--------|----------|-----------|-----------|
| **CRITICAL** | RDS 페일오버, Multi-AZ 전환 | 즉시 실행 + 알림 | 사후 보고 |
| **HIGH** | Auto Scaling 그룹 스케일 아웃 | 자동 실행 | 모니터링 |
| **HIGH** | Lambda 쓰로틀링 → Provisioned Concurrency | 자동 제안 | 승인 후 실행 |
| **MEDIUM** | CloudFront 캐시 무효화 | 자동 제안 | 승인 후 실행 |
| **MEDIUM** | DynamoDB WCU 증설 | 자동 제안 | 승인 후 실행 |
| **LOW** | 로그 분석, 원인 파악 | 자동 실행 | 결과 보고 |
| **LOW** | 비용 분석, 최적화 제안 | 자동 실행 | 검토 후 결정 |

---

## 6. 주요 사례 요약

### 5.1 성공 사례 매트릭스

| 회사/플랫폼 | 장애 유형 | AI 해결 방법 | MTTR 개선 |
|-------------|-----------|-------------|-----------|
| **WGU** | Lambda 설정 오류 | AWS DevOps Agent + Dynatrace | 77% (2h→28m) |
| **Zenchef** | ECS 코드 리그레션 | AWS DevOps Agent | 75% (1-2h→20-30m) |
| **Datadog 내부** | Multi-service 장애 | Bits AI SRE | 최대 95% |
| **OpsWorker 고객** | K8s Alert | AI SRE Agent | 1분 이내 RCA |
| **PagerDuty 고객** | AWS 서비스 장애 | AIOps + AWS | 40%+ MTTR 감소 |

### 5.2 핵심 인사이트

1. **토폴로지 인텔리전스가 핵심**: 리소스 간 의존성을 아는 AI가 훨씬 빠르고 정확
2. **3-tier Skill 학습**: AWS 제공 → 사용자 정의 → 자동 학습의 계층적 지식
3. **Human-in-the-Loop 필수**: 완전 자율보다 인간 감독 하의 자동화가 실용적
4. **모델 선택 전략**: 작업별 다른 모델 (Sonnet=분석, Haiku=채팅, Nova=추출)
5. **서버리스가 자연스러운 선택**: 장애는 버스티하고 예측 불가

---

## 6. 참고 자료

- [AWS DevOps Agent 공식 블로그](https://aws.amazon.com/blogs/devops/leverage-agentic-ai-for-autonomous-incident-response-with-aws-devops-agent/)
- [Datadog: How we built Bits AI SRE](https://www.datadoghq.com/blog/building-bits-ai-sre/)
- [OpsWorker: AI-Powered Incident Investigation](https://www.opsworker.ai/blog/opsworker-ai-powered-incident-investigation-built-on-aws/)
- [PagerDuty AI Agents + AWS](https://www.pagerduty.com/blog/ai/ai-agents-just-got-smarter-thanks-to-pagerduty-aws/)
- [PagerDuty AIOps Use Cases](https://www.pagerduty.com/resources/aiops/learn/aiops-use-cases-incident-resolution/)
- [AWS re:Invent 2025: Accelerating incident response through AIOps](https://www.youtube.com/watch?v=Ny4rrINHPe0)
- [Nitish Agarwal: AI agents can cut MTTR by 40%](https://nitishagar.medium.com/ai-agents-can-cut-mttr-by-40-2ca232f26542)
- [AWS DevOps Agent 문서](https://docs.aws.amazon.com/devopsagent/latest/userguide/)
