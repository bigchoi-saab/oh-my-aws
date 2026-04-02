# AWS CDK를 활용한 AI Agent 인프라 관리 조사

> 조사일: 2026-04-02
> 목적: AI Agent가 AWS CDK를 이용하여 AWS 인프라를 프로그래밍 방식으로 관리하는 방법 조사

---

## 1. AWS CDK 개요

### 1.1 CDK란?

AWS Cloud Development Kit (CDK)는 **코드로 AWS 인프라를 정의하고 프로비저닝**하는 오픈소스 프레임워크이다. CloudFormation 템플릿(JSON/YAML) 대신 TypeScript, Python, Java, C#, Go 등의 프로그래밍 언어로 인프라를 정의할 수 있다.

**핵심 장점 (AI Agent 관점):**
- **프로그래밍 언어 사용**: AI Agent가 코드를 생성·수정·실행하기에 최적
- **타입 안전성**: 컴파일 타임에 오류 감지
- **재사용성**: Construct 단위로 모듈화 가능
- **프로그래밍 제어**: 조건문, 반복문, 함수 등으로 동적 인프라 구성
- **CloudFormation 기반**: 안정적인 배포 파이프라인

### 1.2 핵심 개념

| 개념 | 설명 | 예시 |
|------|------|------|
| **App** | CDK 애플리케이션의 루트 | `cdk.App()` |
| **Stack** | CloudFormation 스택에 매핑되는 배포 단위 | `cdk.Stack(app, "MyStack")` |
| **Construct** | AWS 리소스를 캡슐화한 재사용 가능한 컴포넌트 | `s3.Bucket(self, "MyBucket")` |
| **L1 Construct** | AWS 리소스 1:1 매핑 (CFn 리소스) | `s3.CfnBucket` |
| **L2 Construct** | 기본값과 모범 사례가 포함된 고수준 추상화 | `s3.Bucket` |
| **L3 Construct** | 특정 use case를 위한 패턴 | `aws-rds.DatabaseInstance` |

### 1.3 CDK가 AI Agent에 이상적인 이유

```
전통적 접근 (CloudFormation YAML):
  - 수동 JSON/YAML 작성
  - 동적 구성 어려움
  - 오류 감지가 배포 시에만 가능

CDK 접근 (AI Agent 최적):
  - AI가 코드를 생성 → synth → diff → deploy
  - 프로그래밍 로직으로 동적 인프라
  - IDE/LSP로 즉각적 오류 피드백
  - Git 기반 버전 관리
```

---

## 2. CDK with Python (aws-cdk-lib)

### 2.1 프로젝트 설정

```bash
# Python CDK 프로젝트 생성
mkdir my-cdk-project && cd my-cdk-project
cdk init app --language python

# 가상환경 활성화
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 필수 패키지 설치
pip install aws-cdk-lib constructs
```

### 2.2 프로젝트 구조

```
my-cdk-project/
├── app.py                    # CDK 앱 진입점
├── cdk.json                  # CDK 설정
├── requirements.txt          # 의존성
├── setup.py
└── my_cdk_project/
    ├── __init__.py
    └── my_cdk_project_stack.py  # 스택 정의
```

### 2.3 주요 리소스 예제 (Python)

#### VPC 생성

```python
from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    CfnOutput
)
from constructs import Construct

class NetworkStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self, "MainVpc",
            max_azs=3,
            nat_gateway_provider=ec2.NatProvider.gateway(),
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    cidr_mask=24
                ),
            ]
        )

        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
```

#### Lambda + API Gateway (Serverless)

```python
from aws_cdk import (
    Stack,
    Duration,
    aws_lambda as _lambda,
    aws_apigateway as apigw,
)
from constructs import Construct

class ServerlessStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Lambda 함수
        handler = _lambda.Function(
            self, "ApiHandler",
            runtime=_lambda.Runtime.PYTHON_3_12,
            handler="index.handler",
            code=_lambda.Code.from_asset("lambda"),
            timeout=Duration.seconds(30),
            environment={
                "LOG_LEVEL": "INFO"
            }
        )

        # API Gateway
        api = apigw.LambdaRestApi(
            self, "ApiEndpoint",
            handler=handler,
            proxy=False
        )

        api.root.add_resource("hello").add_method("GET")
```

#### RDS 데이터베이스

