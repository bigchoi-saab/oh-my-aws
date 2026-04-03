# AWS 운영자 역할, 페르소나, 필수 기술 및 학습 경로

> 조사일: 2026-04-03
> 목적: AWS 클라우드 운영에 관여하는 역할들을 체계적으로 정리하고, 각 역할의 페르소나(일상 업무), 필요 기술, 학습 자료를 매핑
> 대상: oh-my-aws Agent가 각 운영자 역할의 관점에서 올바른 지원을 제공하기 위한 기준

---

## 1. 역할 전체 맵

### 1.1 역할 분류 체계

```
                        ┌─────────────────────────────────┐
                        │         AWS 운영 조직            │
                        └──────────┬──────────────────────┘
                                   │
           ┌───────────────────────┼───────────────────────┐
           │                       │                       │
    ┌──────▼──────┐        ┌──────▼──────┐        ┌──────▼──────┐
    │ 인프라 운영  │        │ 애플리케이션 │        │  플랫폼      │
    │ Infrastructure│       │ Application  │        │  Platform    │
    └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
           │                       │                       │
    ┌──────┴──────┐        ┌──────┴──────┐        ┌──────┴──────┐
    │· Cloud/Infra│        │· SRE        │        │· Platform   │
    │  Engineer   │        │· DevOps Eng. │        │  Engineer   │
    │· Network Eng│        │· On-Call Eng│        │· FinOps Eng.│
    │· DBA(Cloud) │        │             │        │· Security   │
    │· SysOps     │        │             │        │  Operations │
    └─────────────┘        └─────────────┘        └─────────────┘
```

### 1.2 역할별 책임 영역 한눈에 보기

| 역할 | 주요 책임 | 관여 단계 | 장애 대응 역할 |
|------|----------|----------|--------------|
| **Cloud Infrastructure Engineer** | AWS 리소스 프로비저닝, IaC, 네트워크 | 설계·구축·운영 | Ops Lead |
| **SRE (Site Reliability Engineer)** | 신뢰성, SLO/SLI, 자동화, 장애 대응 | 전 단계 | IC 또는 Ops Lead |
| **DevOps Engineer** | CI/CD, 배포 자동화, 도구 체인 | 개발·배포·운영 | Ops Lead |
| **Platform Engineer** | 개발자 플랫폼, 셀프서비스, 템플릿 | 설계·구축 | 인프라 지원 |
| **Cloud DBA** | 데이터베이스 설계·운영, 성능 튜닝 | 설계·운영 | DB 전문가 |
| **Network Engineer (Cloud)** | VPC, 연결성, DNS, 보안 그룹 | 설계·운영 | 네트워크 전문가 |
| **Security Operations (SecOps)** | 보안 모니터링, 침해 대응, 컴플라이언스 | 전 단계 | 보안 전문가 |
| **FinOps Engineer** | 비용 최적화, 예산 관리, 사용량 분석 | 운영 | 재무 지원 |
| **On-Call Engineer** | 1차 장애 수신, 분류, 에스컬레이션 | 운영 (비상) | 1차 응답 |
| **Cloud Architect** | 아키텍처 설계, Well-Architected 리뷰 | 설계 | 아키텍처 자문 |

---

## 2. 역할별 상세 정리

### 2.1 Cloud Infrastructure Engineer (클라우드 인프라 엔지니어)

#### 페르소나

```
이름: "인프라 김대호"
경력: 5-8년 (전통 인프라 → 클라우드 전환 경험)

하루 일과:
09:00 - CDK/Terraform 코드 리뷰 (PR 승인)
10:00 - 신규 VPC 설계 검토 (3-Tier 아키텍처)
11:00 - ECS 클러스터 용량 계획 수립
13:00 - AWS Config 규칙 위반 항목 처리
14:00 - cdktf diff 확인 후 프로덕션 배포 승인
15:00 - 인프라 비용 리포트 검토 (사용량 변화 분석)
16:00 - Runbook 업데이트 (이번 주 장애 교훈 반영)
17:00 - 온콜 인수인계 (P1 알람 대응 절차 공유)

주요 고민:
  "이 CDK 변경이 프로덕션에 어떤 영향을 줄까?"
  "이 리소스 구성이 Well-Architected 기준에 맞는가?"
  "장애 발생 시 롤백은 어떻게?"
```

#### 일상 업무

| 업무 | 빈도 | 도구 |
|------|------|------|
| IaC 코드 작성/리뷰 (CDK, Terraform) | 매일 | Git, CDK CLI, Terraform CLI |
| AWS 리소스 프로비저닝/변경 | 매일 | AWS Console, CLI, CDK |
| 인프라 아키텍처 설계 | 주간 | draw.io, Cloudcraft |
| 용량 계획 및 비용 분석 | 주간 | AWS Cost Explorer, CUR |
| Well-Architected 리뷰 | 월간 | AWS WA Tool |
| 인프라 보안 점검 | 주간 | AWS Config, AWS Audit Manager |
| Runbook/가이드 업데이트 | 격주 | Confluence, Git |
| 온콜 대기 (1차/2차) | 격주 교대 | PagerDuty, Slack |

#### 필수 기술

