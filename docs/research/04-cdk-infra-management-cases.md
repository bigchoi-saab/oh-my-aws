# AWS CDK를 활용한 인프라 관리 사례 및 방법

> 조사일: 2026-04-02
> 목적: AWS CDK로 실제 인프라를 관리하는 사례, 패턴, 방법론 조사

---

## 1. 실제 CDK 활용 패턴

### 1.1 Multi-Environment 관리 (Dev/Staging/Prod)

```python
# app.py - 환경별 스택 배포
from aws_cdk import App, Environment
from my_stacks import VpcStack, AppStack

app = App()

# 환경 설정
environments = {
    "dev": {"account": "111111111111", "region": "ap-northeast-2"},
    "staging": {"account": "222222222222", "region": "ap-northeast-2"},
    "prod": {"account": "333333333333", "region": "ap-northeast-2"},
}

for env_name, env_config in environments.items():
    env = Environment(**env_config)

    # 네트워크 스택
    vpc_stack = VpcStack(
        app, f"{env_name}-vpc",
        env_name=env_name,
        env=env,
    )

    # 애플리케이션 스택
    AppStack(
        app, f"{env_name}-app",
        vpc=vpc_stack.vpc,
        env_name=env_name,
        env=env,
    )

app.synth()
```

**cdk.json 환경별 배포:**
```json
{
  "context": {
    "dev": { "instanceType": "t3.small", "minCapacity": 1, "maxCapacity": 2 },
    "staging": { "instanceType": "t3.medium", "minCapacity": 2, "maxCapacity": 4 },
    "prod": { "instanceType": "t3.large", "minCapacity": 3, "maxCapacity": 10 }
  }
}
```

### 1.2 Multi-Account (AWS Organizations)

```python
# 멀티 계정 아키텍처
from aws_cdk import App, Environment

app = App()

# 1. Shared Services Account
shared_env = Environment(account="111111111111", region="ap-northeast-2")
SharedServicesStack(app, "shared-services", env=shared_env)

# 2. Network Account (Hub)
network_env = Environment(account="222222222222", region="ap-northeast-2")
NetworkHubStack(app, "network-hub", env=network_env)

# 3. Workload Accounts
for workload in ["frontend", "backend", "data"]:
    workload_env = Environment(account="333333333333", region="ap-northeast-2")
    WorkloadStack(
        app, f"{workload}-stack",
        workload_name=workload,
        env=workload_env,
    )

# 4. Security Account
security_env = Environment(account="444444444444", region="ap-northeast-2")
SecurityStack(app, "security", env=security_env)
```

### 1.3 Microservices 인프라

```python
from aws_cdk import (
    Stack, Duration, CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_elasticloadbalancingv2 as elbv2,
    aws_servicediscovery as sd,
)
from constructs import Construct

class MicroserviceStack(Stack):
    """단일 마이크로서비스를 위한 인프라"""

    def __init__(self, scope: Construct, id: str,
                 vpc: ec2.IVpc,
                 cluster: ecs.ICluster,
                 service_name: str,
                 container_port: int = 8080,
                 **kwargs):
        super().__init__(scope, id, **kwargs)

        # ECR Repository
        repo = ecr.Repository(
            self, f"{service_name}-repo",
            repository_name=f"microservices/{service_name}",
            lifecycle_rules=[ecr.LifecycleRule(max_image_count=10)],
        )

        # Task Definition
        task_def = ecs.FargateTaskDefinition(
            self, f"{service_name}-task",
            cpu=256,
            memory_limit_mib=512,
        )

        container = task_def.add_container(service_name,
            image=ecs.ContainerImage.from_ecr_repository(repo),
            port_mappings=[ecs.PortMapping(container_port=container_port)],
            logging=ecs.LogDriver.aws_logs(stream_prefix=service_name),
            environment={
                "SERVICE_NAME": service_name,
                "ENVIRONMENT": self.stack_name.split("-")[0],
            },
        )

        # ECS Service
        service = ecs.FargateService(
            self, f"{service_name}-service",
            cluster=cluster,
            task_definition=task_def,
            desired_count=2,
            min_healthy_percent=50,
            max_healthy_percent=200,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
        )

        # Auto Scaling
        scaling = service.auto_scale_task_count(
            min_capacity=2,
            max_capacity=10,
        )
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=70,
        )

        self.service = service
        self.repository = repo
```

### 1.4 Serverless 패턴 (Lambda + API Gateway + DynamoDB)

