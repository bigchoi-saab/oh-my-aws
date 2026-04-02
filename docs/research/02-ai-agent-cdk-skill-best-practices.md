# AI Agent를 위한 CDK Skill 작성 Best Practice 조사

> 조사일: 2026-04-02
> 목적: AI Agent가 AWS CDK를 효과적으로 사용하기 위한 Skill 시스템 구축의 Best Practice 조사

---

## 1. AI Agent Skill이란?

### 1.1 정의

AI Agent Skill은 **구조화된 지식 패키지**로, AI 어시스턴트(Claude Code, Cursor, Copilot 등)가 특정 도메인에서 전문가처럼 동작하도록 지시하는 것이다.

**Skill = 표준작업절차(SOP) + 코드 패턴 + 제약사항**

### 1.2 Skill vs System Prompt vs Project

| 구분 | 특징 | 토큰 소모 |
|------|------|-----------|
| **System Prompt** | 항상 활성화, 모든 대화에 적용 | 높음 (매 대화마다) |
| **Project (CLAUDE.md)** | 정적 배경 컨텍스트 | 중간 (프로젝트당) |
| **Skill (SKILL.md)** | 필요시에만 로드 (Progressive Disclosure) | 낮음 (사용시에만) |

### 1.3 Progressive Disclosure 패턴

```
1단계: AI가 Skill 메타데이터(이름, 설명)만 인지
2단계: 사용자 요청이 관련 Skill과 매치되면 SKILL.md 로드
3단계: 깊이 있는 참조 문서(references/)는 필요시에만 로드
```

---

## 2. 기존 AI Agent 인프라 관리 도구

### 2.1 Pulumi Agent Skills (2026년 1월 출시)

Pulumi는 **Agent Skills 오픈 표준**(agentskills.io)을 따르는 Skill 패키지를 출시했다.

**Authoring Skills (코드 품질):**
| Skill | 설명 |
|-------|------|
| pulumi-best-practices | Output 처리, Component 구조, Secrets 관리, 안전한 리팩토링 |
| pulumi-component | ComponentResource 클래스 작성 가이드 |
| pulumi-automation-api | 프로그래밍 방식 Pulumi 오케스트레이션 |
| pulumi-esc | 중앙화된 Secrets/Config 관리 |

**Migration Skills:**
| Skill | 설명 |
|-------|------|
| terraform-to-pulumi | Terraform → Pulumi 마이그레이션 |
| cloudformation-to-pulumi | CloudFormation → Pulumi |
| cdk-to-pulumi | AWS CDK → Pulumi |
| azure-to-pulumi | Azure ARM/Bicep → Pulumi |

**설치 방법:**
```bash
# Claude Code Plugin Marketplace
claude plugin marketplace add pulumi/agent-skills
claude plugin install pulumi-authoring

# Universal (모든 AI 도구)
npx skills add pulumi/agent-skills --skill '*'
```

### 2.2 CloudPosse Atmos Agent Skills (2026년 2월)

CloudPosse의 Atmos 프로젝트는 **21개의 AI Agent Skill**을 오픈소스로 공개했다.

**특징:**
- Claude Code Plugin Marketplace 배포 (`atmos@cloudposse`)
- AGENTS.md 표준 (Linux Foundation AAIF) 준수
- 3-tier Progressive Disclosure: `AGENTS.md → SKILL.md → references/*.md`
- CI/CD 검증 워크플로우 포함

**Skill 목록 (21개):**
`atmos-stacks`, `atmos-components`, `atmos-vendoring`, `atmos-terraform`, `atmos-workflows`, `atmos-custom-commands`, `atmos-gitops`, `atmos-validation`, `atmos-templates`, `atmos-helmfile`, `atmos-packer`, `atmos-ansible`, `atmos-auth`, `atmos-stores`, `atmos-schemas`, `atmos-design-patterns`, `atmos-toolchain`, `atmos-devcontainer`, `atmos-introspection`, `atmos-yaml-functions`, `atmos-config`

### 2.3 LAXIMA Terraform Skill (Claude Code)

LAXIMA에서 발표한 Terraform IaC Skill 패턴:

```yaml
# .claude/skills/terraform-infrastructure-as-code/SKILL.md
---
name: terraform-infrastructure-as-code
description: Comprehensive Terraform IaC skill
version: 1.0.0
category: Infrastructure
tags: terraform, infrastructure-as-code, cloud, devops, aws
prerequisites: Basic cloud concepts, CLI familiarity, Git knowledge
allowed-tools: [Read, Grep, Glob, Bash]
---
```

