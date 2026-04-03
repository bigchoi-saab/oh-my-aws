# AWS Kiro CLI Skill - Phase별 구현 계획

> Plan created: 2026-04-03
> Project: oh-my-aws
> Scope: AWS 장애 초동 조치 Kiro CLI Skill (20 scenarios, 6 phases: Phase 0-5)
> Revision: 2026-04-03 v2 (Architect + Critic feedback reflected)
> Complexity: HIGH

---

## RALPLAN-DR SUMMARY

### Principles (핵심 원칙)

1. **완화 우선 (Mitigation Before Diagnosis)**: 가역적 조치를 10분 내 실행하고, 근본 원인 분석은 안정화 이후에 수행한다. MTTR의 60-80%가 진단에서 소모되는 패턴을 역전시킨다.

2. **Dual-Target Kiro-Native 설계**: Claude Code Skill(`.claude/skills/`)을 golden source로 유지하되, Kiro Skills 포맷(agentskills.io YAML frontmatter + markdown)으로 파생 버전(`.kiro/skills/`)을 생성한다. DKR YAML, scenario-registry 등 도메인 자산은 양쪽에서 공유한다. Kiro Specs 구조(`.kiro/specs/{feature}/`)와 MCP 서버 통합, Bedrock 연동을 전제로 설계하되, Phase 0 검증 실패 시 Claude Code Skill로 피벗한다.

3. **Human-in-the-Loop 승인 게이트**: 위험도에 따라 3단계(자동/제안+승인/분석+명시적승인) 실행 수준을 구분한다. 장애 중 비가역적 조치는 절대 자동 실행하지 않는다.

4. **증거 기반 의사결정 (Evidence-Driven)**: 모든 진단 단계에 구체적 CLI/API 명령어, 모든 조치에 롤백 명령어, 모든 검증에 CloudWatch 쿼리/메트릭을 포함한다. DKR(Decision Knowledge Record) 스키마로 정규화한다.

5. **점진적 확장 (Progressive Rollout)**: 2개 시나리오 MVP에서 시작하여 20개 시나리오 + 자동 감지까지 단계적으로 확장한다. 각 Phase가 독립적으로 가치를 제공해야 한다.

### Decision Drivers (핵심 의사결정 요인)

1. **Kiro 생태계 적합성**: Kiro는 `.kiro/specs/` 기반 Spec-driven 개발과 agentskills.io 기반 Skill 시스템을 사용한다. 기존 Claude Code SKILL.md를 그대로 사용할 수 없으며, Kiro의 SKILL.md 포맷(YAML frontmatter + allowed tools + markdown instructions)으로 변환해야 한다. MCP 서버는 Kiro가 네이티브로 지원하므로 aws-ops-tools MCP 서버를 핵심 도구 계층으로 활용한다.

2. **이미 완성된 리서치 자산 활용**: DKR 스키마(05), 로그 소스 맵(06), 10개 시나리오 인간 대응 절차(07), 골든 타임라인(07-playbook), 보안 플레이북(_research/)이 이미 존재한다. Lambda 타임아웃/쓰로틀링은 전체 DKR 정규화까지 완료되어 있다. 새로 연구할 필요 없이 변환/구현에 집중한다.

3. **장애 대응 시간 제약**: 장애 초동 조치는 골든 타임(15분) 내에 첫 완화가 시작되어야 한다. Skill이 느리게 동작하면 가치가 없다. Observe-Reason 단계를 병렬로 실행하고, Act 단계에서는 사전 검증된 CLI 명령어를 즉시 제안하는 구조가 필요하다.

### Viable Options (구현 접근법 비교)

#### Option A: Kiro Skill + Kiro Specs + MCP Server (선택)

Kiro의 3대 핵심 기능을 모두 활용하는 Full-Native 접근.

- **Kiro Skill** (`.kiro/skills/aws-incident-response/SKILL.md`): agentskills.io 포맷, YAML frontmatter에 allowed-tools/prerequisites/tags 정의, markdown body에 Observe-Reason-Act-Verify-Audit 파이프라인 지시
- **Kiro Specs** (`.kiro/specs/aws-incident-response/`): requirements.md로 기능 요구사항, design.md으로 DKR 스키마 아키텍처, tasks.md로 구현 태스크 추적
- **MCP Server** (`aws-ops-tools`): CloudWatch Logs/Metrics, CloudTrail, AWS Health, 토폴로지, 완화 실행 도구를 MCP 프로토콜로 제공

Pros:
- Kiro의 Spec-driven 워크플로우와 자연스럽게 통합
- MCP 도구로 AWS API 호출을 추상화하여 안전한 실행 게이트 구현 가능
- Bedrock 모델 연동이 네이티브 (Kiro는 Bedrock 기반)
- 시나리오 추가 시 DKR YAML 파일만 추가하면 Skill이 자동으로 인식

Cons:
- Kiro Skill 포맷이 아직 초기 단계라 문서/예제가 제한적
- MCP 서버 개발이 별도 필요 (Phase 3에서 구현)
- 기존 Claude Code SKILL.md에서 상당한 구조 변환 필요

#### Option B: 순수 Kiro Specs 기반 (Skill 없이 Specs만 사용) (탈락)

Kiro Specs의 requirements/design/tasks 구조만으로 장애 대응 워크플로우를 정의하고, 별도 Skill 없이 Kiro의 일반 에이전트 기능으로 실행.

Pros:
- 구조가 단순하고 초기 세팅이 빠름
- Kiro Specs 포맷만 학습하면 됨

Cons:
- **탈락 사유**: Specs는 "기능 명세 + 설계 + 태스크 추적"용이지 "런타임 에이전트 지시"용이 아니다. 장애 발생 시 Kiro에게 "이 Spec대로 대응해라"라고 할 수 없다. Skill이 런타임 행동 지시를, Specs가 개발 프로세스 관리를 담당하는 것이 Kiro의 설계 의도다.
- MCP 도구 없이는 AWS API 호출을 Bash 명령어로만 해야 하므로 안전 게이트 구현이 어려움
- 시나리오 확장 시 Specs 파일이 비대해짐

