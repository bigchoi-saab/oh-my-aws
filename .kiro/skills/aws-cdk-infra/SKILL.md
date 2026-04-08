---
name: aws-cdk-infra
description: CDK 인프라 생성/변경 도메인 지식. 신규 AWS 리소스를 CDK로 프로비저닝하거나 기존 인프라를 변경하는 작업을 지원한다.
version: 0.1.0
category: Operations
tags: [aws, cdk, infrastructure, iac, provisioning, create, modify]
prerequisites: [Node.js, AWS CDK CLI, CDK project initialized, TypeScript]
allowed-tools: [Read, Grep, Glob]
note: "이 skill은 aws-team-leader를 통해서만 사용됨. Infra Analyzer agent가 참조하는 도메인 지식."
---

# AWS CDK Infrastructure Skill

## 1. 역할

신규 AWS 인프라를 CDK로 생성하거나, 기존 인프라를 변경하는 작업의 **도메인 지식**을 제공한다.

### 지원 요청 유형

| 유형 | 설명 | 예시 |
|------|------|------|
| **create** | 새로운 construct/stack 생성 | "Lambda + API Gateway 생성해줘" |
| **modify** | 기존 construct 설정 변경 | "Lambda 타임아웃을 30초로 변경" |

> **delete는 v2로 이연**: 데이터 손실 위험이 높아 현재 버전에서는 지원하지 않는다. delete 요청 시 팀장은 "삭제는 아직 지원하지 않습니다. CDK 코드를 직접 수정해주세요."로 응답한다.

### 인시던트 대응과의 차이

| 항목 | 인시던트 CDK (aws-cdk-operations) | 인프라 CDK (이 skill) |
|------|-----------------------------------|----------------------|
| 트리거 | 장애 완화 후 drift 반영 | 사용자의 인프라 요청 |
| 목표 | CLI 변경을 CDK에 영구 반영 | 새 리소스 생성 또는 기존 변경 |
| 범위 | 단일 속성 변경 | 전체 construct/stack 설계 |
| 참조 | audit-report.yaml | infra-request.yaml |

## 2. CDK Construct Catalog

### 2.1 Lambda + API Gateway

REST API 백엔드. Lambda 함수와 API Gateway를 연결한다.

```typescript
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import { Duration } from 'aws-cdk-lib';

// Lambda Function
const fn = new lambda.Function(this, 'ApiHandler', {
  runtime: lambda.Runtime.NODEJS_20_X,
  handler: 'index.handler',
  code: lambda.Code.fromAsset('lambda'),
  timeout: Duration.seconds(30),
  memorySize: 256,
  environment: {
    NODE_ENV: props.environment,  // CDK context로 주입
  },
  tracing: lambda.Tracing.ACTIVE,
});

// API Gateway
const api = new apigw.RestApi(this, 'Api', {
  restApiName: `${props.serviceName}-api`,
  deployOptions: {
    stageName: props.environment,
    tracingEnabled: true,
  },
});

api.root.addMethod('GET', new apigw.LambdaIntegration(fn));
```

**안전 노트**: Lambda timeout은 API Gateway timeout(29초)보다 짧게 설정. Provisioned Concurrency는 prod에서만 고려.

### 2.2 ECS Fargate + ALB

컨테이너 기반 서비스. Fargate 태스크와 Application Load Balancer를 연결한다.

```typescript
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecsPatterns from 'aws-cdk-lib/aws-ecs-patterns';

const service = new ecsPatterns.ApplicationLoadBalancedFargateService(this, 'Service', {
  cluster: props.cluster,
  taskImageOptions: {
    image: ecs.ContainerImage.fromEcrRepository(props.repository, props.imageTag),
    containerPort: 8080,
    environment: {
      NODE_ENV: props.environment,
    },
    logDriver: ecs.LogDrivers.awsLogs({
      streamPrefix: props.serviceName,
    }),
  },
  cpu: 512,
  memoryLimitMiB: 1024,
  desiredCount: props.environment === 'prod' ? 3 : 1,
  healthCheckGracePeriod: Duration.seconds(60),
  circuitBreaker: { rollback: true },
});

// Auto Scaling
const scaling = service.service.autoScaleTaskCount({
  minCapacity: 1,
  maxCapacity: props.environment === 'prod' ? 10 : 3,
});
scaling.scaleOnCpuUtilization('CpuScaling', {
  targetUtilizationPercent: 70,
});
```

**안전 노트**: circuitBreaker 활성화 필수. desiredCount는 환경별 분리. healthCheckGracePeriod는 컨테이너 시작 시간 고려.