```python
from aws_cdk import (
    Stack, Duration, CfnOutput,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_lambda_event_sources as events,
)
from constructs import Construct

class ServerlessApiStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # DynamoDB Table
        table = dynamodb.Table(
            self, "DataTable",
            partition_key=dynamodb.Attribute(
                name="pk", type=dynamodb.AttributeType.STRING
            ),
            sort_key=dynamodb.Attribute(
                name="sk", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            stream=dynamodb.StreamViewType.NEW_AND_OLD_IMAGES,
        )

        # DLQ
        dlq = sqs.Queue(self, "DLQ",
            retention_period=Duration.days(14),
        )

        # Lambda 함수
        create_handler = _lambda.Function(
            self, "CreateHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="create.handler",
            code=_lambda.Code.from_asset("src/create"),
            environment={"TABLE_NAME": table.table_name},
            dead_letter_queue=dlq,
        )
        table.grantReadWriteData(create_handler)

        get_handler = _lambda.Function(
            self, "GetHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="get.handler",
            code=_lambda.Code.from_asset("src/get"),
            environment={"TABLE_NAME": table.table_name},
        )
        table.grantReadData(get_handler)

        # API Gateway
        api = apigw.LambdaRestApi(
            self, "Api",
            handler=create_handler,
            proxy=False,
            deploy_options=apigw.StageOptions(
                throttling_rate_limit=100,
                throttling_burst_limit=200,
            ),
        )

        items = api.root.add_resource("items")
        items.add_method("POST", apigw.LambdaIntegration(create_handler))
        items.add_method("GET", apigw.LambdaIntegration(get_handler))
        items.add_resource("{id}").add_method(
            "GET", apigw.LambdaIntegration(get_handler)
        )

        CfnOutput(self, "ApiUrl", value=api.url)
```

### 1.5 데이터 파이프라인 (Glue + Step Functions + EventBridge)

```python
from aws_cdk import (
    Stack, Duration,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as tasks,
    aws_events as events,
    aws_events_targets as targets,
    aws_glue as glue,
    aws_s3 as s3,
)
from constructs import Construct

class DataPipelineStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)

        # S3 Buckets
        raw_bucket = s3.Bucket(self, "RawData",
            lifecycle_rules=[s3.LifecycleRule(
                expiration=Duration.days(90),
                transitions=[s3.Transition(
                    storage_class=s3.StorageClass.GLACIER,
                    transition_after=Duration.days(30),
                )],
            )],
        )

        processed_bucket = s3.Bucket(self, "ProcessedData")

        # Glue Job
        glue_job = glue.CfnJob(self, "ETLJob",
            role="arn:aws:iam::xxx:role/GlueRole",
            command=glue.CfnJob.JobCommandProperty(
                name="glueetl",
                script_location="s3://scripts/etl.py",
            ),
            glue_version="4.0",
            max_retries=1,
        )

        # Step Functions 워크플로우
        extract_task = tasks.GlueStartJobRun(
            self, "Extract",
            glue_job_name=glue_job.ref,
        )

        success_task = sfn.Succeed(self, "Success")

        definition = extract_task.next(success_task)

        state_machine = sfn.StateMachine(
            self, "Pipeline",
            definition=definition,
            timeout=Duration.hours(2),
        )

        # EventBridge 스케줄
        rule = events.Rule(
            self, "DailySchedule",
            schedule=events.Schedule.rate(Duration.hours(24)),
        )
        rule.add_target(targets.SfnStateMachine(state_machine))
```

---

## 2. CDK 프로젝트 조직화

### 2.1 Monorepo 구조 (권장)

```
infra-monorepo/
├── bin/
│   └── app.ts                    # CDK App 진입점
├── lib/
│   ├── constructs/               # 재사용 가능한 Construct
│   │   ├── vpc.ts
│   │   ├── ecs-service.ts
│   │   ├── lambda-api.ts
│   │   └── database.ts
│   ├── stacks/                   # 환경별 Stack
│   │   ├── network-stack.ts
│   │   ├── compute-stack.ts
│   │   ├── data-stack.ts
│   │   └── monitoring-stack.ts
│   └── utils/                    # 유틸리티
│       ├── config.ts
│       └── constants.ts
├── config/                       # 환경 설정
│   ├── dev.yaml
│   ├── staging.yaml
│   └── prod.yaml
├── test/
├── cdk.json
└── package.json
```

### 2.2 Construct 라이브러리 조직