#### Option C: Claude Code Skill Golden Source + Kiro 파생 (Dual-Target, 부분 채택)

`.claude/skills/aws-incident-response/SKILL.md`를 golden source로 유지하고, Kiro용 SKILL.md를 파생 생성한다. DKR YAML, scenario-registry, guardrails 등 도메인 자산은 공유한다.

Pros:
- 기존 작업물 재사용 극대화
- Claude Code 생태계의 성숙한 도구를 fallback으로 활용 가능
- Phase 0에서 Kiro 검증 실패 시 Claude Code Skill로 즉시 피벗 가능
- 도메인 지식(DKR, 시나리오)이 플랫폼 독립적으로 관리됨

Cons:
- 두 SKILL.md 간 동기화 부담 (완화: golden source -> 파생 단방향 흐름)
- Kiro 전용 기능(MCP 도구 참조, Bedrock 네이티브)은 파생 버전에만 존재
- **기존 탈락 사유 재평가**: "래퍼" 방식은 탈락이지만, "golden source + 파생" 방식은 Dual-Target 전략으로 부분 채택. Option A와 결합하여 최종 접근법으로 선택됨.

---

## PHASE별 구현 계획

### Phase 0: Platform Validation Sprint (1-2일)

**목표**: Kiro Skill 플랫폼의 핵심 전제조건을 검증하고, 실패 시 Claude Code Skill 피벗 여부를 결정한다. Phase 1 진입의 필수 게이트.

**의존 관계**: 없음 (최우선 실행)

**산출물**:

| 파일 경로 | 설명 |
|-----------|------|
| `.kiro/skills/aws-incident-response/SKILL.md` | 빈 스켈레톤 (YAML frontmatter + minimal body) - 로드 검증용 |
| `.kiro/mcp.json` | MCP 등록 포맷 테스트용 최소 설정 |
| `.omc/plans/phase0-validation-report.md` | 검증 결과 보고서 (PASS/FAIL + 근거) |

**Phase 0 Gate Checklist (필수, 하나라도 FAIL이면 Phase 1 진입 불가)**:

- [ ] **G0-1**: Kiro SKILL.md YAML frontmatter 필드 스펙 확인 -- agentskills.io 최신 문서에서 `name`, `description`, `version`, `category`, `tags`, `prerequisites`, `allowed-tools` 등 필수/선택 필드 목록 확정
- [ ] **G0-2**: Kiro MCP transport 방식 확인 -- `.kiro/mcp.json` 포맷 확정 + stdio/SSE/HTTP 중 지원 transport 확인 + 실제 빈 MCP 서버 연결 테스트
- [ ] **G0-3**: 승인 게이트 UX 가능 여부 확인 -- Kiro CLI에서 MCP 도구가 "승인 필요"를 반환했을 때 인터랙티브 프롬프트 표시 가능 여부 검증. 불가 시 텍스트 기반 승인 대안 설계
- [ ] **G0-4**: 샌드박스 AWS 계정/리전 확보 -- Game Day 테스트를 위한 AWS 계정 접근 확인, Lambda/CloudWatch/CloudTrail 권한 검증
- [ ] **G0-5**: 피벗 기준 정의 -- 아래 피벗 매트릭스에 따라 부분 실패 시나리오별 대응 방안 확정

**피벗 매트릭스**:

| 검증 항목 | PASS | PARTIAL FAIL | FULL FAIL |
|-----------|------|-------------|-----------|
| Kiro Skill 로드 (G0-1) | Phase 1 진행 | SKILL.md 포맷 조정 후 재시도 | Claude Code Skill로 피벗 |
| MCP transport (G0-2) | Phase 3 계획 유지 | 지원 transport에 맞게 Phase 3 조정 | Phase 3을 CLI wrapper로 대체, Phase 5 자동감지는 CloudWatch EventBridge 기반으로 전환 |
| 승인 게이트 UX (G0-3) | 인터랙티브 승인 구현 | 텍스트 기반 승인으로 대체 | SKILL.md 지시에 "사용자 확인 후 진행" 텍스트 삽입 |
| AWS 계정 (G0-4) | Game Day 진행 | LocalStack mock으로 대체 | E2E 검증을 dry-run으로 한정 |
| 피벗 기준 (G0-5) | 문서화 완료 | - | - |

**세부 TODO**:

1. **빈 Kiro Skill 스켈레톤 생성**: 최소 YAML frontmatter + "Hello World" 수준 body로 Kiro CLI에서 Skill 로드 여부 확인.
   - AC: `kiro` CLI에서 Skill 목록에 표시되고, Skill 호출 시 body 내용이 에이전트에 전달됨

2. **MCP transport 테스트**: `.kiro/mcp.json`에 빈 echo MCP 서버를 등록하고, Kiro에서 MCP 도구 호출이 가능한지 확인. stdio/SSE/HTTP 각각 테스트.
   - AC: 최소 1개 transport에서 MCP 도구 호출-응답이 성공함

3. **승인 게이트 프로토타입**: MCP 도구에서 `approval_required: true`를 반환했을 때 Kiro CLI의 동작을 관찰. 인터랙티브 프롬프트 여부 확인.
   - AC: 승인 메커니즘(인터랙티브 또는 텍스트 기반) 결정이 문서화됨

4. **agentskills.io YAML frontmatter 필드 확정**: kiro.dev 및 agentskills.io 최신 문서를 조회하여 필수/선택 필드 목록을 확정하고 기록.
   - AC: 필드 목록이 `.omc/plans/phase0-validation-report.md`에 기록됨

5. **검증 결과 보고서 작성**: 모든 Gate 항목의 PASS/FAIL 결과와 PARTIAL FAIL 시 대응 방안을 기록.
   - AC: phase0-validation-report.md에 5개 Gate 항목 모두의 결과가 기록되고, Phase 1 진입 가/부 판정이 명시됨

