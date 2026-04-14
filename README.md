# Self-Improving Skill

Meta의 [HyperAgents](https://arxiv.org/abs/2603.19461) 논문 핵심 아이디어를 Claude Code 환경에서 축소 구현한 프로젝트.

> "개선하는 방법 자체를 개선한다" — Metacognitive Self-Modification

## 아이디어

HyperAgents는 AI 에이전트가 **자기 개선 메커니즘 자체를 자기 수정**하는 프레임워크다.
이 프로젝트는 그 핵심을 Claude Code 스킬 1개 + Python 스크립트로 축소 구현한다.

### HyperAgents에서 가져온 것

| HyperAgents 개념 | 이 프로젝트에서의 구현 |
|-----------------|---------------------|
| Meta Agent (18줄) | SKILL.md 내 메타 전략 섹션 |
| Task Agent (44줄) | Claude Code 자체 |
| Archive (아카이브) | git 히스토리 |
| Persistent Memory | `.meta/memory.json` |
| Performance Tracker | `.meta/scores.json` |
| Docker 격리 실행 | Claude Code 세션 |

### 동작 흐름

```
사용자: "이 함수 리팩토링해줘"
         │
         ▼
   ① Task 수행 (Claude Code)
         │
         ▼
   ② 자동 평가 (테스트, lint, diff 크기)
         │
         ▼
   ③ Meta 분석 (평가 + 히스토리 → 전략 갱신)
         │
         ▼
   ④ Memory 저장 (.meta/memory.json)
         │
         ▼
   ⑤ 다음 작업에서 Memory 참조 → 개선된 방식으로 수행
```

## 프로젝트 구조

```
self-improving-skill/
├── README.md              ← 이 파일
├── CLAUDE.md              ← 프로젝트 규칙
├── skill/                 ← Claude Code 스킬 정의
│   └── SKILL.md           ← /self-improve 스킬
├── src/                   ← Python 소스
│   ├── evaluator.py       ← 작업 결과 자동 평가
│   ├── memory.py          ← 영속 메모리 관리
│   └── tracker.py         ← 성능 추적
├── docs/                  ← 설계 문서 및 연구 노트
│   └── design.md          ← 아키텍처 설계 문서
├── .meta/                 ← 런타임 데이터 (gitignore)
│   ├── memory.json        ← 영속 메모리
│   └── scores.json        ← 성능 히스토리
└── .gitignore
```

## 영감

- [HyperAgents 논문](https://arxiv.org/abs/2603.19461) (Meta, 2025)
- [facebookresearch/Hyperagents](https://github.com/facebookresearch/Hyperagents) (Python, CC BY-NC-SA 4.0)
- [AI Paper Wiki 정리](/mnt/c/work/projects/llm-wiki/ai-paper-wiki/wiki/sources/summary-hyperagents.md)

## 라이선스

MIT