```python
from aws_cdk import (
    Stack,
    Duration,
    aws_rds as rds,
    aws_ec2 as ec2,
)
from constructs import Construct

class DatabaseStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
                 vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.cluster = rds.DatabaseCluster(
            self, "AuroraCluster",
            engine=rds.DatabaseClusterEngine.aurora_postgres(
                version=rds.AuroraPostgresEngineVersion.VER_16_1
            ),
            vpc=vpc,
            writer=rds.ClusterInstance.provisioned("Writer",
                instance_type=ec2.InstanceType.of(
                    ec2.InstanceClass.BURSTABLE4,
                    ec2.InstanceSize.MEDIUM
                )
            ),
            readers=[
                rds.ClusterInstance.provisioned("Reader",
                    instance_type=ec2.InstanceType.of(
                        ec2.InstanceClass.BURSTABLE4,
                        ec2.InstanceSize.MEDIUM
                    )
                )
            ],
            backup_retention=Duration.days(7),
            deletion_protection=True,
        )
```

#### ECS Fargate

```python
from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ec2 as ec2,
    aws_ecr as ecr,
)
from constructs import Construct

class EcsStack(Stack):
    def __init__(self, scope: Construct, construct_id: str,
                 vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        cluster = ecs.Cluster(
            self, "Cluster",
            vpc=vpc
        )

        repo = ecr.Repository(
            self, "AppRepository",
            repository_name="my-app"
        )

        task_definition = ecs.FargateTaskDefinition(
            self, "TaskDef",
            cpu=512,
            memory_limit_mib=1024,
        )

        container = task_definition.add_container("App",
            image=ecs.ContainerImage.from_ecr_repository(repo, "latest"),
            port_mappings=[ecs.PortMapping(container_port=8080)],
        )

        service = ecs.FargateService(
            self, "Service",
            cluster=cluster,
            task_definition=task_definition,
            desired_count=2,
            assign_public_ip=False,
        )
```

### 2.4 CDK CLI 주요 명령어

```bash
# 부트스트래핑 (최초 1회)
cdk bootstrap aws://ACCOUNT_ID/REGION

# 합성 (CloudFormation 템플릿 생성)
cdk synth

# 배포 전 변경사항 확인
cdk diff

# 배포
cdk deploy --require-approval never

# 스택 목록
cdk list

# 스택 삭제
cdk destroy --force
```

---

## 3. CDK with TypeScript

### 3.1 프로젝트 설정

```bash
mkdir my-cdk-app && cd my-cdk-app
cdk init app --language typescript
npm install @aws-cdk/aws-*
```

### 3.2 프로젝트 구조

```
my-cdk-app/
├── bin/
│   └── my-cdk-app.ts          # 진입점
├── lib/
│   └── my-cdk-app-stack.ts    # 스택 정의
├── test/
│   └── my-cdk-app.test.ts     # 테스트
├── cdk.json
├── tsconfig.json
└── package.json
```

### 3.3 주요 리소스 예제 (TypeScript)

```typescript
import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';

export class MyStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // S3 Bucket
    const bucket = new s3.Bucket(this, 'MyBucket', {
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // DynamoDB Table
    const table = new dynamodb.Table(this, 'MyTable', {
      partitionKey: { name: 'pk', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'sk', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
    });

    // Lambda Function
    const handler = new lambda.Function(this, 'Handler', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda'),
      environment: {
        BUCKET_NAME: bucket.bucketName,
        TABLE_NAME: table.tableName,
      },
    });

    bucket.grantReadWrite(handler);
    table.grantReadWriteData(handler);

    // API Gateway
    const api = new apigw.LambdaRestApi(this, 'Api', {
      handler,
      proxy: false,
    });

    api.root.addResource('items').addMethod('GET');
  }
}
```

---

## 4. CDK 프로그래밍 제어 (AI Agent 핵심)

### 4.1 CDK Toolkit Library (GA - 2025년 5월)

**AWS CDK Toolkit Library**는 CDK를 프로그래밍 방식으로 제어할 수 있는 Node.js 라이브러리이다. CLI 명령어 없이 코드에서 직접 synth, deploy, destroy 등을 수행할 수 있다.

> **참고**: 현재 TypeScript만 지원. Python 지원은 로드맵에 있음.