**완료 기준**:
- [ ] 5개 Gate 항목 모두 검증 완료 (PASS 또는 PARTIAL FAIL + 대안 확보)
- [ ] 검증 결과 보고서가 `.omc/plans/phase0-validation-report.md`에 저장됨
- [ ] FULL FAIL 항목이 있을 경우 피벗 결정이 문서화됨
- [ ] Phase 1 진입 가/부 판정이 명시됨

---

### Phase 1: Kiro Skill MVP (2개 시나리오 작동)

**목표**: Kiro CLI에서 `lambda-timeout`과 `lambda-throttle` 시나리오에 대해 Observe-Reason-Act-Verify 파이프라인이 end-to-end로 작동하는 최소 기능 Skill 구현.

**의존 관계**: Phase 0 완료 (모든 Gate PASS 또는 PARTIAL FAIL + 대안 확보)

**산출물**:

| 파일 경로 | 설명 |
|-----------|------|
| `.claude/skills/aws-incident-response/SKILL.md` | **Golden Source** - Claude Code Skill 메인 파일 (Observe-Reason-Act-Verify-Audit 파이프라인 지시) |
| `.kiro/skills/aws-incident-response/SKILL.md` | **파생** - Kiro Skill 메인 파일 (agentskills.io YAML frontmatter + 파이프라인 지시, golden source에서 파생) |
| `.kiro/skills/aws-incident-response/scenarios/lambda-timeout.yaml` | Lambda 타임아웃 DKR (docs/research/05에서 변환) -- **공유 자산** |
| `.kiro/skills/aws-incident-response/scenarios/lambda-throttle.yaml` | Lambda 쓰로틀링 DKR (docs/research/05에서 변환) -- **공유 자산** |
| `.kiro/skills/aws-incident-response/references/log-source-map.md` | 서비스별 로그 위치 참조 (docs/research/06에서 추출) -- **공유 자산** |
| `.kiro/skills/aws-incident-response/references/guardrails.yaml` | 글로벌 가드레일 정의 (승인 게이트 3단계, 사전/사후 조건) -- **공유 자산** |
| `.kiro/specs/aws-incident-response/requirements.md` | Kiro Spec: 기능 요구사항 |
| `.kiro/specs/aws-incident-response/design.md` | Kiro Spec: DKR 스키마 아키텍처 + 파이프라인 설계 |
| `.kiro/specs/aws-incident-response/tasks.md` | Kiro Spec: 전체 구현 태스크 추적 |

**Dual-Target 구현 방식**:

- `.claude/skills/aws-incident-response/SKILL.md`를 golden source로 먼저 작성한다. 핵심 파이프라인 로직, 시나리오 라우팅, 안티패턴, 가드레일 지시가 여기에 정의된다.
- `.kiro/skills/aws-incident-response/SKILL.md`는 golden source에서 파생한다: agentskills.io YAML frontmatter(`name`, `description`, `version`, `category`, `tags`, `prerequisites`, `allowed-tools`) 추가 + Kiro 전용 MCP 도구 참조로 변환.
- `allowed-tools`에 Bash(AWS CLI 실행), Read(DKR/참조 파일 로드), Glob(시나리오 파일 탐색)을 선언한다 (Phase 3 완료 후 MCP 도구 참조 추가)
- `prerequisites`에 AWS CLI configured, CloudWatch 접근 권한, Lambda 관리 권한을 명시한다
- DKR YAML, scenario-registry, guardrails 등 도메인 자산은 양쪽 Skill에서 공유한다 (경로 참조로 연결)
- DKR YAML 파일은 기존 리서치(05)의 정규화된 데이터를 `decision-knowledge-record/v1` 스키마로 변환한다
- Kiro Specs의 `requirements.md`에 20개 시나리오 전체 요구사항을 정의하되, 각 시나리오에 Phase 매핑을 명시한다

**세부 TODO**:

1. **Dual-Target SKILL.md 작성**: (a) `.claude/skills/` golden source SKILL.md에 핵심 파이프라인 로직을 정의. (b) golden source에서 `.kiro/skills/` 파생 SKILL.md를 생성하여 agentskills.io YAML frontmatter 추가 + Kiro-native 실행 지시로 변환. The Insight/Core Architecture/Anti-Patterns 섹션은 양쪽 모두 유지하되, Implementation Options 섹션은 제거.
   - AC: (1) Claude Code에서 golden source Skill이 로드됨, (2) Kiro CLI에서 파생 Skill이 로드되고 `allowed-tools`가 인식됨, (3) 양쪽 SKILL.md의 파이프라인 로직이 동일함

2. **Lambda DKR 변환**: docs/research/05의 섹션 2 전체(증상/진단트리/근본원인/조치/가드레일/검증)를 `lambda-timeout.yaml`과 `lambda-throttle.yaml`로 분리 변환.
   - AC: 각 DKR 파일이 `decision-knowledge-record/v1` 스키마를 준수하고, 모든 `remediation.actions`에 `aws_cli` 명령어와 `rollback` 명령어가 포함됨

3. **가드레일 정의**: 승인 게이트 3단계(LOW/MEDIUM/HIGH risk) 정의 + 사전/사후 조건 YAML.
   - AC: `guardrails.yaml`에 risk level별 자동화 수준이 정의되고, Lambda 설정 변경(MEDIUM)과 로그 수집(LOW)이 올바른 수준으로 분류됨

4. **Kiro Specs 초기 구조**: requirements.md에 20개 시나리오 전체 목록 + Phase 매핑, design.md에 DKR 스키마 + 파이프라인 아키텍처, tasks.md에 Phase 1 태스크 목록.
   - AC: `.kiro/specs/aws-incident-response/` 하위 3개 파일이 존재하고, requirements.md에 모든 시나리오 ID가 나열됨