| 기술 영역 | 상세 | 수준 |
|----------|------|------|
| **AWS 핵심 서비스** | VPC, EC2, ECS/EKS, S3, RDS, IAM, CloudWatch | 전문가 |
| **IaC (Infrastructure as Code)** | AWS CDK (TypeScript/Python), Terraform | 전문가 |
| **네트워킹** | VPC 설계, 서브넷/라우팅, Transit Gateway, VPN/Direct Connect | 고급 |
| **보안** | IAM 정책, KMS, Secrets Manager, AWS Organizations | 고급 |
| **CI/CD** | CodePipeline, GitHub Actions, ArgoCD | 중급 |
| **모니터링** | CloudWatch, X-Ray, 로그 분석 | 고급 |
| **스크립팅** | Python, Bash | 중급 |
| **Git** | 브랜치 전략, 코드 리뷰, PR 워크플로우 | 고급 |

#### 학습 자료

| 자료 | 유형 | 내용 |
|------|------|------|
| **AWS Solutions Architect Professional** | 자격증 | 전체 AWS 서비스 설계·운영 종합 |
| **AWS Well-Architected Framework** (6개 Pillar) | 공식 문서 | 안전·신뢰·성능·비용·운영·지속가능 설계 원칙 |
| **AWS CDK 개발자 가이드** | 공식 문서 | CDK Construct 설계, 배포, 테스트 |
| **AWS Cloud Adoption Framework** | 백서 | 클라우드 도입 전략, 역할 모델 |
| **AWS Infrastructure Event Management** | 백서 | 대규모 이벤트(블랙프라이데이 등) 인프라 준비 |
| **HashiCorp Terraform Associate** | 자격증 | Terraform 모듈·상태·워크플로우 |
| **Amazon Builders' Library** | 아티클 | 아마존 내부 실무 문서 (분산 시스템, 장애 대응) |

---

### 2.2 SRE (Site Reliability Engineer)

#### 페르소나

```
이름: "신뢰성 박서린"
경력: 4-7년 (소프트웨어 엔지니어링 + 운영 경험)

하루 일과:
09:00 - SLO 대시보드 확인 (어제 Error Budget 소진율)
09:30 - Toil(반복 수동 작업) 자동화 스크립트 작성
10:30 - 장애 Post-Mortem 액션 아이템 처리
11:30 - 신규 서비스 SLO/SLI 정의 회의
13:00 - Chaos Engineering 실험 설계 (Latency Injection)
14:00 - On-Call 핸드오프 미팅 (이번 주 인시던트 리뷰)
15:00 - 배포 Canary 메트릭 자동 검증 로직 개발
16:00 - 시스템 병목 분석 (p99 지연 원인 추적)
17:00 - Runbook as Code 작성

주요 고민:
  "이 서비스의 SLO는 99.9%인데, Error Budget이 얼마나 남았나?"
  "이 장애를 자동으로 감지하고 완화할 수 있는가?"
  "On-Call 엔지니어가 3AM에도 올바르게 대응할 수 있는가?"
```

#### 일상 업무

| 업무 | 빈도 | 도구 |
|------|------|------|
| SLO/SLI 모니터링 & Error Budget 추적 | 매일 | Datadog, Grafana, CloudWatch |
| 장애 대응 & 인시던트 관리 | 발생 시 | PagerDuty, Slack, Zoom |
| Toil 자동화 (수동 작업 제거) | 매일 | Python, Lambda, Step Functions |
| Post-Mortem 작성 & 액션 추적 | 장애 후 | Confluence, Jira |
| Runbook 작성/갱신 | 주간 | Git, Markdown |
| 시스템 성능 분석 & 병목 제거 | 주간 | X-Ray, CloudWatch, Flame Graphs |
| 배포 안전성 검증 (Canary/Blue-Green) | 배포 시 | Argo Rollouts, CodeDeploy |
| Chaos Engineering 실험 | 월간 | AWS FIS, Chaos Monkey, Litmus |
| On-Call 순환 (보통 1주 교대) | 격주~월1 | PagerDuty |

#### 필수 기술

| 기술 영역 | 상세 | 수준 |
|----------|------|------|
| **시스템 신뢰성** | SLO/SLI/SLA, Error Budget, Error Budget Policy | 전문가 |
| **장애 대응** | 인시던트 라이프사이클, Blameless Post-Mortem, 에스컬레이션 | 전문가 |
| **관측성(Observability)** | Metrics, Logs, Traces 상관 분석, 대시보드 설계 | 전문가 |
| **프로그래밍** | Python/Go/TypeScript (자동화 스크립트, 도구 개발) | 고급 |
| **분산 시스템** | CAP, 일관성 모델, 재시도/서킷브레이커/벌크헤드 | 고급 |
| **IaC** | CDK/Terraform (인프라 변경 자동화) | 중급~고급 |
| **CI/CD** | 파이프라인 설계, 배포 전략, 롤백 자동화 | 고급 |
| **Linux/컨테이너** | 트러블슈팅, Docker, Kubernetes/ECS | 고급 |
| **데이터 분석** | 메트릭 통계, p50/p95/p99 이해, 이상 탐지 | 중급 |

#### 학습 자료

| 자료 | 유형 | 내용 |
|------|------|------|
| **Google SRE Book** | 도서 (무료 온라인) | SLO, Error Budget, On-Call, Incident Response, Post-Mortem |
| **Google SRE Workbook** | 도서 (무료 온라인) | SRE 실무 구현 가이드 (Concret SLO, Alerting) |
| **AWS Well-Architected Reliability Pillar** | 공식 문서 | 장애 격리, 복구, DR 전략 |
| **AWS DevOps Engineer Professional** | 자격증 | CI/CD, IaC, 모니터링, 자동화 종합 |
| **Building Secure & Reliable Systems (Google)** | 도서 (무료) | 보안 + 신뢰성 교차 영역 |
| **Chaos Engineering (Casey Rosenthal)** | 도서 | 카오스 엔지니어링 원리와 실무 |
| **Amazon Builders' Library** | 아티클 | 분산 시스템, 장애 격리, 배포 안전성 |
| **AWS Fault Injection Simulator (FIS)** | 서비스 | AWS 환경에서 카오스 실험 실행 |

