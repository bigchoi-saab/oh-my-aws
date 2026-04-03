---
name: aws-cdk-operations
description: CDK 인프라 코드 수정/배포 도메인 지식. 인시던트 완화 후 CLI 변경을 CDK 코드로 영구 반영하는 작업을 지원한다.
version: 0.1.0
category: Operations
tags: [aws, cdk, infrastructure, iac, deploy]
prerequisites: [Node.js, AWS CDK CLI, CDK project initialized]
allowed-tools: [Read, Grep, Glob, Edit, Bash, Write]
note: "이 skill은 aws-team-leader를 통해서만 사용됨. CDK Analyzer와 CDK Engineer agent가 참조하는 도메인 지식."
---

# AWS CDK Operations Skill

## 1. 역할

인시던트 완화 후 CLI로 적용한 임시 변경을 CDK 코드로 영구 반영하는 작업의 **도메인 지식**을 제공한다.

### 왜 필요한가
- CLI로 변경한 설정은 다음 `cdk deploy` 시 원래 값으로 되돌아감 (drift)
- CDK 코드와 실제 인프라가 불일치하면 팀 전체가 혼란에 빠짐
- "완화는 CLI로, 영구 수정은 CDK로" 가 올바른 패턴

## 2. 인시던트 → CDK 매핑 테이블

CLI 완화 조치를 CDK 코드에서 어떤 속성으로 반영해야 하는지 매핑한다.

### Compute

| CLI 변경 | CDK 속성 | Construct | 예시 |
|----------|----------|-----------|------|
| Lambda Reserved Concurrency | `reservedConcurrentExecutions` | `lambda.Function` | `reserved_concurrent_executions=300` |
| Lambda Timeout | `timeout` | `lambda.Function` | `timeout=Duration.seconds(30)` |
| Lambda Memory | `memorySize` | `lambda.Function` | `memory_size=512` |
| Lambda Provisioned Concurrency | `provisionedConcurrentExecutions` | `lambda.Alias` | `provisioned_concurrent_executions=10` |
| ECS Desired Count | `desiredCount` | `ecs.FargateService` | `desired_count=4` |
| ECS Task CPU/Memory | `cpu` / `memoryLimitMiB` | `ecs.FargateTaskDefinition` | `cpu=1024, memory_limit_mib=2048` |

### Database

| CLI 변경 | CDK 속성 | Construct | 예시 |
|----------|----------|-----------|------|
| DynamoDB Read/Write Capacity | `readCapacity` / `writeCapacity` | `dynamodb.Table` | `read_capacity=100` |
| DynamoDB Billing Mode | `billingMode` | `dynamodb.Table` | `billing_mode=BillingMode.PAY_PER_REQUEST` |
| RDS Instance Class | `instanceType` | `rds.DatabaseInstance` | `instance_type=InstanceType.of(...)` |
| RDS Storage (IOPS) | `storageThroughput` / `iops` | `rds.DatabaseInstance` | `iops=5000` |

### Network

| CLI 변경 | CDK 속성 | Construct | 예시 |
|----------|----------|-----------|------|
| CloudFront Cache Policy | `defaultBehavior.cachePolicy` | `cloudfront.Distribution` | 캐시 정책 변경 |
| Security Group Rules | `addIngressRule` | `ec2.SecurityGroup` | 인그레스 룰 추가/수정 |

### 기타

| CLI 변경 | CDK 속성 | Construct | 예시 |
|----------|----------|-----------|------|
| CloudWatch Alarm Threshold | `threshold` | `cloudwatch.Alarm` | `threshold=100` |
| Auto Scaling Policy | `targetUtilizationPercent` | `applicationautoscaling.TargetTrackingScalingPolicy` | `target_utilization_percent=70` |

## 3. 안전 규칙

CDK 코드 수정 및 배포 시 반드시 따라야 하는 규칙.

### 필수 규칙
| # | 규칙 | 설명 |
|---|------|------|
| 1 | **항상 diff 먼저** | `cdk deploy` 전에 반드시 `cdk diff`로 변경 사항 확인 |
| 2 | **Production 승인 필수** | production 스택은 deploy 전 명시적 사용자 승인 |
| 3 | **최소 변경** | 인시던트 관련 속성만 변경. 리팩터링이나 개선 금지 |
| 4 | **deploy 분리** | CDK Engineer는 synth/diff까지만. deploy는 팀장 승인 후 별도 실행 |

### 권장 규칙
| # | 규칙 | 설명 |
|---|------|------|
| 5 | **cdk-nag 검증** | 보안 규칙 위반이 없는지 확인 |
| 6 | **Hotswap은 dev만** | `--hotswap`은 개발 환경에서만 사용 |
| 7 | **스냅샷 태깅** | 변경 전 인시던트 ID로 태깅한 스냅샷 권장 |

## 4. CDK 프로젝트 탐색 패턴

CDK 코드베이스에서 대상 리소스를 찾는 방법.

### Step 1: CDK 프로젝트 루트 찾기
```bash
find . -name "cdk.json" -not -path "*/node_modules/*" -not -path "*/_research/*" -not -path "*/cdk-research/*"
```

### Step 2: 스택 파일 구조 파악
```
# TypeScript
Glob: **/lib/**/*-stack.ts, **/stacks/**/*.ts, **/bin/*.ts

# Python
Glob: **/*_stack.py, **/stacks/**/*.py, **/app.py
```

### Step 3: 리소스 검색
```
# Construct 타입으로 검색
Grep: "lambda.Function" | "dynamodb.Table" | "rds.DatabaseInstance"

# 리소스 이름/ID로 검색
Grep: "<리소스명>" | "<construct-id>"

# 속성명으로 검색
Grep: "reservedConcurrentExecutions" | "timeout" | "memorySize"
```

### Step 4: 의존성 확인
```
# Cross-stack reference
Grep: "CfnOutput" | "Fn.importValue" | "from_*"

# 같은 스택 내 참조
Grep: "<construct변수명>."
```

## 5. 참조 문서

| 문서 | 위치 | 내용 |
|------|------|------|
| CDK + AI Agent 인프라 | `docs/research/01-aws-cdk-ai-agent-infra.md` | CDK 패턴, multi-env, agent 워크플로우 |
| CDK 인프라 관리 사례 | `docs/research/04-cdk-infra-management-cases.md` | 모노레포, reusable constructs, 배포 전략 |