5. **End-to-End 검증**: Kiro CLI에서 "Lambda 함수가 타임아웃 발생 중" 상황을 입력했을 때, Skill이 Observe(로그 쿼리 생성) -> Reason(진단 트리 탐색) -> Act(설정 변경 CLI 제안) -> Verify(검증 쿼리 제안) 순서로 응답하는지 확인.
   - AC: 파이프라인 4단계가 순서대로 출력되고, 제안된 CLI 명령어가 실제 실행 가능한 형태이며, MEDIUM risk 조치에 승인 요청 메시지가 포함됨

**완료 기준**:
- [ ] Kiro CLI에서 Skill이 인식되고 로드됨
- [ ] `lambda-timeout` 시나리오 입력 시 Observe-Reason-Act-Verify 4단계 응답 생성
- [ ] `lambda-throttle` 시나리오 입력 시 동일 파이프라인 작동
- [ ] 모든 Act 단계 CLI 명령어에 롤백 명령어가 병기됨
- [ ] MEDIUM/HIGH risk 조치에 승인 게이트 프롬프트 포함

---

### Phase 2: 핵심 시나리오 확장 (Priority 1-2, 총 12개 시나리오)

**목표**: Priority 1-2인 10개 추가 시나리오의 DKR을 작성하여 총 12개 시나리오를 커버한다. 카테고리별(Compute, Database, Network, Deployment, Platform, Security) 최소 1개 이상의 시나리오가 작동한다.

**의존 관계**: Phase 1 완료

**산출물**:

| 파일 경로 | 설명 |
|-----------|------|
| `.kiro/skills/aws-incident-response/scenarios/ecs-crash-loop.yaml` | ECS 태스크 반복 실패 DKR |
| `.kiro/skills/aws-incident-response/scenarios/rds-perf-degradation.yaml` | RDS 성능 저하 DKR |
| `.kiro/skills/aws-incident-response/scenarios/rds-failover.yaml` | RDS Multi-AZ 페일오버 DKR |
| `.kiro/skills/aws-incident-response/scenarios/dynamodb-throttle.yaml` | DynamoDB 쓰로틀링 DKR |
| `.kiro/skills/aws-incident-response/scenarios/vpc-unreachable.yaml` | VPC 연결 불가 DKR |
| `.kiro/skills/aws-incident-response/scenarios/post-deploy-5xx.yaml` | 배포 후 5xx 에러 DKR |
| `.kiro/skills/aws-incident-response/scenarios/az-failure.yaml` | AZ 수준 장애 DKR |
| `.kiro/skills/aws-incident-response/scenarios/region-outage.yaml` | 리전 전체 장애 DKR |
| `.kiro/skills/aws-incident-response/scenarios/cascade-failure.yaml` | 연쇄 실패 / 재시도 폭풍 DKR |
| `.kiro/skills/aws-incident-response/scenarios/iam-compromise.yaml` | IAM 자격증명 유출 DKR |
| `.kiro/skills/aws-incident-response/references/scenario-registry.yaml` | 시나리오 레지스트리 (Kiro 포맷으로 변환, `network-unauthorized` 포함 -- Critic 반영) |
| `.kiro/skills/aws-incident-response/references/message-templates.md` | 커뮤니케이션 템플릿 (인시던트 선언/상태 업데이트/해결 알림) |

**Kiro 특화 구현 방식**:

- 보안 시나리오(`iam-compromise`)는 `_research/aws-customer-playbook-framework/`의 Compromised_IAM_Credentials 플레이북을 DKR 포맷으로 변환한다
- SKILL.md의 시나리오 라우팅 로직을 확장하여 `first_signal` 기반 자동 매칭을 추가한다: 사용자 입력에서 키워드/증상을 추출 -> scenario-registry.yaml의 `first_signal` 패턴과 매칭 -> 해당 DKR 로드
- 커뮤니케이션 템플릿은 docs/research/07-playbook의 섹션 6.3 메시지 템플릿을 Kiro Skill 참조로 변환한다
- Kiro Specs tasks.md를 Phase 2 태스크로 업데이트한다

**세부 TODO**:

1. **Compute 카테고리 DKR 작성** (`ecs-crash-loop`): docs/research/07-scenarios의 ECS 섹션과 scenario-registry.yaml의 root_causes를 기반으로 DKR 정규화.
   - AC: 5개 root_cause(OOM/APP-ERROR/IMAGE-PULL/SECRET-INIT/HEALTH-FAIL)에 각각 진단 CLI와 조치 CLI가 포함됨

2. **Database 카테고리 DKR 작성** (`rds-perf-degradation`, `rds-failover`, `dynamodb-throttle`): 각 시나리오의 진단 트리, 근본 원인, CloudWatch 메트릭 기반 조치를 정규화.
   - AC: RDS DKR에 Performance Insights 쿼리가 포함되고, DynamoDB DKR에 on-demand 전환 vs 프로비저닝 증설 분기가 있음

3. **Network/Deployment 카테고리 DKR 작성** (`vpc-unreachable`, `post-deploy-5xx`): VPC는 계층별(SG->NACL->Route->NAT->DNS->Endpoint) 진단 트리, post-deploy는 배포 시간 상관관계 + 롤백 우선 로직.
   - AC: VPC DKR에 Reachability Analyzer CLI가 포함되고, post-deploy DKR에 CodeDeploy/ECS 롤백 명령어가 있음

4. **Platform 카테고리 DKR 작성** (`az-failure`, `region-outage`, `cascade-failure`): AWS Health API 기반 감지 + Zonal Shift/DR 전환 조치 + 재시도 폭풍 서킷브레이커 패턴.
   - AC: az-failure DKR에 `aws arc-zonal-shift start-zonal-shift` CLI가 포함되고, cascade-failure에 재시도 제한 + 백프레셔 조치가 있음