---

### 2.3 DevOps Engineer

#### 페르소나

```
이름: "배포 이민수"
경력: 3-6년 (개발 + 운영 경험)

하루 일과:
09:00 - CI 파이프라인 실패 원인 분석 (Flaky Test?)
10:00 - 신규 마이크로서비스 배포 파이프라인 구성
11:00 - ECS Blue/Green 배포 자동화 스크립트 작성
13:00 - 배포 후 Smoke Test 결과 확인
14:00 - 개발팀 요청: 새 환경(Staging) 프로비저닝
15:00 - Docker 이미지 최적화 (멀티스테이지 빌드, 레이어 캐싱)
16:00 - GitOps 워크플로우 개선 (ArgoCD Sync 문제 해결)
17:00 - 배포 Runbook 업데이트

주요 고민:
  "이 배포가 프로덕션을 망가뜨리지 않을까?"
  "롤백은 30초 안에 가능한가?"
  "배포 파이프라인이 15분 이내에 끝나는가?"
```

#### 일상 업무

| 업무 | 빈도 | 도구 |
|------|------|------|
| CI/CD 파이프라인 구축/유지보수 | 매일 | GitHub Actions, CodePipeline, Jenkins |
| 배포 자동화 (Blue/Green, Canary, Rolling) | 매일 | CodeDeploy, ArgoCD, Flagger |
| 컨테이너 이미지 빌드/관리 | 매일 | Docker, ECR, Buildpacks |
| 환경 프로비저닝 (Dev/Staging/Prod) | 주간 | CDK, Terraform, Helm |
| 배포 모니터링 & 롤백 | 배포 시 | CloudWatch, Datadog |
| 보안 스캔 (이미지/IaC/의존성) | 파이프라인 내 | Trivy, Checkov, Snyk |
| GitOps 워크플로우 관리 | 주간 | ArgoCD, Flux |
| 배포 관련 Runbook 작성 | 격주 | Confluence, Git |

#### 필수 기술

| 기술 영역 | 상세 | 수준 |
|----------|------|------|
| **CI/CD 도구** | GitHub Actions, CodePipeline, Jenkins, GitLab CI | 전문가 |
| **배포 전략** | Blue/Green, Canary, Rolling, Feature Flag | 전문가 |
| **컨테이너** | Docker, ECR, ECS, EKS, Helm, Kustomize | 고급 |
| **IaC** | CDK, Terraform, CloudFormation | 고급 |
| **GitOps** | ArgoCD, Flux, Git 워크플로우 | 중급~고급 |
| **보안** | 이미지 스캔, IaC 스캔, SBOM, 서명 | 중급 |
| **스크립팅** | Bash, Python, Makefile | 고급 |
| **AWS 서비스** | CodeBuild, CodeDeploy, CodeCommit, ECR, ECS/EKS | 고급 |

#### 학습 자료

| 자료 | 유형 | 내용 |
|------|------|------|
| **AWS DevOps Engineer Professional** | 자격증 | CI/CD, IaC, 모니터링, 자동화 |
| **The Phoenix Project** | 도서 | DevOps 문화와 실무 (소설 형식) |
| **Accelerate (DORA)** | 도서 | 배포 성숙도, 4개 핵심 메트릭 |
| **AWS CDK 개발자 가이드** | 공식 문서 | CDK로 인프라 코드화 |
| **GitHub Actions 공식 문서** | 공식 문서 | 워크플로우, 커스텀 액션, Runner |
| **ArgoCD 문서** | 오픈소스 문서 | GitOps 패턴, Sync 전략 |
| **Docker 공식 튜토리얼** | 튜토리얼 | 이미지 빌드 최적화, 멀티스테이지 |
| **DORA State of DevOps Report** | 연례 보고서 | 배포 성숙도 벤치마크 |

---

### 2.4 Platform Engineer (플랫폼 엔지니어)

#### 페르소나

```
이름: "플랫폼 정하윤"
경력: 5-10년 (인프라 + 개발 + 아키텍처)

하루 일과:
09:00 - Internal Developer Platform(IDP) 백로그 리뷰
10:00 - 개발팀 요구사항 분석: "ECS 서비스를 셀프서비스로 만들어주세요"
11:00 - 서비스 템플릿(CDK Construct Library) 설계
13:00 - 플랫폼 API 개발 (인프라 프로비저닝 자동화)
14:00 - 개발자 문서 작성 (How-to 가이드)
15:00 - 플랫폼 메트릭 리뷰 (셀프서비스 사용률, 프로비저닝 리드타임)
16:00 - Crossplane/AWS Proton 설정
17:00 - Golden Path 템플릿 업데이트

주요 고민:
  "개발자가 인프라 팀 없이 서비스를 배포할 수 있는가?"
  "모든 팀이 동일한 보안/규정 준수 기준을 따르고 있는가?"
  "플랫폼이 개발자 생산성을 높이고 있는가, 아니면 방해하고 있는가?"
```