```typescript
// lib/constructs/ecs-service.ts
import { Construct } from 'constructs';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as elbv2 from 'aws-cdk-lib/aws-elasticloadbalancingv2';

export interface EcsServiceProps {
  readonly vpc: ec2.IVpc;
  readonly cluster: ecs.ICluster;
  readonly image: ecs.ContainerImage;
  readonly port: number;
  readonly cpu?: number;
  readonly memory?: number;
  readonly desiredCount?: number;
  readonly autoScaling?: {
    min: number;
    max: number;
    targetCpuUtilization: number;
  };
}

export class EcsService extends Construct {
  public readonly service: ecs.FargateService;
  public readonly loadBalancer: elbv2.ApplicationLoadBalancer;

  constructor(scope: Construct, id: string, props: EcsServiceProps) {
    super(scope, id);

    // 기본값이 포함된 Construct
    const taskDef = new ecs.FargateTaskDefinition(this, 'TaskDef', {
      cpu: props.cpu ?? 256,
      memoryLimitMiB: props.memory ?? 512,
    });

    taskDef.addContainer('app', {
      image: props.image,
      portMappings: [{ containerPort: props.port }],
      logging: ecs.LogDriver.aws_logs({ stream_prefix: 'app' }),
    });

    this.service = new ecs.FargateService(this, 'Service', {
      cluster: props.cluster,
      taskDefinition: taskDef,
      desiredCount: props.desiredCount ?? 2,
      circuitBreaker: { rollback: true },
    });

    if (props.autoScaling) {
      const scaling = this.service.autoScaleTaskCount({
        minCapacity: props.autoScaling.min,
        maxCapacity: props.autoScaling.max,
      });
      scaling.scaleOnCpuUtilization('CpuScaling', {
        targetUtilizationPercent: props.autoScaling.targetCpuUtilization,
      });
    }
  }
}
```

---

## 3. CDK 배포 전략

### 3.1 Blue/Green 배포 (ECS)

```python
# ECS Blue/Green 배포 (CodeDeploy)
from aws_cdk import (
    aws_codedeploy as codedeploy,
    aws_ecs as ecs,
)

# CodeDeploy Application + Deployment Group
deployment_group = codedeploy.EcsDeploymentGroup(
    self, "BlueGreenDG",
    service=ecs_service,
    deployment_config=codedeploy.EcsDeploymentConfig.ALL_AT_ONCE,
    blue_green_deployment_config=codedeploy.EcsBlueGreenDeploymentConfig(
        terminate_time_on_rollback=Duration.minutes(5),
        green_target=...,
        blue_target=...,
    ),
)
```

### 3.2 Canary 배포

```python
# Step Functions 기반 Canary 배포
canary_task = tasks.EcsRunTask(
    self, "CanaryTest",
    cluster=cluster,
    task_definition=canary_task_def,
    run_task_resources_override=tasks.RunTaskOverrides(
        container_overrides=[...],
    ),
)

# 10% 트래픽 → 검증 → 100% 또는 롤백
```

### 3.3 CDK Hotswap (개발 환경)

```bash
# 개발 환경에서 빠른 반복
cdk deploy --hotswap

# Hotswap은 CloudFormation을 거치지 않고 직접 리소스 업데이트
# ⚠️ 프로덕션에서는 절대 사용하지 말 것 (drift 발생)
```

---

## 4. CDK + 다른 도구 통합

### 4.1 CDK + GitHub Actions

```yaml
name: CDK Deploy
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Configure AWS
        uses: aws-actions/configure-aws-credentials@v4
        with:
          role-to-assume: arn:aws:iam::xxx:role/GitHubActionsCDK
          aws-region: ap-northeast-2
      - name: Install & Deploy
        run: |
          npm ci
          npx cdk diff
          npx cdk deploy --require-approval never
```

### 4.2 CDK + Terraform (cdktf)

```typescript
// CDKTF (CDK for Terraform) - AWS 외 클라우드도 관리
import { App, TerraformStack } from 'cdktf';
import { AwsProvider } from '@cdktf/provider-aws';

class MultiCloudStack extends TerraformStack {
  constructor(scope: App, id: string) {
    super(scope, id);

    new AwsProvider(this, 'aws', { region: 'ap-northeast-2' });
    // AWS + GCP + Azure 리소스를 같은 코드로 관리
  }
}
```

### 4.3 CDK + cdk-nag (보안 검증)

```python
# cdk-nag로 보안 규칙 자동 검증
from cdk_nag import AwsSolutionsChecks, NagSuppressions
from aws_cdk import App, Aspects

app = App()

# 보안 규칙 검증 활성화
Aspects.of(app).add(AwsSolutionsChecks())

# 특정 규칙 예외 처리
NagSuppressions.add_stack_suppressions(
    my_stack,
    [{"id": "AwsSolutions-IAM4", "reason": "Managed policy acceptable"}],
)
```

