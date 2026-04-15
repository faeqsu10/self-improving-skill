# 설계 문서: Self-Improving Skill

## 1. 이 프로젝트가 하는 일

Claude Code가 나와 작업할 때마다 **자동으로 데이터를 쌓고, 패턴을 분석하고, 다음 세션에서 더 나은 방식으로 작업하게** 만드는 시스템.

핵심 원칙: **자동 수집, 자동 분석, 수동 적용.**

---

## 2. 전체 흐름

```
╔══════════════════════════════════════════╗
║         평소처럼 Claude Code 사용          ║
╚════════════════════╦═════════════════════╝
                     │
                세션 종료 (Stop hook 자동 발동)
                     │
    ┌────────────────┼────────────────┐
    ▼                ▼                ▼
┌─────────┐   ┌──────────┐   ┌──────────┐
│evaluator│   │ memory   │   │ injector │
│         │   │          │   │          │
│이 세션의 │→  │전체 기록  │→  │제안 파일  │
│지표 수집 │   │패턴 분석  │   │저장      │
└────┬────┘   └────┬─────┘   └────┬─────┘
     ▼              ▼              ▼
scores.json   memory.json   .self-improve-
(세션 기록부)  (두뇌)        strategies.md
                             (제안서)
     │              │              │
     └──────────────┼──────────────┘
                    │
              ✖ 여기서 멈춤
              ✖ CLAUDE.md는 안 건드림
                    │
          사용자가 /self-improve 실행 (수동)
                    │
                    ▼
          ┌──────────────────┐
          │  제안 + 검증 결과  │
          │  보여주고 물어봄   │
          │  "적용할까요?"    │
          └────────┬─────────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
     승인 → CLAUDE.md    거부 → 아무 일도
     에 반영              안 일어남
```

---

## 3. 핵심 파일 5개

### 소스 코드 (src/)

| 파일 | 줄 수 | 역할 |
|------|-------|------|
| `hook-runner.py` | ~45줄 | Stop hook 진입점. stdin을 각 단계에 전달 |
| `evaluator.py` | ~250줄 | 세션 지표 수집 (git, 테스트, lint, 대화) |
| `memory.py` | ~280줄 | 패턴 분석 + 전략 도출 |
| `verifier.py` | ~180줄 | 전략 적용 전/후 지표 비교로 효과 검증 |
| `injector.py` | ~100줄 | 제안 파일(.self-improve-strategies.md) 생성 |

### 데이터 파일

| 파일 | 위치 | 역할 | 비유 |
|------|------|------|------|
| `scores.json` | `~/.config/self-improving-skill/` | 매 세션의 지표 기록 | 일기장 |
| `memory.json` | `~/.config/self-improving-skill/` | 분석 결과 + 전략 | 두뇌 |
| `.self-improve-strategies.md` | 프로젝트 루트 | 현재 제안 목록 (gitignore) | 제안서 |

---

## 4. 활성화 방식: opt-in

`.self-improve` 파일이 있는 프로젝트에서만 동작한다.

```bash
# 활성화
cd ~/projects/my-project
touch .self-improve

# 비활성화
rm .self-improve
```

- 파일이 없는 프로젝트 → 데이터 수집 안 함, 아무 일도 안 일어남
- 하위 디렉토리에서 작업해도 상위의 `.self-improve`를 찾아서 동작

### 커스텀 설정 (선택)

```json
// .self-improve
{
  "test_cmd": "python3 -m pytest tests/ -q",
  "lint_cmd": "ruff check ."
}
```

빈 파일이면 자동 감지.

---

## 5. 검증 시스템

HyperAgents의 "평가 → 우수한 것만 아카이브"를 축소 구현.

### 검증 흐름

```
전략 생성 (memory.py)
    │
    ▼
적용 전 세션 지표 ←→ 적용 후 세션 지표 비교 (verifier.py)
    │
    ├── 지표 개선됨    → verified   (적용 권장)
    ├── 지표 악화됨    → unverified (제거 권장)
    ├── 변화 없음      → neutral    (사용자 판단)
    └── 데이터 부족    → pending    (아직 판단 불가)
```

### 비교 지표

| 지표 | 수집 방법 |
|------|----------|
| 세션 에러 수 | transcript 로그 분석 |
| 테스트 통과율 | pytest/npm 자동 실행 |
| lint 에러 수 | ruff/flake8 자동 실행 |
| 미커밋 비율 | git status 확인 |