#### 일상 업무

| 업무 | 빈도 | 도구 |
|------|------|------|
| Internal Developer Platform 설계/개발 | 매일 | AWS Proton, Crossplane, Backstage |
| CDK Construct Library 유지보수 | 매일 | AWS CDK, TypeScript/Python |
| 서비스 템플릿(Golden Path) 관리 | 주간 | CDK, Terraform Module, Helm Chart |
| 셀프서비스 포털 개발/유지보수 | 주간 | Backstage, Custom Portal |
| 개발자 문서 작성 | 주간 | Markdown, Docusaurus |
| 플랫폼 보안 가드레일 구현 | 격주 | OPA, AWS Config, Service Control Policy |
| 플랫폼 사용률 분석 | 월간 | Custom Metrics, Developer Survey |

#### 필수 기술

| 기술 영역 | 상세 | 수준 |
|----------|------|------|
| **AWS 전 서비스 이해** | 컴퓨트/스토리지/네트워크/보안/데이터 전반 | 전문가 |
| **CDK Construct 설계** | L2/L3 Construct, CDK Library 아키텍처 | 전문가 |
| **개발자 경험(DX)** | 셀프서비스, Golden Path, 내부 문서 | 고급 |
| **소프트웨어 엔지니어링** | API 설계, 라이브러리 설계, 버전 관리 | 고급 |
| **보안 정책 as Code** | OPA/Rego, AWS SCP, Config Rules | 고급 |
| **플랫폼 도구** | Backstage, AWS Proton, Crossplane | 중급~고급 |
| **컨테이너 오케스트레이션** | ECS, EKS, Helm | 고급 |
| **관측성** | CloudWatch, OpenTelemetry, 대시보드 | 중급~고급 |

#### 학습 자료

| 자료 | 유형 | 내용 |
|------|------|------|
| **Team Topologies** | 도서 | 팀 구조, 플랫폼 팀 역할, 스트림 정렬 |
| **Platform Engineering on Kubernetes** | 도서/강의 | IDP 설계 원칙 |
| **AWS Proton 문서** | 공식 문서 | 관리형 플랫폼 엔지니어링 서비스 |
| **Spotify Backstage 문서** | 오픈소스 | 개발자 포털 아키텍처 |
| **CDK Construct Library 가이드** | 공식 문서 | 재사용 가능한 Construct 설계 패턴 |
| **AWS Solutions Constructs** | 공식 패턴 | AWS 검증 아키텍처 패턴 라이브러리 |
| **Platform Engineering Community** | 커뮤니티 | CNCF 플랫폼 엔지니어링 실무 공유 |
| **AWS Well-Architected Framework** | 공식 문서 | 6개 Pillar 기반 설계 원칙 |

---

### 2.5 Cloud DBA (클라우드 데이터베이스 관리자)

#### 페르소나

```
이름: "데이터 최지훈"
경력: 5-10년 (온프레미스 DBA → 클라우드 DBA 전환)

하루 일과:
09:00 - RDS/Aurora 클러스터 상태 확인 (CPU, 연결수, 복제지연)
09:30 - Performance Insights 슬로우 쿼리 리뷰
10:00 - 신규 인덱스 추가 요청 검토 (실행계획 분석)
11:00 - DB 파라미터 그룹 변경 리뷰 (work_mem 등)
13:00 - 읽기 복제본 추가 (트래픽 증가 대응)
14:00 - 자동 백업 복원 테스트 (RTO 검증)
15:00 - 데이터베이스 마이그레이션 계획 수립 (Major Version Upgrade)
16:00 - 애플리케이션 팀과 쿼리 최적화 페어 세션
17:00 - DB 관련 Runbook 업데이트

주요 고민:
  "이 쿼리가 프로덕션을 먹통으로 만들지 않을까?"
  "페일오버 시 데이터 손실이 없는가?"
  "스토리지가 고갈되기 전에 확보할 수 있는가?"
```

#### 일상 업무

| 업무 | 빈도 | 도구 |
|------|------|------|
| DB 인스턴스 상태 모니터링 | 매일 | CloudWatch, Performance Insights |
| 슬로우 쿼리 분석/튜닝 | 매일 | Explain Analyze, pg_stat_statements |
| 스키마 변경 관리 (Migration) | 주간 | Flyway, Liquibase, pg_dump |
| 백업/복구 검증 | 주간 | AWS Backup, RDS Snapshot |
| 읽기 복제본 관리 | 필요 시 | RDS API, Aurora 클론 |
| DB 파라미터 튜닝 | 격주 | RDS Parameter Group |
| 용량 계획 | 월간 | CloudWatch Metrics, Cost Explorer |
| 장애 대응 (페일오버, 성능 저하) | 발생 시 | RDS Console, CW Logs |

#### 필수 기술

| 기술 영역 | 상세 | 수준 |
|----------|------|------|
| **데이터베이스 엔진** | PostgreSQL, MySQL, Aurora 특성 | 전문가 |
| **성능 튜닝** | 실행계획 분석, 인덱스 설계, 파라미터 튜닝 | 전문가 |
| **AWS 데이터 서비스** | RDS, Aurora, DynamoDB, ElastiCache | 고급 |
| **백업/복구** | RDS Snapshot, PITR, AWS Backup | 고급 |
| **고가용성** | Multi-AZ, 읽기 복제본, 페일오버 | 고급 |
| **SQL** | 복잡한 쿼리 작성, 최적화 | 전문가 |
| **데이터 마이그레이션** | DMS, Schema Conversion Tool | 중급 |
| **보안** | 암호화, IAM 데이터베이스 인증, 감사 로그 | 중급 |

