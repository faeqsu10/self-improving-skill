#!/usr/bin/env python3
"""
Self-Improving Skill — Strategy Verifier

전략의 효과를 검증한다. HyperAgents의 평가 → 아카이브 구조를 축소 구현.

전략 적용 전/후의 지표를 비교하여:
- 효과 있음 → 전략 유지 (verified)
- 효과 없음/악화 → 전략 제거 제안 (unverified)
- 판단 불가 → 대기 (pending)

사용법:
    python3 verifier.py                    # 전체 전략 검증
    python3 verifier.py --project NAME     # 특정 프로젝트만
"""

import json
import sys
from datetime import datetime
from pathlib import Path

SCORES_FILE = Path.home() / ".config" / "self-improving-skill" / "scores.json"
MEMORY_FILE = Path.home() / ".config" / "self-improving-skill" / "memory.json"

# 검증에 필요한 최소 세션 수
MIN_SESSIONS_BEFORE = 3  # 전략 적용 전 최소 세션
MIN_SESSIONS_AFTER = 3   # 전략 적용 후 최소 세션


def load_json(path: Path) -> dict:
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_json(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_sessions_around_date(sessions: list[dict], date_str: str, project: str | None = None) -> tuple[list, list]:
    """특정 날짜 기준으로 전/후 세션을 분리한다."""
    before = []
    after = []
    for s in sessions:
        if project and s.get("project") != project:
            continue
        if s.get("date", "") < date_str:
            before.append(s)
        else:
            after.append(s)
    return before, after


def compute_metrics(sessions: list[dict]) -> dict:
    """세션 목록에서 평균 지표를 계산한다."""
    if not sessions:
        return {}

    metrics = {
        "session_count": len(sessions),
        "avg_errors": 0,
        "avg_test_pass_rate": None,
        "avg_lint_errors": 0,
        "uncommitted_ratio": 0,
    }

    error_sum = 0
    test_rates = []
    lint_sum = 0
    uncommitted = 0

    for s in sessions:
        session_info = s.get("session", {})
        error_sum += session_info.get("errors_in_session", 0)

        tests = s.get("tests", {})
        if tests.get("pass_rate") is not None:
            test_rates.append(tests["pass_rate"])

        lint = s.get("lint", {})
        lint_sum += lint.get("errors", 0)

        git = s.get("git", {})
        if git.get("has_uncommitted", False):
            uncommitted += 1

    n = len(sessions)
    metrics["avg_errors"] = round(error_sum / n, 2)
    metrics["avg_lint_errors"] = round(lint_sum / n, 2)
    metrics["uncommitted_ratio"] = round(uncommitted / n, 2)
    if test_rates:
        metrics["avg_test_pass_rate"] = round(sum(test_rates) / len(test_rates), 3)

    return metrics


def verify_strategy(strategy: dict, sessions: list[dict]) -> dict:
    """개별 전략의 효과를 검증한다."""
    created = strategy.get("created", "")
    project = strategy.get("project")

    before, after = get_sessions_around_date(sessions, created, project)

    result = {
        "strategy": strategy["strategy"],
        "project": project,
        "created": created,
        "sessions_before": len(before),
        "sessions_after": len(after),
    }

    # 데이터 부족 → pending
    if len(before) < MIN_SESSIONS_BEFORE or len(after) < MIN_SESSIONS_AFTER:
        needed_before = max(0, MIN_SESSIONS_BEFORE - len(before))
        needed_after = max(0, MIN_SESSIONS_AFTER - len(after))
        result["verdict"] = "pending"
        result["reason"] = f"데이터 부족 (전: {len(before)}/{MIN_SESSIONS_BEFORE}, 후: {len(after)}/{MIN_SESSIONS_AFTER})"
        return result

    before_metrics = compute_metrics(before)
    after_metrics = compute_metrics(after)

    result["before"] = before_metrics
    result["after"] = after_metrics

    # 개선 판단: 여러 지표를 종합
    improvements = 0
    regressions = 0
    details = []

    # 세션 에러 비교
    if after_metrics["avg_errors"] < before_metrics["avg_errors"]:
        improvements += 1
        details.append(f"세션 에러 감소 ({before_metrics['avg_errors']} → {after_metrics['avg_errors']})")
    elif after_metrics["avg_errors"] > before_metrics["avg_errors"]:
        regressions += 1
        details.append(f"세션 에러 증가 ({before_metrics['avg_errors']} → {after_metrics['avg_errors']})")

    # 테스트 통과율 비교
    if before_metrics.get("avg_test_pass_rate") is not None and after_metrics.get("avg_test_pass_rate") is not None:
        if after_metrics["avg_test_pass_rate"] > before_metrics["avg_test_pass_rate"]:
            improvements += 1
            details.append(f"테스트 통과율 향상 ({before_metrics['avg_test_pass_rate']} → {after_metrics['avg_test_pass_rate']})")
        elif after_metrics["avg_test_pass_rate"] < before_metrics["avg_test_pass_rate"]:
            regressions += 1
            details.append(f"테스트 통과율 하락 ({before_metrics['avg_test_pass_rate']} → {after_metrics['avg_test_pass_rate']})")

    # lint 에러 비교
    if after_metrics["avg_lint_errors"] < before_metrics["avg_lint_errors"]:
        improvements += 1
        details.append(f"lint 에러 감소 ({before_metrics['avg_lint_errors']} → {after_metrics['avg_lint_errors']})")
    elif after_metrics["avg_lint_errors"] > before_metrics["avg_lint_errors"]:
        regressions += 1
        details.append(f"lint 에러 증가 ({before_metrics['avg_lint_errors']} → {after_metrics['avg_lint_errors']})")

    # 미커밋 비율 비교
    if after_metrics["uncommitted_ratio"] < before_metrics["uncommitted_ratio"]:
        improvements += 1
        details.append(f"커밋 습관 개선 ({before_metrics['uncommitted_ratio']} → {after_metrics['uncommitted_ratio']})")
    elif after_metrics["uncommitted_ratio"] > before_metrics["uncommitted_ratio"]:
        regressions += 1
        details.append(f"커밋 습관 악화 ({before_metrics['uncommitted_ratio']} → {after_metrics['uncommitted_ratio']})")

    # 종합 판정
    if not details:
        result["verdict"] = "pending"
        result["reason"] = "비교 가능한 지표가 없음"
    elif improvements > regressions:
        result["verdict"] = "verified"
        result["reason"] = f"개선 {improvements}건 > 퇴보 {regressions}건"
    elif regressions > improvements:
        result["verdict"] = "unverified"
        result["reason"] = f"퇴보 {regressions}건 > 개선 {improvements}건 — 제거 권장"
    else:
        result["verdict"] = "neutral"
        result["reason"] = f"개선 {improvements}건 = 퇴보 {regressions}건 — 효과 불분명"

    result["details"] = details
    return result


def verify_all(project_filter: str | None = None):
    """모든 전략을 검증하고 결과를 출력한다."""
    scores_data = load_json(SCORES_FILE)
    sessions = scores_data.get("sessions", [])

    memory = load_json(MEMORY_FILE)
    strategies = memory.get("strategies", [])

    if not strategies:
        print("검증할 전략이 없습니다.")
        return

    results = []
    for s in strategies:
        if project_filter and s.get("project") != project_filter:
            continue
        result = verify_strategy(s, sessions)
        results.append(result)

        # memory의 전략에 검증 상태 반영
        s["verified"] = result["verdict"]
        s["last_verified"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    # memory 저장
    save_json(MEMORY_FILE, memory)

    # 결과 출력
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    args = sys.argv[1:]
    project = None
    if "--project" in args:
        idx = args.index("--project")
        if idx + 1 < len(args):
            project = args[idx + 1]
    verify_all(project)
