# Self-Improving Skill

HyperAgents 논문의 핵심 아이디어를 Claude Code 스킬로 축소 구현하는 프로젝트.

## 프로젝트 원칙

1. **단순함 유지**: HyperAgents의 meta_agent.py가 18줄인 것처럼, 핵심 로직은 최소한으로
2. **단계적 구현**: Hook → Skill → 자기 수정 순서로 진행
3. **실용성 우선**: 학술적 완벽함보다 실제로 돌아가는 것이 중요
4. **Python 3.12+**: HyperAgents와 동일한 Python 버전 사용

## 폴더 규칙

- `src/` — Python 소스 코드
- `skill/` — Claude Code SKILL.md 정의
- `docs/` — 설계 문서, 연구 노트
- `.meta/` — 런타임 데이터 (gitignore 대상)

## 핵심 참조

- HyperAgents 논문: https://arxiv.org/abs/2603.19461
- 코드: https://github.com/facebookresearch/Hyperagents
- 위키: /mnt/c/work/projects/llm-wiki/ai-paper-wiki/wiki/sources/summary-hyperagents.md