5. **Security 카테고리 DKR 작성** (`iam-compromise`): _research/aws-customer-playbook-framework/Compromised_IAM_Credentials.md 기반 변환. 자격증명 비활성화 -> 세션 토큰 무효화 -> CloudTrail 감사 순서.
   - AC: DKR에 `aws iam update-access-key --status Inactive` 명령어가 있고, risk level이 HIGH로 설정되어 명시적 승인 게이트가 작동함

6. **시나리오 라우팅 로직 강화**: SKILL.md에 증상 키워드 기반 시나리오 자동 매칭 섹션 추가.
   - AC: "5xx 에러가 급증" 입력 시 `post-deploy-5xx` DKR이 로드되고, "IAM 키 유출" 입력 시 `iam-compromise` DKR이 로드됨

**완료 기준**:
- [ ] 12개 시나리오 DKR 파일이 모두 `decision-knowledge-record/v1` 스키마 준수
- [ ] 모든 카테고리(compute/database/network/deployment/platform/security)에 최소 1개 시나리오 작동
- [ ] 증상 키워드 입력 시 올바른 시나리오가 자동 매칭됨
- [ ] 보안 시나리오(iam-compromise)에서 HIGH risk 승인 게이트가 작동함
- [ ] 커뮤니케이션 템플릿이 SEV1-3별로 차별화됨

---

### Phase 3: MCP Server 도구 계층 (aws-ops-tools)

**목표**: AWS 관측/조치 API 호출을 MCP 프로토콜로 추상화하는 `aws-ops-tools` MCP 서버를 구현한다. Kiro의 MCP 통합을 통해 Skill이 구조화된 도구로 AWS를 조회/조작할 수 있게 한다.

**의존 관계**: Phase 1 완료 (Phase 2와 부분 병렬 진행 -- 아래 병렬화 범위 참조)

**Phase 2-3 병렬화 범위**:

| 작업 | 병렬/순차 | 근거 |
|------|----------|------|
| DKR YAML 작성 (Phase 2) | **병렬 OK** | MCP 코드와 독립적인 도메인 자산 |
| MCP Python 코드 (Phase 3) | **병렬 OK** | DKR 스키마와 독립적인 도구 계층 |
| SKILL.md `allowed-tools` 업데이트 | **순차 필요** | MCP 도구 이름이 확정되어야 참조 가능 |
| scenario-registry.yaml 시나리오 추가 | **병렬 OK** | DKR과 동시 작성 가능 |

**통합 지점**: Phase 2 + Phase 3 병렬 완료 후, SKILL.md의 `allowed-tools`를 MCP 도구 참조로 업데이트하고 end-to-end 통합 테스트를 수행하는 **통합 스프린트**(1-2일)가 필요하다.

**통합 스프린트 테스트 시나리오**:
- MCP `observe.*` 도구 -> DKR의 `diagnosis.steps[].cli` 매칭 검증
- MCP `act.execute_remediation` -> DKR의 `remediation.actions[].aws_cli` 실행 검증
- SKILL.md 시나리오 라우팅 -> scenario-registry -> DKR 로드 -> MCP 도구 호출 전체 경로 검증

**산출물**:

| 파일 경로 | 설명 |
|-----------|------|
| `mcp-servers/aws-ops-tools/server.py` | MCP 서버 메인 (Python 가정, Phase 0에서 확정 -- FastMCP 또는 mcp-python-sdk 기반) |
| `mcp-servers/aws-ops-tools/tools/observe.py` | Observe 도구: query_cloudwatch_logs, get_cloudwatch_metrics, get_cloudtrail_events, describe_aws_health (언어는 Phase 0에서 확정, Python 가정) |
| `mcp-servers/aws-ops-tools/tools/reason.py` | Reason 도구: get_resource_topology, correlate_deploy_timeline, analyze_blast_radius |
| `mcp-servers/aws-ops-tools/tools/act.py` | Act 도구: execute_remediation (승인 게이트 내장), dry_run_remediation |
| `mcp-servers/aws-ops-tools/tools/verify.py` | Verify 도구: check_metric_recovery, validate_stability_window |
| `mcp-servers/aws-ops-tools/guardrails.py` | 실행 가드레일: 사전조건 검증, 비용 영향 계산, 자동 롤백 트리거 |
| `mcp-servers/aws-ops-tools/pyproject.toml` | 프로젝트 설정 (Python 가정: boto3 + mcp-python-sdk, TypeScript 시: aws-sdk + @modelcontextprotocol/sdk -- Phase 0 G0-2 결과에 따라 확정) |
| `.kiro/mcp.json` | Kiro MCP 서버 등록 설정 |

**Kiro 특화 구현 방식**:

- Kiro는 `.kiro/mcp.json`(또는 프로젝트 설정)에서 MCP 서버를 등록한다. `aws-ops-tools` 서버를 여기에 등록하면 Skill의 `allowed-tools`에서 MCP 도구를 참조할 수 있다.
- MCP 도구는 파이프라인 단계별로 그룹화한다: `observe_*`, `reason_*`, `act_*`, `verify_*`
- `act.execute_remediation` 도구에는 반드시 `approval_required` 파라미터가 있어야 하며, risk level에 따라 Kiro가 사용자에게 승인을 요청하는 인터랙션 흐름을 구현한다
- `act.dry_run_remediation` 도구는 실제 실행 없이 CLI 명령어와 예상 영향을 반환한다
- boto3 세션은 환경변수 또는 AWS SSO 프로파일에서 자격증명을 로드한다

**세부 TODO**:

1. **MCP 서버 스캐폴딩**: FastMCP(또는 mcp-python-sdk) 기반 프로젝트 구조 생성. boto3 의존성, 타입 힌트, 에러 핸들링 기반 구조.
   - AC: `python -m mcp_servers.aws_ops_tools.server` 실행 시 MCP 프로토콜로 도구 목록이 반환됨