#### 학습 자료

| 자료 | 유형 | 내용 |
|------|------|------|
| **AWS Database Specialty** | 자격증 | AWS 데이터베이스 설계·운영 종합 |
| **RDS 모범 사례 (서비스별)** | 공식 문서 | PostgreSQL/MySQL/Aurora 운영 가이드 |
| **Performance Insights 사용 가이드** | 공식 문서 | DB 성능 분석, 대기 이벤트 해석 |
| **Amazon Aurora 설계 가이드** | 백서 | Aurora 아키텍처, 성능, 운영 |
| **Use the Index, Luke** | 온라인 도서 | 인덱스 설계와 실행계획 (무료) |
| **PostgreSQL 공식 문서** | 공식 문서 | 튜닝, 모니터링, WAL, 복제 |
| **AWS DMS 모범 사례** | 공식 문서 | 데이터베이스 마이그레이션 전략 |
| **AWS Well-Architected Data Analytics Lens** | 공식 문서 | 데이터 파이프라인 설계 원칙 |

---

### 2.6 Network Engineer — Cloud (클라우드 네트워크 엔지니어)

#### 페르소나

```
이름: "네트워크 한서영"
경력: 5-8년 (네트워크 엔지니어 → 클라우드 네트워크 전환)

하루 일과:
09:00 - VPC Flow Logs 리뷰 (비정상 REJECT 패턴 확인)
09:30 - Transit Gateway 라우팅 테이블 업데이트
10:30 - Cross-Account VPC Peering 연결 설정
11:30 - VPN 연결 상태 모니터링 (온프레미스 연동)
13:00 - Security Group 규칙 최소화 검토
14:00 - DNS 설계 리뷰 (Route 53 Private Hosted Zone)
15:00 - 네트워크 트러블슈팅 (Reachability Analyzer 활용)
16:00 - 네트워크 아키텍처 문서 업데이트
17:00 - 새 VPC 설계 요구사항 분석

주요 고민:
  "이 트래픽이 왜 차단되고 있지?"
  "Transit Gateway가 병목인가?"
  "DNS 해석이 왜 간헐적으로 실패하지?"
```

#### 일상 업무

| 업무 | 빈도 | 도구 |
|------|------|------|
| VPC 설계/관리 | 주간 | VPC Console, CDK |
| 라우팅/피어링/TGW 관리 | 주간 | VPC Console, CLI |
| Security Group / NACL 관리 | 주간 | EC2 Console, CDK |
| DNS 관리 (Route 53) | 주간 | Route 53 Console |
| VPN/Direct Connect 관리 | 격주 | VPN Console, CloudWatch |
| VPC Flow Logs 분석 | 장애 시 | CW Logs Insights, Athena |
| 네트워크 트러블슈팅 | 장애 시 | Reachability Analyzer, VPC Flow Logs |
| 네트워크 아키텍처 문서화 | 월간 | draw.io, Cloudcraft |

#### 필수 기술

| 기술 영역 | 상세 | 수준 |
|----------|------|------|
| **AWS 네트워킹** | VPC, Subnet, Route Table, IGW, NAT, TGW, VPC Peering | 전문가 |
| **보안 그룹 / NACL** | 상태 저장/비저장 방화벽, 규칙 설계 | 전문가 |
| **DNS** | Route 53 (Public/Private), Resolver, Health Checks | 고급 |
| **하이브리드 연결** | VPN, Direct Connect, Transit Gateway | 고급 |
| **네트워크 트러블슈팅** | VPC Flow Logs, Reachability Analyzer, tcpdump | 고급 |
| **IaC** | CDK/Terraform로 네트워크 리소스 관리 | 중급~고급 |
| **TCP/IP 기초** | L3/L4 프로토콜, 서브네팅, CIDR | 전문가 |
| **모니터링** | CloudWatch, VPC Flow Logs, NAT Gateway 메트릭 | 고급 |

#### 학습 자료

| 자료 | 유형 | 내용 |
|------|------|------|
| **AWS Advanced Networking Specialty** | 자격증 | AWS 네트워크 설계·운영 종합 |
| **AWS VPC 사용 가이드** | 공식 문서 | VPC, 서브넷, 라우팅, Flow Logs |
| **AWS Transit Gateway 설계 패턴** | 백서 | Multi-Account 네트워크 아키텍처 |
| **Route 53 개발자 가이드** | 공식 문서 | DNS 페일오버, 헬스체크, 라우팅 정책 |
| **AWS Hybrid Connectivity** | 백서 | VPN, Direct Connect 아키텍처 |
| **Reachability Analyzer 가이드** | 공식 문서 | 네트워크 경로 분석 |
| **Wireshark/TCPDump 기초** | 튜토리얼 | 패킷 캡처 분석 기초 |

---

### 2.7 Security Operations (SecOps)

#### 페르소나