**핵심 구성 요소:**
1. **Workflow Rules**: Terraform 라이프사이클 강제 (init → plan → review → apply)
2. **Resource Standards**: 암호화, 태깅, 버전관리 등 기본값 강제
3. **Modularization Strategy**: 모놀리식 방지, modules/ 디렉토리 구조
4. **Validation Protocol**: `terraform fmt` + `terraform validate` 자동 실행
5. **State Management**: 원격 상태, Locking 모범 사례

---

## 3. Skill 작성 Best Practice

### 3.1 디렉토리 구조

```
.claude/skills/
├── aws-cdk-python/
│   ├── SKILL.md                  # 메인 지시 파일
│   └── references/               # 심층 참조 문서
│       ├── common-patterns.md
│       ├── security-defaults.md
│       └── troubleshooting.md
├── aws-cdk-typescript/
│   ├── SKILL.md
│   └── references/
│       └── ...
└── aws-incident-response/
    ├── SKILL.md
    └── references/
        ├── runbooks/
        └── past-incidents.md
```

### 3.2 SKILL.md YAML Frontmatter

```yaml
---
name: aws-cdk-python
description: AWS CDK Python을 사용한 인프라 관리. VPC, Lambda, ECS, RDS 등 AWS 리소스 생성, 수정, 삭제 지원. 보안 기본값, 태깅 정책, 비용 최적화 포함.
version: 1.0.0
category: Infrastructure
tags: aws, cdk, python, infrastructure-as-code, devops
prerequisites: Python 3.9+, AWS CLI, CDK CLI, AWS 계정
allowed-tools: [Read, Grep, Glob, Bash, Write, Edit]
---
```

**`allowed-tools` 중요성:** 도구를 명시하면 AI가 매번 권한을 요청하지 않아 속도가 향상된다.

### 3.3 SKILL.md 본문 구조 (6섹션)

```markdown
# AWS CDK Python Skill

## 1. Workflow Rules (안전장치)
## 2. Resource Standards (코딩 표준)
## 3. Common Patterns (코드 패턴)
## 4. Validation Protocol (검증 절차)
## 5. Error Handling (오류 처리)
## 6. Knowledge Base (참조 정보)
```

### 3.4 CDK Skill을 위한 핵심 섹션

#### Workflow Rules (안전장치)

```markdown
## CDK Workflow Rules
인프라 관리 요청 시, 반드시 다음 라이프사이클을 따를 것:

1. **검토**: 기존 CDK 코드 확인
2. **코드 작성/수정**: CDK Python/TypeScript 코드 생성
3. **검증**: `cdk synth` 실행하여 CloudFormation 템플릿 생성 확인
4. **변경 검토**: `cdk diff` 출력을 사용자에게 제시
5. **승인**: 사용자의 명시적 승인 후에만 `cdk deploy` 실행
6. **검증**: 배포 후 리소스 상태 확인

**절대 하지 말 것:**
- `--require-approval never`를 기본으로 사용하지 않음 (Production)
- `cdk destroy`를 사용자 확인 없이 실행하지 않음
- 보안 그룹을 0.0.0.0/0으로 열지 않음
- S3 버킷에 퍼블릭 접근을 허용하지 않음
```

#### Resource Standards (코딩 표준)

```markdown
## Resource Standards

### S3 Bucket
- 반드시 `versioned=True` 설정
- 반드시 `encryption=s3.BucketEncryption.S3_MANAGED` 설정
- 반드시 `removal_policy=cdk.RemovalPolicy.RETAIN` (Production)
- 필수 태그: `Environment`, `Project`, `ManagedBy=CDK`

### VPC
- 최소 2개 AZ 사용
- NAT Gateway 필수 (Private Subnet 인터넷 접근)
- Flow Logs 활성화

### Lambda
- 최소 Python 3.12 런타임
- 타임아웃 명시적 설정 (기본 30초)
- 메모리 설정 명시적 (기본 256MB)
- Dead Letter Queue 구성

### RDS
- 암호화 활성화
- Multi-AZ (Production)
- 자동 백업 활성화 (7일 이상 보존)
- 삭제 보호 (Production)
```

### 3.5 보안 가드레일 (Skill 내장)

```markdown
## Security Guardrails

### 위험도 분류
| 작업 | 위험도 | 승인 필요 |
|------|--------|-----------|
| 읽기 (list, diff, synth) | LOW | 자동 |
| 리소스 생성 (deploy - 새 스택) | MEDIUM | 사용자 확인 |
| 리소스 수정 (deploy - 기존 스택) | HIGH | 상세 diff 검토 |
| 리소스 삭제 (destroy) | CRITICAL | 2단계 승인 |

### 금지된 패턴
- SecurityGroup에 0.0.0.0/0 인바운드
- S3 퍼블릭 접근 허용
- IAM Role에 `*:*` 권한
- RDS 퍼블릭 접근성
- 암호화 없는 스토리지
```