2. **Observe 도구 구현**: `query_cloudwatch_logs`(Log Group + 쿼리 + 시간 범위 -> 결과), `get_cloudwatch_metrics`(네임스페이스/메트릭/통계/기간 -> 데이터포인트), `get_cloudtrail_events`(시간 범위/이벤트명/리소스 -> 이벤트 목록), `describe_aws_health`(서비스/리전 -> 진행 중 이벤트).
   - AC: 각 도구가 올바른 boto3 API를 호출하고, 결과를 구조화된 JSON으로 반환하며, 에러 시 의미 있는 메시지를 반환함

3. **Act 도구 구현 (승인 게이트 포함)**: `execute_remediation`은 DKR의 `remediation.actions[].aws_cli` 명령어를 받아 실행하되, `guardrails.py`의 사전조건 검증을 먼저 통과해야 한다. `dry_run_remediation`은 명령어와 예상 영향만 반환한다.
   - AC: risk=HIGH 조치 실행 시 `approval_required=true` 응답이 반환되고, 사전조건 미충족 시 실행이 차단됨

4. **Kiro MCP 등록**: `.kiro/mcp.json`에 aws-ops-tools 서버를 등록하고, SKILL.md의 `allowed-tools`를 MCP 도구 참조로 업데이트한다.
   - AC: Kiro CLI에서 MCP 도구 목록이 조회되고, Skill이 MCP 도구를 호출할 수 있음

**MCP 레이턴시 버짓** (Architect 반영):

| 파이프라인 단계 | 시간 버짓 | 비고 |
|----------------|----------|------|
| Observe + Reason | 5분 이내 | 로그 쿼리 + 메트릭 조회 + 진단 트리 탐색 |
| Act | 5분 이내 | 승인 대기 시간 제외, 실행 + 검증 준비 |
| Verify | 5분 이내 | 안정화 확인 + 메트릭 회복 검증 |
| **단일 MCP 호출** | **10초 이내** | **초과 시 CLI fallback circuit breaker 발동** |

**CLI Fallback Circuit Breaker**: MCP 단일 호출이 10초를 초과하면 해당 도구를 circuit-open 상태로 전환하고, 동일한 AWS API를 직접 `aws` CLI 명령어로 실행하는 fallback 경로를 활성화한다. 3회 연속 성공 후 circuit-close로 복귀.

**완료 기준**:
- [ ] MCP 서버가 단독 실행되고 도구 목록을 반환함
- [ ] `observe.query_cloudwatch_logs`로 실제 CloudWatch Logs 쿼리가 실행됨
- [ ] `act.execute_remediation`에서 사전조건 검증과 승인 게이트가 작동함
- [ ] **MCP 단일 호출 레이턴시가 10초 이내** (Critic 반영)
- [ ] CLI fallback circuit breaker가 타임아웃 시 정상 작동함
- [ ] `act.dry_run_remediation`이 실행 없이 명령어와 영향을 반환함
- [ ] Kiro CLI에서 Skill이 MCP 도구를 호출하여 Lambda 메트릭을 조회할 수 있음

---

### Phase 4: 잔여 시나리오 완성 + Audit 파이프라인 (20개 전체)

**목표**: Priority 3 시나리오 8개를 추가하여 20개 전체를 커버하고, Audit 단계(타임라인 자동 기록, 결정사항 추적, 포스트모템 초안 생성)를 구현한다.

**의존 관계**: Phase 2 완료, Phase 3 완료 (MCP 도구 활용)

**산출물**:

| 파일 경로 | 설명 |
|-----------|------|
| `.kiro/skills/aws-incident-response/scenarios/lambda-cold-start.yaml` | Lambda 콜드 스타트 DKR |
| `.kiro/skills/aws-incident-response/scenarios/ec2-unreachable.yaml` | EC2 응답 불가 DKR |
| `.kiro/skills/aws-incident-response/scenarios/s3-access-denied.yaml` | S3 Access Denied DKR |
| `.kiro/skills/aws-incident-response/scenarios/cloudfront-issue.yaml` | CloudFront 캐시/5xx DKR |
| `.kiro/skills/aws-incident-response/scenarios/cert-expiry.yaml` | 인증서/자격증명 만료 DKR |
| `.kiro/skills/aws-incident-response/scenarios/control-plane-failure.yaml` | 제어 평면 장애 DKR |
| `.kiro/skills/aws-incident-response/scenarios/s3-public-exposure.yaml` | S3 버킷 공개 노출 DKR |
| `.kiro/skills/aws-incident-response/scenarios/network-unauthorized.yaml` | 비인가 네트워크 변경 DKR |
| `.kiro/skills/aws-incident-response/audit/timeline-template.md` | 인시던트 타임라인 자동 생성 템플릿 |
| `.kiro/skills/aws-incident-response/audit/postmortem-template.md` | 포스트모템 초안 생성 템플릿 |
| `mcp-servers/aws-ops-tools/tools/audit.py` | Audit 도구: record_timeline, generate_postmortem_draft, create_followup_actions |

**Kiro 특화 구현 방식**:

- Audit MCP 도구는 Observe-Reason-Act-Verify 과정에서 수집된 모든 데이터를 시간순 타임라인으로 자동 기록한다
- **Audit 데이터 영속성**: 타임라인과 포스트모템은 `.kiro/skills/aws-incident-response/audit/incidents/{incident-id}/` 하위에 `timeline.json`, `postmortem.md`, `decisions.json`으로 저장한다. `incident-id`는 `{YYYY-MM-DD}-{scenario-id}-{short-hash}` 포맷. 장기 보관이 필요한 경우 S3 버킷으로 아카이빙하는 MCP 도구(`audit.archive_to_s3`)를 Phase 5에서 추가한다.
- 포스트모템 초안은 docs/research/07-playbook 섹션 9의 표준(Executive summary, Impact quantification, Timeline, Root cause, Action items)을 따른다
- `generate_postmortem_draft` 도구는 타임라인 + 결정사항 + 메트릭 스냅샷을 입력받아 마크다운 포스트모템을 출력한다
- 보안 시나리오 DKR(`s3-public-exposure`, `network-unauthorized`)은 `_research/aws-customer-playbook-framework/`의 해당 플레이북을 참조하여 NIST 800-61 대응 단계와 매핑한다