---

## 5. 단계별 CDK 워크플로우 가이드

### 5.1 새 프로젝트 시작

```bash
# 1. 프로젝트 생성
mkdir my-infra && cd my-infra
cdk init app --language python

# 2. 부트스트래핑 (최초 1회)
cdk bootstrap aws://ACCOUNT_ID/ap-northeast-2

# 3. 코드 작성 (lib/ 또는 스택 파일)

# 4. 합성 (CloudFormation 템플릿 생성)
cdk synth

# 5. 변경사항 검토
cdk diff

# 6. 배포
cdk deploy

# 7. 확인
aws cloudformation describe-stacks --stack-name MyStack
```

### 5.2 리소스 추가

```python
# 기존 스택에 S3 버킷 추가
class MyStack(Stack):
    def __init__(self, scope, id, **kwargs):
        super().__init__(scope, id, **kwargs)

        # 기존 리소스...
        self.vpc = ec2.Vpc(self, "Vpc", max_azs=3)

        # 새로 추가할 리소스
        bucket = s3.Bucket(
            self, "DataBucket",
            versioned=True,
            encryption=s3.BucketEncryption.S3_MANAGED,
        )
```

```bash
# diff로 변경 확인 후 배포
cdk diff
cdk deploy
```

### 5.3 Drift 관리

```bash
# CloudFormation drift 감지
aws cloudformation detect-stack-drift --stack-name MyStack

# drift 상태 확인
aws cloudformation describe-stack-resource-drifts --stack-name MyStack
```

### 5.4 안전한 리팩토링

```bash
# CDK refactor 액션 사용 (Toolkit Library)
# 리소스를 다른 스택으로 이동해도 물리적 리소스는 보존
cdk refactor
```

---

## 6. 엔터프라이즈 채택 패턴

### 6.1 팀 소유권 모델

```
조직 구조:
├── Platform Team
│   ├── VPC / Network Stack (공유)
│   ├── Security Stack (공유)
│   └── CI/CD Pipeline Stack
├── Frontend Team
│   ├── CloudFront + S3 Stack
│   └── Lambda@Edge Stack
├── Backend Team
│   ├── ECS/Fargate Stack
│   └── API Gateway Stack
└── Data Team
    ├── RDS/Aurora Stack
    ├── Glue ETL Stack
    └── S3 Data Lake Stack
```

### 6.2 비용 관리 및 태깅

```python
# 필수 태그 정책
from aws_cdk import Tags

Tags.of(stack).add("Environment", env_name)
Tags.of(stack).add("Team", team_name)
Tags.of(stack).add("CostCenter", cost_center)
Tags.of(stack).add("ManagedBy", "CDK")
Tags.of(stack).add("Project", project_name)
Tags.of(stack).add("Owner", owner_email)
```

### 6.3 컴플라이언스 및 거버넌스

```python
# AWS Config 규칙 + CDK
from aws_cdk import aws_config as config

# 필수 태그 검증
config.ManagedRule(
    self, "RequiredTagsRule",
    identifier=config.ManagedRuleIdentifiers.REQUIRED_TAGS,
    rule_scope=config.RuleScope.from_resource(
        resource_type="AWS::S3::Bucket",
    ),
)
```

---

## 7. 참고 자료

- [AWS CDK 공식 가이드](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [CDK Toolkit Library GA (InfoQ)](https://www.infoq.com/news/2025/06/aws-cdk-toolkit-library/)
- [CDK 프로그래밍 액션](https://docs.aws.amazon.com/cdk/v2/guide/toolkit-library-actions.html)
- [AWS CDK in Action — May 2025](https://dev.to/aws/aws-cdk-in-action-may-2025-empowered-deployments-governance-and-community-1gdb)
- [CDK Pipelines 문서](https://docs.aws.amazon.com/cdk/api/v2/python/aws_cdk.pipelines/README.html)
- [Ultimate AWS CDK Guide 2025](https://www.cloudlaya.com/blog/aws-cdk-guide-2025/)
- [DataCamp: Build Your First CDK Stack](https://www.datacamp.com/tutorial/aws-cdk)
- [IaC 비교: Terraform vs Pulumi vs CDK](https://oneuptime.com/blog/post/2026-02-20-infrastructure-as-code-comparison/view)
- [Terraform vs Pulumi vs CDK for AI Workflows](https://medium.com/@pranavprakash4777/iac-battle-terraform-vs-pulumi-vs-aws-cdk-for-modern-ai-workflows-19cc6f7e8000)
