# Self-Improving Skill

Meta의 [HyperAgents](https://arxiv.org/abs/2603.19461) 논문 핵심 아이디어를 Claude Code 환경에서 축소 구현한 프로젝트.

> "개선하는 방법 자체를 개선한다" — Metacognitive Self-Modification

## 뭘 하는 건가

Claude Code가 나와 작업할 때마다 **자동으로 데이터를 쌓고, 패턴을 분석하고, 다음 세션에서 더 나은 방식으로 작업하게** 만드는 시스템.

```
Claude Code 세션 종료
    │
    ▼
① evaluator  ── 이 세션에서 뭘 했는지 기록 (git, 테스트, lint)
    │
    ▼
② memory     ── 전체 기록을 분석해서 패턴을 찾는다
    │
    ▼
③ injector   ── 분석 결과를 CLAUDE.md에 넣는다
    │
    ▼
다음 세션에서 Claude Code가 전략을 읽고 반영
```

## 사용법

### 1. 설치 (1회)

이미 Stop hook이 등록되어 있으므로 추가 설치 불필요.

### 2. 프로젝트에서 활성화

자기 개선을 사용하고 싶은 프로젝트에서 `.self-improve` 파일을 만든다:

```bash
# 프로젝트에서 자기 개선 활성화
cd ~/projects/my-project
touch .self-improve
```

이것만 하면 끝. 이후 이 프로젝트에서 Claude Code를 사용할 때마다 자동으로 데이터가 쌓인다.

`.self-improve` 파일이 **없는** 프로젝트에서는 아무 일도 일어나지 않는다.

### 3. 비활성화

```bash
# 자기 개선 끄기
rm .self-improve
```

### 4. 커스텀 설정 (선택)

프로젝트별로 테스트 명령이나 lint 도구를 지정하고 싶으면:

```bash
cat > .self-improve << 'EOF'
{
  "test_cmd": "python3 -m pytest tests/ -q",
  "lint_cmd": "ruff check ."
}
EOF
```

빈 파일(`touch .self-improve`)이면 기본 자동 감지를 사용한다.

### 5. 수동 분석

쌓인 데이터를 직접 분석하고 싶을 때:

```bash
# Claude Code 세션에서
/self-improve

# 또는 터미널에서 직접
python3 ~/projects/self-improving-skill/src/memory.py summary    # 간단 요약
python3 ~/projects/self-improving-skill/src/memory.py analyze    # 전체 분석
```

## 동작 원리

### 3개 파일이 각각 하는 일

| 파일 | 역할 | 비유 |
|------|------|------|
| `scores.json` | 매 세션의 지표 기록 | 일기장 |
| `memory.json` | 패턴 분석 + 전략 저장 | 두뇌 |
| `CLAUDE.md` | Claude Code가 읽는 전략 | 행동 지침 |

### 감지하는 안티패턴

- 테스트 없이 반복 작업 (3회 이상)
- lint 에러 방치 (5개 이상, 2회 이상)
- 세션 중 에러 빈발 (3개 이상, 3회 이상)
- 미커밋 변경 자주 방치 (70% 이상)

### 활성화 기준

프로젝트 루트 또는 상위 디렉토리에 `.self-improve` 파일이 있으면 활성화.
하위 디렉토리에서 작업해도 상위의 `.self-improve`를 찾아서 동작한다.

```
~/projects/my-project/.self-improve   ← 이 파일이 있으면
~/projects/my-project/src/            ← 여기서 작업해도 감지됨
~/projects/my-project/src/utils/      ← 여기서도 감지됨
```

## 프로젝트 구조

```
self-improving-skill/
├── README.md              ← 이 파일
├── CLAUDE.md              ← 프로젝트 규칙
├── .self-improve          ← 이 프로젝트 자체도 자기 개선 대상
├── skill/
│   └── SKILL.md           ← /self-improve 스킬 정의
├── src/
│   ├── evaluator.py       ← Phase 1: 세션 자동 평가 (Stop hook)
│   ├── memory.py          ← Phase 2: 패턴 분석 + 전략 도출
│   └── injector.py        ← Phase 3: 전략 → CLAUDE.md 자동 주입
└── docs/
    └── design.md          ← 아키텍처 설계 문서
```

데이터 저장 위치:
```
~/.config/self-improving-skill/
├── scores.json            ← 세션 기록 (최근 100개)
└── memory.json            ← 분석 결과 + 전략
```

## HyperAgents 논문과의 대응

| HyperAgents (논문) | 이 프로젝트 |
|-------------------|-----------|
| Meta Agent (18줄) | injector.py — 전략을 CLAUDE.md에 주입 |
| Task Agent (44줄) | Claude Code 자체 |
| Archive (아카이브) | scores.json + git 히스토리 |
| PerformanceTracker | evaluator.py |
| MemoryTool | memory.py + memory.json |
| Docker 격리 실행 | Claude Code 세션 단위 격리 |
| 수백 세대 진화 | 세션이 쌓일수록 전략이 정교해짐 |

핵심 차이: HyperAgents는 API 비용을 써서 수백 번 돌리지만, 이 프로젝트는 **평소 작업하면서 자연스럽게 쌓이는 구조**.

## 영감

- [HyperAgents 논문](https://arxiv.org/abs/2603.19461) (Meta, 2025)
- [facebookresearch/Hyperagents](https://github.com/facebookresearch/Hyperagents)

## 라이선스

MIT
