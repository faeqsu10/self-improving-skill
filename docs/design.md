# 설계 문서: Self-Improving Skill

## 1. 배경

### HyperAgents 핵심 발견

Meta의 HyperAgents(2025) 논문에서 핵심적으로 참고할 포인트:

1. **메타 에이전트는 극도로 단순해도 된다** — HyperAgents의 meta_agent.py는 18줄. "코드베이스의 아무 부분이나 수정해라"가 전부.
2. **복잡성은 루프 관리에 있다** — 진화 루프(평가 → 아카이브 → 부모 선택 → 수정 → 재평가)가 핵심.
3. **에이전트가 자발적으로 발명하는 것들** — 영속 메모리, 성능 추적, 다단계 평가, 도메인 지식 베이스, 편향 감지, 재시도 로직.
4. **메타 수준 개선은 도메인 간 전이된다** — 한 분야에서 학습한 개선 전략이 새로운 분야에서도 동작.

### 축소 원칙

| HyperAgents (원본) | 이 프로젝트 (축소) |
|-------------------|------------------|
| Docker 격리 실행 | Claude Code 세션 |
| 수백 세대 진화 | 세션 단위 학습 |
| 4개 도메인 벤치마크 | 프로젝트 내 테스트/lint |
| LLM API 직접 호출 | Claude Code가 LLM |
| 아카이브 (세대별 저장) | git 커밋 히스토리 |
| 부모 선택 알고리즘 | 최근 N개 세션 참조 |

## 2. 아키텍처

### 컴포넌트

```
┌─────────────────────────────────────────┐
│              Claude Code                 │
│  ┌─────────┐   ┌──────────┐             │
│  │  SKILL  │   │ evaluator│             │
│  │  .md    │──▶│   .py    │──▶ scores   │
│  │ (메타   │   └──────────┘    .json    │
│  │  전략)  │   ┌──────────┐             │
│  │         │◀──│ memory   │◀── memory   │
│  │         │   │   .py    │    .json    │
│  └─────────┘   └──────────┘             │
└─────────────────────────────────────────┘
```

### 핵심 루프

```
Session Start
    │
    ├── memory.json 로드 (이전 세션의 전략/교훈)
    │
    ├── 사용자 작업 수행
    │
    ├── evaluator.py 실행
    │   ├── 테스트 통과율
    │   ├── lint 점수
    │   ├── diff 크기 (변경량)
    │   └── 에러 발생 여부
    │
    ├── 평가 결과 → scores.json에 추가
    │
    ├── Meta 분석 (Claude Code가 수행)
    │   ├── 이전 세션 대비 개선/퇴보 판단
    │   ├── 반복되는 실패 패턴 감지
    │   └── 새로운 전략 도출
    │
    └── memory.json 업데이트
        ├── 인과 가설 ("X 접근이 Y에서 실패한 이유")
        ├── 전략 ("다음에는 Z를 먼저 시도")
        └── 도메인 지식 ("이 프로젝트에서는 A가 중요")
```

## 3. 데이터 구조

### memory.json

```json
{
  "version": 1,
  "strategies": [
    {
      "id": "s001",
      "created": "2026-04-14",
      "context": "리팩토링 작업",
      "insight": "큰 함수를 나눌 때 테스트를 먼저 확인해야 한다",
      "source": "session-003에서 테스트 없이 리팩토링 → 회귀 버그 발생",
      "success_count": 0,
      "fail_count": 1
    }
  ],
  "domain_knowledge": [
    {
      "project": "dalpintong",
      "facts": ["Flask 기반", "SQLite 사용", "테스트 커버리지 낮음"]
    }
  ],
  "anti_patterns": [
    {
      "pattern": "테스트 없이 대규모 리팩토링",
      "detected_count": 2,
      "last_seen": "2026-04-14"
    }
  ]
}
```

### scores.json

```json
{
  "sessions": [
    {
      "id": "session-001",
      "date": "2026-04-14",
      "project": "dalpintong",
      "task_type": "refactor",
      "metrics": {
        "tests_passed": 0.85,
        "lint_score": 0.92,
        "diff_lines": 45,
        "errors": 0
      },
      "strategies_used": ["s001"],
      "outcome": "success"
    }
  ]
}
```

## 4. 구현 단계

### Phase 1: Hook 기반 (최소 구현)
- Claude Code Stop hook으로 세션 종료 시 자동 평가
- 결과를 scores.json에 저장
- memory.json은 수동 관리

### Phase 2: Skill 기반 (메타 분석 추가)
- `/self-improve` 스킬로 메타 분석 트리거
- memory.json 자동 업데이트
- 이전 세션 대비 성장/퇴보 리포트

### Phase 3: 자기 수정 (HyperAgents 핵심)
- SKILL.md 자체를 세션 결과에 따라 업데이트
- 평가 기준도 자기 수정 대상
- 전략의 성공/실패 추적으로 전략 자체를 진화

## 5. 참고 자료

- [HyperAgents 논문](https://arxiv.org/abs/2603.19461)
- [facebookresearch/Hyperagents](https://github.com/facebookresearch/Hyperagents)
- [AI Paper Wiki: summary-hyperagents](/mnt/c/work/projects/llm-wiki/ai-paper-wiki/wiki/sources/summary-hyperagents.md)
- [NotebookLM 분석](https://notebooklm.google.com/notebook/02550f76-e131-45cd-92ed-74c4f5d5edf9)