### 2.3 S3 + CloudFront

정적 웹사이트 또는 CDN 배포. S3 버킷과 CloudFront Distribution을 연결한다.

```typescript
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as cloudfront from 'aws-cdk-lib/aws-cloudfront';
import * as origins from 'aws-cdk-lib/aws-cloudfront-origins';
import { RemovalPolicy } from 'aws-cdk-lib';

const bucket = new s3.Bucket(this, 'WebBucket', {
  bucketName: `${props.serviceName}-${props.environment}-web`,
  blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
  encryption: s3.BucketEncryption.S3_MANAGED,
  removalPolicy: props.environment === 'prod'
    ? RemovalPolicy.RETAIN
    : RemovalPolicy.DESTROY,
  autoDeleteObjects: props.environment !== 'prod',
});

const distribution = new cloudfront.Distribution(this, 'Distribution', {
  defaultBehavior: {
    origin: origins.S3BucketOrigin.withOriginAccessControl(bucket),
    viewerProtocolPolicy: cloudfront.ViewerProtocolPolicy.REDIRECT_TO_HTTPS,
    cachePolicy: cloudfront.CachePolicy.CACHING_OPTIMIZED,
  },
  defaultRootObject: 'index.html',
  errorResponses: [
    { httpStatus: 404, responsePagePath: '/index.html', responseHttpStatus: 200 },
  ],
});
```

**안전 노트**: BLOCK_ALL 퍼블릭 액세스 필수. prod는 RETAIN, dev는 DESTROY. OAC(Origin Access Control) 사용.

### 2.4 DynamoDB + Streams

이벤트 기반 데이터 처리. DynamoDB 테이블과 Stream을 Lambda에 연결한다.

```typescript
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as eventsources from 'aws-cdk-lib/aws-lambda-event-sources';

const table = new dynamodb.Table(this, 'DataTable', {
  tableName: `${props.serviceName}-${props.environment}-data`,
  partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
  sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
  billingMode: props.environment === 'prod'
    ? dynamodb.BillingMode.PROVISIONED
    : dynamodb.BillingMode.PAY_PER_REQUEST,
  stream: dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
  pointInTimeRecovery: true,
  removalPolicy: props.environment === 'prod'
    ? RemovalPolicy.RETAIN
    : RemovalPolicy.DESTROY,
});

// Stream Consumer
const streamProcessor = new lambda.Function(this, 'StreamProcessor', {
  runtime: lambda.Runtime.NODEJS_20_X,
  handler: 'stream.handler',
  code: lambda.Code.fromAsset('lambda'),
  timeout: Duration.minutes(1),
});

streamProcessor.addEventSource(new eventsources.DynamoEventSource(table, {
  startingPosition: lambda.StartingPosition.TRIM_HORIZON,
  batchSize: 100,
  retryAttempts: 3,
}));

table.grantStreamRead(streamProcessor);
```

**안전 노트**: prod는 PROVISIONED + PITR 필수. PAY_PER_REQUEST는 dev/staging만. retryAttempts 설정으로 poison pill 방지.

### 2.5 VPC + Subnets

네트워크 기반 인프라. 프라이빗/퍼블릭 서브넷 구성.

```typescript
import * as ec2 from 'aws-cdk-lib/aws-ec2';

const vpc = new ec2.Vpc(this, 'Vpc', {
  vpcName: `${props.serviceName}-${props.environment}-vpc`,
  maxAzs: props.environment === 'prod' ? 3 : 2,
  natGateways: props.environment === 'prod' ? 2 : 1,
  subnetConfiguration: [
    {
      name: 'Public',
      subnetType: ec2.SubnetType.PUBLIC,
      cidrMask: 24,
    },
    {
      name: 'Private',
      subnetType: ec2.SubnetType.PRIVATE_WITH_EGRESS,
      cidrMask: 24,
    },
    {
      name: 'Isolated',
      subnetType: ec2.SubnetType.PRIVATE_ISOLATED,
      cidrMask: 24,
    },
  ],
  flowLogs: {
    'FlowLog': {
      destination: ec2.FlowLogDestination.toCloudWatchLogs(),
      trafficType: ec2.FlowLogTrafficType.REJECT,
    },
  },
});
```

**안전 노트**: prod는 3 AZ + NAT 2개. PRIVATE_ISOLATED 서브넷은 DB용. VPC Flow Logs 필수 활성화.

### 2.6 RDS + Proxy

관계형 데이터베이스. RDS 인스턴스와 RDS Proxy를 연결한다.