```
이름: "보안 강도현"
경력: 5-10년 (정보보안 + 클라우드 보안)

하루 일과:
09:00 - GuardDuty Finding 대시보드 확인
09:30 - AWS Config 비준수 리소스 처리
10:30 - IAM 권한 리뷰 (과도한 권한 최소화)
11:30 - 보안 이벤트 조사 (의심스러운 로그인 패턴)
13:00 - 취약점 스캔 결과 리뷰 (Inspector)
14:00 - 보안 정책 업데이트 (SCP, WAF 규칙)
15:00 - 컴플라이언스 리포트 작성 (SOC2, ISO27001)
16:00 - 보안 인시던트 대응 훈련 (Tabletop Exercise)
17:00 - 보안 Runbook 업데이트

주요 고민:
  "이 IAM Role이 과도한 권한을 가지고 있지 않은가?"
  "이 EC2 인스턴스가 암호화폐 채굴에 사용되고 있는가?"
  "S3 버킷이 공개 접근 가능한가?"
```

#### 일상 업무

| 업무 | 빈도 | 도구 |
|------|------|------|
| 보안 위협 모니터링 | 매일 | GuardDuty, Security Hub, Detective |
| IAM 권한 관리/리뷰 | 매일 | IAM Console, IAM Access Analyzer |
| 취약점 관리 | 주간 | Inspector, Systems Manager Patch Manager |
| 컴플라이언스 준수 확인 | 주간 | AWS Config, Audit Manager |
| 보안 인시던트 대응 | 발생 시 | GuardDuty, CloudTrail, Macie |
| WAF/Shield 관리 | 격주 | WAF Console, Shield |
| 암호화 키 관리 | 격주 | KMS, CloudHSM |
| 보안 교육/훈련 | 월간 | Tabletop Exercise, Game Day |

#### 필수 기술

| 기술 영역 | 상세 | 수준 |
|----------|------|------|
| **AWS 보안 서비스** | GuardDuty, Security Hub, Inspector, Macie, Detective | 전문가 |
| **IAM** | 정책 설계, 최소 권한, SCP, Permission Boundary | 전문가 |
| **데이터 보호** | KMS, 암호화, S3 버킷 정책, Secrets Manager | 고급 |
| **네트워크 보안** | SG, NACL, WAF, Shield, VPC Endpoint | 고급 |
| **컴플라이언스** | SOC2, ISO27001, PCI-DSS, HIPAA | 중급~고급 |
| **침해 대응(IR)** | 포렌식, 증거 보존, 격리, 복구 | 고급 |
| **보안 자동화** | Lambda, Step Functions (대응 자동화) | 중급 |
| **로깅/감사** | CloudTrail, Config, VPC Flow Logs | 고급 |

#### 학습 자료

| 자료 | 유형 | 내용 |
|------|------|------|
| **AWS Security Specialty** | 자격증 | AWS 보안 설계·운영 종합 |
| **AWS Security Best Practices** | 백서 | 계정/네트워크/데이터 보안 가이드 |
| **AWS Incident Response Guide** | 공식 문서 | 보안 인시던트 대응 절차 |
| **AWS Well-Architected Security Pillar** | 공식 문서 | 보안 설계 원칙 |
| **NIST Cybersecurity Framework** | 프레임워크 | 식별·보호·탐지·대응·복구 |
| **MITRE ATT&CK for Cloud** | 프레임워크 | 클라우드 공격 기법 매트릭스 |
| **CIS AWS Foundations Benchmark** | 벤치마크 | AWS 보안 기준 체크리스트 |
| **AWS Security Blog** | 블로그 | 최신 보안 기능과 모범 사례 |

---

### 2.8 FinOps Engineer (클라우드 재무 운영)

#### 페르소나

```
이름: "비용 최수진"
경력: 3-6년 (재무 분석 + 클라우드 기술)

하루 일과:
09:00 - 전일 AWS 비용 리포트 확인 (이상 징후 탐지)
09:30 - 사용하지 않는 리소스 정리 (Idle EBS, 미사용 EIP)
10:30 - RI/ Savings Plans 커버리지 분석
11:30 - 팀별 비용 배분 리포트 작성 (태그 기반)
13:00 - 비용 이상 알람 설정 (일일 임계값 초과)
14:00 - 새 서비스 비용 예측 모델링
15:00 - 개발팀과 비용 최적화 워크숍
16:00 - AWS Cost Explorer 커스텀 리포트 생성
17:00 - 월간 비용 리뷰 발표 자료 준비

주요 고민:
  "이 달에 왜 비용이 30% 올랐지?"
  "RI를 더 구매해야 하는가, 아님 Savings Plans가 나은가?"
  "이 리소스가 진짜 필요한 건가?"
```

#### 일상 업무

| 업무 | 빈도 | 도구 |
|------|------|------|
| 일일 비용 모니터링 | 매일 | Cost Explorer, CUR (Cost & Usage Report) |
| 비용 이상 탐지 | 매일 | AWS Budgets, Anomaly Detection |
| 미사용 리소스 정리 | 주간 | Trusted Advisor, Compute Optimizer |
| RI/SP 커버리지 분석 | 주간 | Cost Explorer, RI Coverage Report |
| 팀/프로젝트별 비용 배분 | 월간 | 태그 기반 CUR 분석, Athena |
| 비용 예측 & 예산 관리 | 월간 | Cost Explorer Forecast, Budgets |
| 비용 최적화 권장사항 리뷰 | 주간 | Trusted Advisor, Compute Optimizer |
| FinOps 교육/문화 전파 | 격월 | 워크숍, 뉴스레터 |

#### 필수 기술