### 최소 데이터 요구

- 전략 적용 **전** 3개 세션 이상
- 전략 적용 **후** 3개 세션 이상
- 미달 시 `pending` (판단 보류)

---

## 6. CLAUDE.md 수정 규칙

**자동 수정 없음.** 사용자가 `/self-improve`로 승인해야만 수정됨.

수정 시 마커 블록만 사용:

```markdown
# (프로젝트 기존 CLAUDE.md 내용 — 전부 그대로)

<!-- self-improve:start -->
## 자기 개선 전략 (승인됨)
- 전략 1
- 전략 2
<!-- self-improve:end -->
```

- 마커 안쪽만 교체
- 마커 밖은 절대 수정 안 함
- 마커 블록이 없으면 맨 끝에 추가

---

## 7. 감지하는 안티패턴 (4종)

| 패턴 | 발동 조건 | 제안 |
|------|----------|------|
| 테스트 없이 반복 작업 | 테스트 total=0인 세션 3회 이상 | 기본 테스트 추가 |
| lint 에러 방치 | lint error > 5인 세션 2회 이상 | 세션 시작 시 lint 먼저 |
| 세션 중 에러 빈발 | error > 3인 세션 3회 이상 | 접근 방식 변경 |
| 미커밋 변경 방치 | 70% 이상 세션에서 미커밋 | 자주 커밋 |

---

## 8. 설치

### 로컬 또는 원격 서버에 설치 (1회)

```bash
curl -fsSL https://raw.githubusercontent.com/faeqsu10/self-improving-skill/main/install.sh | bash
```

이 스크립트가 하는 일:
1. `~/.config/self-improving-skill/repo/`에 소스 다운로드
2. `~/.claude/settings.json`에 Stop hook 등록
3. `~/.claude/skills/self-improve/`에 스킬 설치

### 프로젝트에서 활성화

```bash
cd ~/projects/my-project
touch .self-improve
```

### 사용

```bash
# 세션에서 분석 요청
/self-improve

# 또는 터미널에서 직접
python3 ~/.config/self-improving-skill/src/memory.py summary
python3 ~/.config/self-improving-skill/src/verifier.py
```

---

## 9. HyperAgents 논문과의 대응

| HyperAgents | 이 프로젝트 | 차이 |
|-------------|-----------|------|
| Meta Agent (18줄) | injector.py | 자동 주입 → 제안만 저장 |
| Task Agent (44줄) | Claude Code 자체 | 동일 |
| Archive | scores.json + git | 동일 개념 |
| PerformanceTracker | evaluator.py | 동일 개념 |
| MemoryTool | memory.py + memory.json | 동일 개념 |
| 평가 → 아카이브 | verifier.py | 전/후 지표 비교 |
| Docker 격리 | Claude Code 세션 | 더 가벼움 |
| 자동 수정 | 사용자 승인 후 수정 | 더 안전 |

핵심 차이: HyperAgents는 자동으로 수백 번 돌리지만, 이 프로젝트는 **평소 작업하면서 자연스럽게 쌓이고, 사용자가 판단**한다.

---

## 10. 파일 구조 전체

```
self-improving-skill/              ← GitHub: faeqsu10/self-improving-skill
├── README.md                      ← 사용법 가이드
├── CLAUDE.md                      ← 프로젝트 규칙
├── install.sh                     ← 원커맨드 설치 스크립트
├── .self-improve                  ← 이 프로젝트도 자기 개선 대상
├── .gitignore
├── src/
│   ├── hook-runner.py             ← Stop hook 진입점
│   ├── evaluator.py               ← 세션 자동 평가
│   ├── memory.py                  ← 패턴 분석 + 전략 도출
│   ├── verifier.py                ← 전략 효과 검증
│   └── injector.py                ← 제안 파일 생성
├── skill/
│   └── SKILL.md                   ← /self-improve 스킬 정의
└── docs/
    └── design.md                  ← 이 파일

데이터 (서버별 로컬):
~/.config/self-improving-skill/
├── scores.json                    ← 세션 기록 (최근 100개)
└── memory.json                    ← 분석 결과 + 전략

프로젝트별 (gitignore):
<project>/.self-improve-strategies.md  ← 현재 제안 목록
```