```typescript
import * as rds from 'aws-cdk-lib/aws-rds';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';

const dbCredentials = new secretsmanager.Secret(this, 'DbCredentials', {
  secretName: `${props.serviceName}/${props.environment}/db-credentials`,
  generateSecretString: {
    secretStringTemplate: JSON.stringify({ username: 'admin' }),
    generateStringKey: 'password',
    excludePunctuation: true,
  },
});

const instance = new rds.DatabaseInstance(this, 'Database', {
  engine: rds.DatabaseInstanceEngine.postgres({
    version: rds.PostgresEngineVersion.VER_16,
  }),
  instanceType: props.environment === 'prod'
    ? ec2.InstanceType.of(ec2.InstanceClass.R6G, ec2.InstanceSize.LARGE)
    : ec2.InstanceType.of(ec2.InstanceClass.T4G, ec2.InstanceSize.MICRO),
  vpc: props.vpc,
  vpcSubnets: { subnetType: ec2.SubnetType.PRIVATE_ISOLATED },
  credentials: rds.Credentials.fromSecret(dbCredentials),
  multiAz: props.environment === 'prod',
  storageEncrypted: true,
  backupRetention: Duration.days(props.environment === 'prod' ? 30 : 7),
  deletionProtection: props.environment === 'prod',
  removalPolicy: props.environment === 'prod'
    ? RemovalPolicy.RETAIN
    : RemovalPolicy.DESTROY,
});

const proxy = new rds.DatabaseProxy(this, 'Proxy', {
  proxyTarget: rds.ProxyTarget.fromInstance(instance),
  vpc: props.vpc,
  secrets: [dbCredentials],
  requireTLS: true,
});
```

**안전 노트**: Secrets Manager로 자격증명 관리 필수. prod는 Multi-AZ + deletionProtection + RETAIN. PRIVATE_ISOLATED 서브넷에 배치.

## 3. 안전 규칙

### 필수 규칙

| # | 규칙 | 설명 |
|---|------|------|
| 1 | **항상 synth → diff 먼저** | 코드 작성 후 반드시 `cdk synth` → `cdk diff` 순서로 검증 |
| 2 | **deploy 분리** | CDK Engineer는 synth/diff까지만. deploy는 팀장 승인 후 별도 |
| 3 | **환경별 승인** | dev=MEDIUM risk, staging/prod=HIGH risk 승인 게이트 |
| 4 | **태그 필수** | 모든 리소스에 `Environment`, `Service`, `ManagedBy=cdk` 태그 |
| 5 | **최소 권한** | IAM Role은 필요한 최소 권한만 부여 |

### 환경별 분기 패턴

CDK context로 환경을 분기한다:
```typescript
const environment = this.node.tryGetContext('env') || 'dev';

// 환경별 분기 예시
const config = {
  dev:     { desiredCount: 1, maxAzs: 2, natGateways: 1, removalPolicy: RemovalPolicy.DESTROY },
  staging: { desiredCount: 2, maxAzs: 2, natGateways: 1, removalPolicy: RemovalPolicy.DESTROY },
  prod:    { desiredCount: 3, maxAzs: 3, natGateways: 2, removalPolicy: RemovalPolicy.RETAIN },
}[environment];
```

### 리소스 태깅 패턴

```typescript
import { Tags } from 'aws-cdk-lib';

Tags.of(this).add('Environment', props.environment);
Tags.of(this).add('Service', props.serviceName);
Tags.of(this).add('ManagedBy', 'cdk');
Tags.of(this).add('Team', props.teamName);
```

## 4. 네이밍 컨벤션

| 대상 | 패턴 | 예시 |
|------|------|------|
| **Stack** | `{ServiceName}{Environment}Stack` | `PaymentProdStack` |
| **Construct ID** | PascalCase, 역할 설명 | `ApiHandler`, `DataTable`, `WebBucket` |
| **Resource Name** | `{service}-{env}-{role}` | `payment-prod-api`, `order-dev-data` |
| **파일명** | kebab-case | `payment-stack.ts`, `order-service.ts` |
| **Props Interface** | `{StackName}Props` | `PaymentStackProps` |

### Stack 구조 패턴

```
cdk-project/
├── bin/
│   └── app.ts              # 진입점, Stack 인스턴스 생성
├── lib/
│   ├── {service}-stack.ts   # 메인 Stack 정의
│   └── constructs/          # 재사용 가능한 Construct
│       ├── api-construct.ts
│       └── data-construct.ts
├── lambda/                  # Lambda 소스 코드
├── test/                    # CDK 테스트
├── cdk.json                 # CDK 설정
└── tsconfig.json
```