```typescript
import { Toolkit } from '@aws-cdk/toolkit-lib';

async function aiAgentDeploy() {
  const toolkit = new Toolkit();

  // CDK 앱에서 Cloud Assembly 생성
  const cloudAssemblySource = await toolkit.fromCdkApp("npx ts-node app.ts");

  // 합성 (Synth)
  const cloudAssembly = await toolkit.synth(cloudAssemblySource);

  // 스택 정보 확인
  const stackDetails = await toolkit.list(cloudAssemblySource);

  // 배포
  await toolkit.deploy(cloudAssemblySource);

  // 또는 기존 Cloud Assembly로 배포
  await toolkit.deploy(cloudAssembly);

  // 삭제
  await toolkit.destroy(cloudAssemblySource);
}
```

### 4.2 주요 프로그래밍 액션

| 액션 | 설명 | AI Agent 활용 |
|------|------|---------------|
| `synth` | CloudFormation 템플릿 생성 | 코드 검증 후 배포 전 dry-run |
| `list` | 스택 정보 조회 | 현재 인프라 상태 파악 |
| `deploy` | 인프라 프로비저닝 | 코드 기반 배포 실행 |
| `destroy` | 스택 삭제 | 리소스 정리 |
| `rollback` | 실패한 배포 복구 | 장애 복구 |
| `watch` | 파일 변경 감지 | 개발 환경 자동 배포 |
| `refactor` | 리소스 이동 시 보존 | 안전한 리팩토링 |

### 4.3 Python에서 프로그래밍 제어

Python에서는 CLI 기반 접근이 필요하다:

```python
import subprocess
import json

class CDKAgent:
    """AI Agent를 위한 CDK 제어 클래스"""

    def synth(self, app_path: str = "app.py") -> dict:
        """CDK 앱 합성"""
        result = subprocess.run(
            ["cdk", "synth", "--app", f"python {app_path}", "--json"],
            capture_output=True, text=True
        )
        return json.loads(result.stdout)

    def diff(self, stack_name: str = None) -> str:
        """배포 전 변경사항 확인"""
        cmd = ["cdk", "diff"]
        if stack_name:
            cmd.append(stack_name)
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    def deploy(self, stack_name: str = None, no_approve: bool = True) -> str:
        """스택 배포"""
        cmd = ["cdk", "deploy"]
        if stack_name:
            cmd.append(stack_name)
        if no_approve:
            cmd.append("--require-approval")
            cmd.append("never")
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout

    def destroy(self, stack_name: str) -> str:
        """스택 삭제"""
        result = subprocess.run(
            ["cdk", "destroy", stack_name, "--force"],
            capture_output=True, text=True
        )
        return result.stdout

    def list_stacks(self) -> list:
        """스택 목록 조회"""
        result = subprocess.run(
            ["cdk", "list"],
            capture_output=True, text=True
        )
        return result.stdout.strip().split("\n")
```

### 4.4 CDK App 프로그래밍 방식 생성 (Python)

```python
from aws_cdk import App, Environment, Stack
import aws_cdk.aws_s3 as s3
import aws_cdk.aws_lambda as _lambda

# 프로그래밍 방식으로 CDK 앱 생성
app = App()

# 동적 스택 생성
env = Environment(account="123456789012", region="ap-northeast-2")

stack = Stack(app, "DynamicStack", env=env)

# AI Agent가 파라미터에 따라 리소스를 동적으로 생성
bucket = s3.Bucket(
    stack, "AgentBucket",
    versioned=True,
    removal_policy=s3.RemovalPolicy.DESTROY,
)

# 합성 (CloudFormation 템플릿 생성)
cloud_assembly = app.synth()

# 템플릿 확인
template = cloud_assembly.get_stack_by_name("DynamicStack").template
print(json.dumps(template, indent=2))
```

---

## 5. CDK Pipelines (CI/CD)

### 5.1 자동 배포 파이프라인

```python
from aws_cdk import (
    Stack,
    aws_codepipeline as codepipeline,
    aws_codepipeline_actions as actions,
)
from constructs import Construct

class PipelineStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        pipeline = codepipeline.Pipeline(
            self, "CdkPipeline",
            pipeline_name="infra-deployment",
        )

        # Source 단계
        source_output = codepipeline.Artifact()
        source_action = actions.CodeCommitSourceAction(
            action_name="Source",
            repository=codepipeline.Repository(
                self, "Repo",
                repository_name="infra-cdk"
            ),
            output=source_output,
        )

        source_stage = pipeline.add_stage(stage_name="Source")
        source_stage.add_action(source_action)

        # Build & Deploy 단계
        # CDK Pipeline은 CodeBuild에서 cdk deploy 실행
```