**세부 TODO**:

1. **Priority 3 시나리오 DKR 8개 작성**: 각 시나리오를 docs/research/07-scenarios의 인간 대응 절차와 scenario-registry.yaml의 root_causes를 기반으로 DKR 정규화.
   - AC: 20개 시나리오 DKR 파일이 모두 존재하고, 각각 최소 2개 이상의 root_cause와 remediation action을 포함함

2. **Audit MCP 도구 구현**: `record_timeline`(이벤트 시간/유형/내용 -> 타임라인 엔트리 추가), `generate_postmortem_draft`(타임라인 + 결정사항 -> 마크다운 포스트모템), `create_followup_actions`(근본 원인 + 조치 이력 -> 후속 조치 목록).
   - AC: 포스트모템 초안에 impact window, timeline, root cause, action items 4개 필수 섹션이 포함됨

3. **SKILL.md Audit 단계 지시 추가**: 파이프라인의 마지막 단계로 Audit을 추가하여, 모든 인시던트 대응 후 자동으로 타임라인과 포스트모템 초안이 생성되도록 지시.
   - AC: 인시던트 대응 완료 후 Audit 단계가 자동으로 트리거되고, 타임라인이 시간순으로 출력됨

**완료 기준**:
- [ ] 20개 시나리오 DKR 파일이 모두 존재하고 스키마 준수
- [ ] Audit 도구로 타임라인이 자동 기록됨
- [ ] 포스트모템 초안이 4개 필수 섹션을 포함하여 생성됨
- [ ] 보안 시나리오에서 NIST 800-61 대응 단계 참조가 포함됨

---

### Phase 5: 자동 감지 + 인텔리전스 계층

**목표**: 사용자가 시나리오를 지정하지 않아도, 현재 AWS 환경의 이상 신호를 자동으로 감지하고 적절한 시나리오를 선택하여 대응을 시작하는 인텔리전스 계층을 구현한다.

**의존 관계**: Phase 3 완료 (MCP 도구), Phase 4 완료 (20개 시나리오)

**산출물**:

| 파일 경로 | 설명 |
|-----------|------|
| `mcp-servers/aws-ops-tools/tools/detect.py` | 자동 감지 도구: scan_active_alarms, scan_health_events, scan_recent_errors, correlate_signals |
| `.kiro/skills/aws-incident-response/intelligence/signal-correlation.md` | 신호 상관관계 분석 규칙 (다중 시나리오 동시 감지, 연쇄 장애 패턴) |
| `.kiro/skills/aws-incident-response/intelligence/severity-classifier.md` | 자동 심각도 분류 규칙 (blast radius + 고객 영향 기반) |
| `.kiro/skills/aws-incident-response/intelligence/suppression-rules.yaml` | False positive 억제 규칙 (flapping/noise/유지보수 윈도우 필터링) |
| `.kiro/skills/aws-incident-response/SKILL.md` | 업데이트: 자동 감지 모드(`--auto`) 지시 추가 |
| `.kiro/specs/aws-incident-response/tasks.md` | 최종 업데이트: 모든 Phase 완료 상태 반영 |

**Kiro 특화 구현 방식**:

- `detect.scan_active_alarms`는 CloudWatch의 ALARM 상태인 알람을 스캔하고, 알람 이름/네임스페이스를 scenario-registry.yaml의 `first_signal` 패턴과 매칭하여 해당 시나리오를 자동 선택한다
- `detect.correlate_signals`는 여러 알람/이벤트가 동시에 발생한 경우 연쇄 장애(`cascade-failure`) 또는 AZ/리전 장애(`az-failure`, `region-outage`)를 우선 판별한다
- 자동 심각도 분류는 blast radius(영향 범위) x 고객 영향(에러율) x 서비스 중요도(핵심/비핵심) 점수로 SEV1-4를 자동 배정한다
- Kiro CLI에서 `--auto` 플래그(또는 자연어 "현재 장애 상황을 점검해줘")를 입력하면 자동 감지 모드가 활성화된다
- Bedrock 모델의 추론 능력을 활용하여 복수 신호 간 인과관계를 분석한다
- **False Positive 필터링 규칙**: (1) ALARM 상태 지속 시간 < 2분인 알람은 flapping으로 분류하여 무시, (2) 동일 알람이 최근 24시간 내 3회 이상 ALARM->OK 전환된 경우 noise로 분류, (3) 스케줄된 유지보수 윈도우(AWS Health scheduled events) 중 발생한 알람은 필터링, (4) 사용자가 `.kiro/skills/aws-incident-response/intelligence/suppression-rules.yaml`에 커스텀 억제 규칙을 정의할 수 있음

**세부 TODO**:

1. **자동 감지 MCP 도구 구현**: `scan_active_alarms`(CloudWatch ALARM 상태 스캔), `scan_health_events`(AWS Health 진행 중 이벤트), `scan_recent_errors`(최근 N분간 에러 로그 패턴 스캔), `correlate_signals`(복수 신호 상관관계 분석).
   - AC: 테스트 계정에서 의도적으로 생성한 ALARM을 스캔하여 올바른 시나리오가 매칭됨

2. **신호 상관관계 규칙 작성**: 동시 발생 패턴(같은 AZ의 여러 서비스 장애 -> az-failure, 배포 시간대 에러 급증 -> post-deploy-5xx, 여러 함수의 쓰로틀링 -> cascade-failure) 규칙을 마크다운으로 정의.
   - AC: 3개 이상 알람 동시 발생 시 연쇄 장애 패턴이 우선 판별됨

3. **자동 심각도 분류기 구현**: blast radius(리전/AZ/서비스/엔드포인트), 고객 영향(에러율%), 서비스 중요도(tier 1/2/3) 기반 점수 산정 -> SEV1-4 자동 배정.
   - AC: 에러율 >10% + 핵심 서비스 장애 시 SEV1이 자동 배정되고, 단일 비핵심 서비스 지연 시 SEV3이 배정됨

