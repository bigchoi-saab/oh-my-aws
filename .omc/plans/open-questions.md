# Open Questions

## aws-kiro-skill-implementation - 2026-04-03 (v2, Architect+Critic 반영)

### Phase 0 Gate Blockers로 승격된 항목

아래 항목들은 기존 Open Questions에서 **Phase 0 Gate 필수 체크리스트**로 승격되었다. Phase 1 진입 전에 반드시 해결해야 하며, 상세 검증 절차는 `.omc/plans/aws-kiro-skill-implementation.md`의 Phase 0 섹션에 정의되어 있다.

- [G0-1] Kiro Skill YAML frontmatter 필드 스펙 확인 -- agentskills.io 최신 문서에서 필수/선택 필드 목록 확정. Phase 1의 SKILL.md 작성 전제조건.
- [G0-2] Kiro MCP transport 방식 확인 (stdio/SSE/HTTP) -- `.kiro/mcp.json` 포맷 + 지원 transport 확인. Phase 3 MCP 서버 구현의 전제조건. FULL FAIL 시 CLI wrapper로 피벗.
- [G0-3] 승인 게이트 UX 가능 여부 확인 -- Kiro CLI에서 인터랙티브 프롬프트 가능 여부. 불가 시 텍스트 기반 승인으로 대체.
- [G0-4] 샌드박스 AWS 계정/리전 확보 -- Game Day 테스트용 AWS 계정 접근 + Lambda/CloudWatch/CloudTrail 권한 검증.
- [G0-5] 피벗 기준 정의 (부분 실패 시나리오 포함) -- Phase 0 피벗 매트릭스에 따라 PASS/PARTIAL FAIL/FULL FAIL 대응 방안 확정.

**5개 Gate 중 하나라도 FULL FAIL이면 Phase 1 진입 불가. 피벗 매트릭스에 따라 Claude Code Skill 피벗 또는 대안 경로를 선택한다.**

### 잔여 Open Questions (Phase 0 이후 해결)

- [ ] MCP 서버 구현 언어 결정: Python(boto3 네이티브) vs TypeScript(Kiro 생태계 친화) -- Phase 0 G0-2 결과에 따라 Phase 3 시작 전에 확정. Kiro MCP transport가 특정 언어를 선호하면 그에 따른다.
- [ ] Kiro Specs의 tasks.md가 자동 체크박스 추적을 지원하는지 -- Kiro가 tasks.md의 체크박스를 자동으로 업데이트하는 기능이 있다면 활용하고, 없다면 수동 관리 방식을 정의해야 함. Phase 1 진행에는 영향 없음.