### 5.2 GitHub Actions 연동

```yaml
# .github/workflows/cdk-deploy.yml
name: CDK Deploy

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          npm install -g aws-cdk
      - name: CDK Diff
        run: cdk diff
      - name: CDK Deploy
        run: cdk deploy --require-approval never
```

---

## 6. AI Agent 아키텍처 제안

### 6.1 AI Agent → CDK 워크플로우

```
┌─────────────┐     ┌──────────────┐     ┌──────────────┐     ┌─────────────┐
│  사용자 요청  │ ──▶ │  AI Agent    │ ──▶ │  CDK 코드 생성 │ ──▶ │  cdk synth  │
│  "VPC 만들어" │     │  (LLM)      │     │  (Python/TS) │     │  (검증)      │
└─────────────┘     └──────────────┘     └──────────────┘     └──────┬──────┘
                                                                      │
                                                ┌─────────────────────┘
                                                ▼
                                         ┌──────────────┐     ┌──────────────┐
                                         │  cdk diff    │ ──▶ │  cdk deploy  │
                                         │  (변경 검토)  │     │  (배포)       │
                                         └──────────────┘     └──────────────┘
```

### 6.2 Agent-CDK 인터페이스 계층

| 계층 | 역할 | 기술 |
|------|------|------|
| **대화 계층** | 사용자 인터페이스 | Claude/GPT API |
| **오케스트레이션** | 요청 분석, 코드 생성 | LangChain, Function Calling |
| **CDK 코드 생성** | 인프라 코드 작성 | aws-cdk-lib (Python/TypeScript) |
| **실행 계층** | synth, diff, deploy | CDK CLI / Toolkit Library |
| **검증 계층** | 보안, 비용, 정책 검사 | cdk-nag, CFN Guard |

---

## 7. 주요 제약사항 및 주의점

### 7.1 프로그래밍 제어 시 주의점

| 항목 | 설명 |
|------|------|
| **Toolkit Library 언어 제한** | 현재 TypeScript만 지원 (Python 미지원) |
| **부트스트래핑 필요** | 대상 계정/리전에 최초 1회 `cdk bootstrap` 필요 |
| **상태 관리** | CDK 상태는 S3에 저장, 동시 수정 시 충돌 가능 |
| **권한 관리** | IAM Role/Policies에 따른 최소 권한 원칙 필수 |
| **롤백** | 배포 실패 시 자동 롤백되지만, 복잡한 스택은 수동 개입 필요 |

### 7.2 AI Agent를 위한 안전 가이드라인

1. **항상 `cdk diff` 후 `cdk deploy`**: 변경사항 사전 검토
2. **Production 스택은 `--require-approval`**: 자동 승인 금지
3. **`cdk destroy` 시 확인 절차**: 삭제 전 리소스 영향 분석
4. **코드 리뷰**: Agent가 생성한 CDK 코드는 항상 human review
5. **점진적 배포**: 한 번에 너무 많은 변경 금지

---

## 8. 참고 자료

- [AWS CDK 공식 문서](https://docs.aws.amazon.com/cdk/v2/guide/home.html)
- [CDK Toolkit Library (GA)](https://docs.aws.amazon.com/cdk/v2/guide/toolkit-library.html)
- [CDK Toolkit Library 프로그래밍 액션](https://docs.aws.amazon.com/cdk/v2/guide/toolkit-library-actions.html)
- [CDK Python 작업](https://docs.aws.amazon.com/cdk/v2/guide/work-with-cdk-python.html)
- [InfoQ: CDK Toolkit Library GA 발표](https://www.infoq.com/news/2025/06/aws-cdk-toolkit-library/)
- [CDK Hotswap Deployments](https://dev.to/aws-heroes/aws-cdk-hotswap-deployments-now-support-bedrock-agentcore-runtime-42c7)
- [PyCon 2025 CDK Demo](https://sreedharbukya.medium.com/automating-aws-infrastructure-with-python-my-pycon-2025-cdk-demo-3188fb6c4096)