---

## 4. Agent Skill 오픈 표준

### 4.1 Agent Skills Specification (agentskills.io)

Anthropic, Microsoft, OpenAI, GitHub가 지원하는 오픈 표준:

```
agent-skills/
├── .claude-plugin/
│   ├── plugin.json          # Plugin manifest
│   └── marketplace.json     # Marketplace 배포
├── skills/
│   ├── skill-name/
│   │   ├── SKILL.md         # 지시 파일
│   │   └── references/      # 참조 문서
│   └── ...
├── AGENTS.md                # Cross-tool 라우터
└── README.md
```

### 4.2 AGENTS.md 표준 (Linux Foundation AAIF)

```markdown
# AGENTS.md - Cross-tool Instruction Router

## Skills

| Skill | Trigger | Description |
|-------|---------|-------------|
| aws-cdk-python | "cdk", "인프라", "배포" | AWS CDK Python 인프라 관리 |
| aws-incident | "장애", "에러", "incident" | AWS 장애 대응 |
```

### 4.3 호환 AI 도구

| 도구 | 설치 방법 | Skill 로딩 |
|------|-----------|-----------|
| Claude Code | Plugin Marketplace | 자동 감지 |
| Cursor | `.cursor/rules/` | 수동 |
| GitHub Copilot | VS Code Extension | 수동 |
| OpenAI Codex | `AGENTS.md` | 자동 |
| Gemini CLI | `AGENTS.md` | 자동 |
| Windsurf | `.windsurfrules` | 수동 |
| JetBrains Junie | Plugin | 자동 |

---

## 5. CDK Skill 아키텍처 제안

### 5.1 Skill 계층 구조

```
oh-my-aws/
├── .claude/
│   └── skills/
│       ├── aws-cdk-python/
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── vpc-patterns.md
│       │       ├── serverless-patterns.md
│       │       ├── ecs-patterns.md
│       │       ├── database-patterns.md
│       │       ├── security-defaults.md
│       │       └── cost-optimization.md
│       ├── aws-cdk-typescript/
│       │   └── SKILL.md
│       ├── aws-incident-response/
│       │   ├── SKILL.md
│       │   └── references/
│       │       ├── runbooks/
│       │       └── diagnostic-patterns.md
│       └── aws-cost-management/
│           └── SKILL.md
└── AGENTS.md
```

### 5.2 Skill 활성화 트리거

```yaml
# AGENTS.md
skills:
  - name: aws-cdk-python
    triggers:
      - "cdk", "인프라 생성", "배포", "스택", "VPC 만들어"
      - "lambda 배포", "ECS 설정", "RDS 생성"
    files:
      - "**/*.py"  # Python CDK 파일 열 때 자동 활성화
      - "cdk.json"
      - "**/cdk/**/*.py"

  - name: aws-incident-response
    triggers:
      - "장애", "에러", "다운", "incident", "alert"
      - "CloudWatch 알람", "Lambda 에러", "503"
    files:
      - "**/runbooks/**"
      - "**/incident/**"
```

---

## 6. 검증 및 품질 관리

### 6.1 Skill CI/CD (CloudPosse 사례)

```yaml
# .github/workflows/validate-agent-skills.yml
name: Validate Agent Skills
on: [push, pull_request]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate skill structure
        run: |
          # SKILL.md 존재 확인
          # YAML frontmatter 형식 검증
          # 파일 크기 제한 (50KB)
          # code fence 언어 태그 확인
          # 금지된 패턴 감지
```

### 6.2 Skill 품질 기준

| 기준 | 설명 |
|------|------|
| **명확성** | AI가 모호함 없이 따를 수 있는 지시 |
| **검증 가능성** | 결과가 올바른지 확인 가능 |
| **완전성** | 필요한 모든 컨텍스트 포함 |
| **안전성** | 위험한 작업에 대한 가드레일 |
| **간결성** | 불필요한 토큰 낭비 없음 |

---

## 7. 참고 자료

- [Pulumi Agent Skills 블로그](https://www.pulumi.com/blog/pulumi-agent-skills/)
- [Pulumi Agent Skills 문서](https://pulumi.com/docs/ai/skills/)
- [CloudPosse Atmos Agent Skills PR](https://github.com/cloudposse/atmos/pull/2121)
- [LAXIMA: Building Terraform Skill for Claude Code](https://laxima.tech/blog/building-the-ultimate-terraform-skill-for-claude-code-a-devops-guide)
- [Agent Skills Specification](https://agentskills.io/specification)
- [AGENTS.md Standard](https://agents.md/)
- [SkillMD: Terraform Agent Skill](https://skillmd.ai/how-to-build/terraform-3/)