| 기술 영역 | 상세 | 수준 |
|----------|------|------|
| **AWS 비용 관리** | Cost Explorer, CUR, Budgets, Cost Anomaly Detection | 전문가 |
| **요금 모델 이해** | On-Demand, RI, Savings Plans, Spot, Fargate 비용 구조 | 전문가 |
| **데이터 분석** | Athena로 CUR 쿼리, QuickSight 대시보드 | 고급 |
| **태그 전략** | 비용 배분 태그, 태그 정책, Cost Categories | 고급 |
| **리소스 최적화** | Right-sizing, 미사용 리소스, 스토리지 계층화 | 고급 |
| **AWS 서비스 이해** | 주요 서비스의 비용 구조 이해 | 중급~고급 |
| **스프레드시트/BI** | Excel/Sheets 피벗, QuickSight, Grafana | 중급 |
| **FinOps 프레임워크** | Inform → Optimize → Operate | 중급 |

#### 학습 자료

| 자료 | 유형 | 내용 |
|------|------|------|
| **FinOps 교육 (FinOps.org)** | 인증/과정 | FinOps Practitioner, FinOps Professional |
| **Cloud FinOps (O'Reilly)** | 도서 | FinOps 프레임워크와 실무 |
| **AWS Cost Management 문서** | 공식 문서 | Cost Explorer, CUR, Budgets 사용법 |
| **AWS Well-Architected Cost Pillar** | 공식 문서 | 비용 최적화 설계 원칙 |
| **AWS Pricing 공식 문서** | 공식 문서 | 서비스별 요금 구조 |
| **AWS Cost & Usage Report (CUR) 쿼리 라이브러리** | GitHub | Athena 비용 분석 쿼리 모음 |

---

### 2.9 On-Call Engineer (온콜 엔지니어)

#### 페르소나

```
이름: "온콜 박준서" (순환 역할, 고정 인물 아님)
경력: 2-5년 (SRE/DevOps/인프라 중 1순위)

알림 수신 시 (3:00 AM):
03:00 - PagerDuty 알림 수신 → 스마트폰 확인
03:02 - 알림 Acknowledge (확인 응답)
03:05 - 노트북 열고 VPN 접속
03:07 - Slack 인시던트 채널 확인
03:10 - CloudWatch 대시보드 빠르게 스캔
03:15 - 영향 범위 판단:
        · 내가 해결할 수 있는가? → Runbook 실행
        · 에스컬레이션이 필요한가? → IC/전문가 호출
03:30 - 조치 후 모니터링
04:00 - 해결 확인 또는 에스컬레이션

주요 고민:
  "이게 진짜 장애인가, 노이즈인가?"
  "내가 이걸 해결할 수 있는가, 누구를 불러야 하나?"
  "Runbook이 있는가? 최신 상태인가?"
```

#### 일상 업무 (온콜 교대 기간)

| 업무 | 빈도 | 도구 |
|------|------|------|
| 알림 수신 → Acknowledge | 발생 시 | PagerDuty, Opsgenie |
| 초기 분류 (심각도 판단) | 알림 시 | CloudWatch, Slack |
| Runbook 실행 | 알림 시 | Runbook Wiki, Git |
| 에스컬레이션 (필요 시) | 필요 시 | Slack, 전화, PagerDuty |
| 장애 타임라인 기록 | 장애 시 | 인시던트 채널 |
| 인수인계 (Shift 변경 시) | 교대 시 | Slack, Handoff 문서 |
| 온콜 핸드북 유지보수 | 격주 | Confluence, Git |

#### 필수 기술

| 기술 영역 | 상세 | 수준 |
|----------|------|------|
| **장애 분류** | 노이즈 vs 실제 장애, 영향 범위 판단 | 중급~고급 |
| **AWS 모니터링 도구** | CloudWatch 대시보드, Logs Insights 기본 | 중급 |
| **Runbook 실행** | 정해진 절차를 정확하게 수행 | 중급 |
| **에스컬레이션 판단** | 언제 도움을 요청해야 하는지 아는 것 | 고급 |
| **커뮤니케이션** | 상황 전달, 타임라인 기록, 인수인계 | 고급 |
| **기본 AWS 트러블슈팅** | Lambda, ECS, RDS 기본 진단 | 중급 |
| **IAM/보안 기본** | 최소 권한으로 조치, 위험한 행위 방지 | 중급 |
| **문서화** | 조치 내용 기록, Runbook 피드백 | 중급 |

#### 학습 자료

| 자료 | 유형 | 내용 |
|------|------|------|
| **Google SRE - Being On-Call** | 온라인 도서 (무료) | 온콜 엔지니어 역할, 근무 시간, 스트레스 관리 |
| **PagerDuty On-Call Best Practices** | 가이드 | 알림 관리, 에스컬레이션, 워라밸 |
| **AWS CloudWatch 기본** | 공식 튜토리얼 | 대시보드, 알람, Logs 기본 |
| **팀 내 Runbook 모음** | 내부 문서 | 각 서비스별 장애 대응 절차 |
| **AWS re:Post Knowledge Center** | 커뮤니티 | 서비스별 트러블슈팅 Q&A |
| **Incident Response for On-Call** | 가이드 | 초기 대응, 분류, 에스컬레이션 |

---

## 3. 역할 간 협업 맵

### 3.1 장애 발생 시 역할 간 상호작용

```
[장애 감지]
    │
    ▼
On-Call Engineer ←─ 알림
    │
    ├─ 초기 분류 ──→ "내가 처리 가능" → Runbook 실행 → 해결
    │
    └─ "에스컬레이션 필요" ──→ SRE/IC 선임
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Cloud Infra Eng   DevOps Eng     Cloud DBA
              (인프라 장애)      (배포 장애)     (DB 장애)
                    │               │               │
                    ├───────────────┼───────────────┤
                    ▼               ▼               ▼
              Network Eng      Platform Eng    SecOps
              (네트워크 장애)    (플랫폼 장애)    (보안 장애)
                    │               │               │
                    └───────────────┼───────────────┘
                                    ▼
                              FinOps Eng
                              (비용 영향 분석)
                                    │
                                    ▼
                            Cloud Architect
                            (아키텍처 개선)
```

### 3.2 일상 운영에서의 협업

| 상황 | 주도 역할 | 협업 역할 | 산출물 |
|------|----------|----------|--------|
| 신규 서비스 인프라 구축 | Cloud Infra Engineer | Platform Eng, Network Eng, SecOps | CDK Stack + 아키텍처 문서 |
| 배포 파이프라인 구축 | DevOps Engineer | Cloud Infra Eng, Platform Eng, SecOps | CI/CD 파이프라인 + Runbook |
| SLO 설정 | SRE | 서비스 개발팀, Cloud Infra Eng | SLO/SLI 정의서 + 알람 |
| 비용 최적화 | FinOps Engineer | Cloud Infra Eng, 모든 팀 | 비용 리포트 + 최적화 권장 |
| 보안 감사 | SecOps | Cloud Infra Eng, DevOps Eng | 컴플라이언스 리포트 |
| DR 훈련 | SRE | Cloud Infra Eng, Network Eng, DBA | DR Runbook + 훈련 결과 |
| 데이터베이스 마이그레이션 | Cloud DBA | DevOps Eng, SRE, Cloud Infra Eng | 마이그레이션 계획서 |
| 네트워크 아키텍처 변경 | Network Engineer | Cloud Infra Eng, SecOps | 네트워크 설계 문서 |

---

## 4. 역할별 AWS 자격증 매핑

| 역할 | 1순위 자격증 | 2순위 자격증 | 관련 Specialty |
|------|------------|------------|---------------|
| **Cloud Infra Engineer** | Solutions Architect Professional | SysOps Administrator | — |
| **SRE** | DevOps Engineer Professional | Solutions Architect Professional | — |
| **DevOps Engineer** | DevOps Engineer Professional | SysOps Administrator | — |
| **Platform Engineer** | Solutions Architect Professional | DevOps Engineer Professional | — |
| **Cloud DBA** | Database Specialty | Solutions Architect Associate | Data Analytics Specialty |
| **Network Engineer** | Advanced Networking Specialty | Solutions Architect Professional | — |
| **SecOps** | Security Specialty | Solutions Architect Associate | — |
| **FinOps Engineer** | Solutions Architect Associate | Cloud Practitioner | — |
| **On-Call Engineer** | SysOps Administrator | Cloud Practitioner | — |
| **Cloud Architect** | Solutions Architect Professional | 모든 Specialty | Well-Architected 프레임워크 |

---

## 5. oh-my-aws Agent 관점: 역할별 지원 방향

| 운영자 역할 | Agent가 가장 큰 가치를 줄 수 있는 영역 |
|------------|--------------------------------------|
| **Cloud Infra Engineer** | CDK 코드 생성/리뷰, cdk diff 자동화, Well-Architected 검사 |
| **SRE** | SLO 계산, 장애 타임라인 자동 생성, Toil 자동화, Runbook 실행 |
| **DevOps Engineer** | 배포 파이프라인 템플릿, 배포 후 검증 자동화, 롤백 실행 |
| **Platform Engineer** | CDK Construct 템플릿, 보안 가드레일 검사, 개발자 문서 생성 |
| **Cloud DBA** | 슬로우 쿼리 분석, 인덱스 제안, 페일오버 모니터링 |
| **Network Engineer** | Flow Logs 분석, Reachability Analyzer 실행, SG 최적화 제안 |
| **SecOps** | GuardDuty Finding 분석, IAM 최소권한 제안, 컴플라이언스 체크 |
| **FinOps Engineer** | 비용 이상 탐지, RI/SP 최적화 제안, 미사용 리소스 식별 |
| **On-Call Engineer** | 장애 자동 분류, Runbook 자동 실행, 에스컬레이션 제안 |
| **Cloud Architect** | Well-Architected 리뷰, 아키텍처 패턴 제안, Trade-off 분석 |

---

## 6. 참고 자료

### AWS 공식

- [AWS Well-Architected Framework](https://aws.amazon.com/architecture/well-architected/) — 6개 Pillar 전체
- [AWS Cloud Adoption Framework](https://aws.amazon.com/professional-services/CAF/) — 조직 역할 모델
- [AWS Skill Builder](https://skillbuilder.aws/) — 공식 학습 플랫폼
- [AWS Certification](https://aws.amazon.com/certification/) — 자격증 로드맵
- [Amazon Builders' Library](https://aws.amazon.com/builders-library/) — 아마존 실무 문서
- [AWS Architecture Center](https://aws.amazon.com/architecture/) — 참조 아키텍처

### 산업 프레임워크

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/) — 무료 온라인
- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/) — 무료 온라인
- [FinOps Framework](https://www.finops.org/framework/) — 클라우드 재무 운영
- [DORA Metrics](https://dora.dev/research/) — DevOps 성숙도 지표
- [SRE Weekly](https://sreweekly.com/) — 주간 SRE 뉴스레터
- [Team Topologies](https://teamtopologies.com/) — 팀 구조 설계