4. **SKILL.md 자동 감지 모드 통합**: 기존 시나리오 지정 모드와 자동 감지 모드를 분기하는 라우팅 로직 추가.
   - AC: "현재 AWS 환경에 문제가 있는지 확인해줘" 입력 시 자동 감지 모드가 활성화되고, 발견된 이상 신호와 매칭 시나리오가 출력됨

**Phase 0 피벗 시 Fallback Plan**:
- **MCP transport FULL FAIL 시**: 자동 감지 도구를 MCP 대신 CloudWatch EventBridge 규칙 + Lambda 함수로 구현. EventBridge가 ALARM 상태 변경을 감지 -> Lambda가 scenario-registry.yaml과 매칭 -> 결과를 SNS/파일로 출력 -> SKILL.md가 결과를 읽어 파이프라인 시작.
- **MCP transport PARTIAL FAIL 시**: 지원되는 transport로 detect 도구만 MCP로 구현하고, 나머지는 CLI 직접 호출.

**완료 기준**:
- [ ] 자동 감지 모드에서 CloudWatch ALARM을 스캔하여 시나리오 매칭
- [ ] 복수 신호 동시 발생 시 연쇄 장애 패턴 우선 판별
- [ ] 자동 심각도 분류가 SEV1-4를 올바르게 배정
- [ ] 자동 감지 -> 시나리오 선택 -> Observe-Reason-Act-Verify-Audit 전체 파이프라인이 end-to-end 작동
- [ ] 20개 시나리오 전체가 자동 감지 경로에서 도달 가능
- [ ] False positive 필터링 규칙이 flapping/noise 알람을 올바르게 억제함

---

## ADR (Architecture Decision Record)

### Decision
AWS Kiro CLI Skill을 **Kiro Skill(agentskills.io) + Kiro Specs + MCP Server** 3계층 구조로 구현하되, **Dual-Target 전략**으로 Claude Code Skill을 golden source로 유지하고 Kiro Skill을 파생 버전으로 관리한다. **Phase 0 Platform Validation Sprint**를 필수 선행 게이트로 추가하여 Kiro 플랫폼 전제조건을 검증한다.

### Drivers
1. Kiro 생태계의 Spec-driven 개발 + MCP 네이티브 도구 통합이 장애 대응 자동화에 최적
2. 이미 완성된 DKR 스키마와 20개 시나리오 리서치를 Kiro 포맷으로 변환하여 빠르게 가치 제공 가능
3. 장애 초동 조치의 15분 골든 타임 제약이 파이프라인 병렬 실행과 사전 검증된 CLI 명령어 즉시 제안을 요구
4. **(신규)** Kiro 플랫폼이 초기 단계이므로 golden source를 Claude Code Skill로 유지하여 피벗 리스크를 헤지해야 함

### Alternatives Considered
- **Option B (순수 Kiro Specs)**: Specs는 개발 명세용이지 런타임 에이전트 지시용이 아니므로 탈락
- **Option C (Claude Code Skill Golden Source + Kiro 래퍼)**: 기존 "래퍼" 방식은 두 에이전트 간 컨텍스트 전달 오버헤드로 탈락했으나, **Dual-Target(golden source + 파생) 방식으로 재평가하여 부분 채택**. Option A와 결합하여 최종 접근법으로 선택됨. 래퍼가 아닌 "파생"이므로 런타임 오버헤드 없음.

### Why Chosen
3계층 분리가 각 관심사를 명확히 분리한다: Skill은 "무엇을 해야 하는가"(파이프라인 지시), Specs는 "어떻게 개발/추적하는가"(프로젝트 관리), MCP Server는 "어떻게 실행하는가"(도구). Dual-Target 전략은 Kiro 플랫폼 불확실성을 헤지하면서도 DKR YAML 등 도메인 자산을 공유하여 중복을 최소화한다. Phase 0 게이트는 검증 없는 구현 착수의 리스크를 제거한다.

### Consequences
- Kiro Skill 포맷이 변경될 경우 파생 SKILL.md 마이그레이션 필요 (위험: LOW, golden source가 보존됨)
- MCP 서버 개발/운영 부담 발생 (완화: Phase 3에서 점진적 도구 추가 + CLI fallback circuit breaker)
- **(신규)** Dual-Target으로 두 SKILL.md 동기화 부담 발생 (완화: golden source -> 파생 단방향 흐름, 자동화 스크립트 고려)
- **(신규)** Phase 0 추가로 전체 일정 1-2일 연장 (완화: 검증 실패 시 조기 피벗으로 낭비 방지)
- boto3 의존성으로 Python 런타임 필요 (대부분의 AWS 환경에서 이미 존재)

### Follow-ups
- Kiro Skill 포맷이 GA로 안정화되면 SKILL.md 구조 재검토, Dual-Target에서 Kiro-only로 전환 가능성 평가
- MCP 서버의 CloudWatch Logs Insights 쿼리 성능 벤치마크 (골든 타임 15분 내 5회 이상 쿼리 가능한지)
- **(신규)** MCP 레이턴시 버짓 모니터링: Observe-Reason 5분, Act 5분, Verify 5분 실제 달성 여부 추적. 단일 호출 10초 초과 시 CLI fallback circuit breaker 효과 측정
- Game Day 시나리오로 전체 파이프라인 end-to-end 검증 (Phase 2 완료 후)
- Bedrock Agent 통합 가능성 검토 (Kiro가 Bedrock Agent를 직접 호출하는 경로)
- **(신규)** Dual-Target SKILL.md 동기화 자동화: golden source 변경 시 파생 버전 자동 업데이트 스크립트 또는 CI 파이프라인 검토
- **(신규)** Phase 0 검증 결과에 따른 구현 언어(Python vs TypeScript) 확정 후 MCP 서버 기술 스택 문서 업데이트
