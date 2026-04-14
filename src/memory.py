#!/usr/bin/env python3
"""
Self-Improving Skill — Memory Manager

HyperAgents의 MemoryTool 개념을 축소 구현.
scores.json을 분석하여 패턴을 감지하고 memory.json을 갱신한다.

사용법:
    python3 memory.py analyze                  # 전체 분석
    python3 memory.py analyze --project NAME   # 특정 프로젝트만
    python3 memory.py summary                  # 간단 요약 출력
"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

SCORES_FILE = Path.home() / ".config" / "self-improving-skill" / "scores.json"
MEMORY_FILE = Path.home() / ".config" / "self-improving-skill" / "memory.json"


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


def load_scores() -> list[dict]:
    data = load_json(SCORES_FILE)
    return data.get("sessions", [])


def load_memory() -> dict:
    data = load_json(MEMORY_FILE)
    if not data:
        data = {
            "version": 1,
            "last_analyzed": None,
            "total_sessions_analyzed": 0,
            "strategies": [],
            "domain_knowledge": {},
            "anti_patterns": [],
            "trends": {},
        }
    return data


# ── 분석 함수들 ──


def analyze_by_project(sessions: list[dict]) -> dict:
    """프로젝트별 통계를 집계한다."""
    projects = defaultdict(lambda: {
        "session_count": 0,
        "total_insertions": 0,
        "total_deletions": 0,
        "test_pass_rates": [],
        "lint_errors": [],
        "errors_in_sessions": 0,
    })

    for s in sessions:
        name = s.get("project", "unknown")
        p = projects[name]
        p["session_count"] += 1
        git = s.get("git", {})
        p["total_insertions"] += git.get("insertions", 0)
        p["total_deletions"] += git.get("deletions", 0)
        tests = s.get("tests", {})
        if tests.get("pass_rate") is not None:
            p["test_pass_rates"].append(tests["pass_rate"])
        lint = s.get("lint", {})
        p["lint_errors"].append(lint.get("errors", 0))
        session = s.get("session", {})
        p["errors_in_sessions"] += session.get("errors_in_session", 0)

    # 요약 지표 계산
    result = {}
    for name, p in projects.items():
        avg_pass = None
        if p["test_pass_rates"]:
            avg_pass = round(sum(p["test_pass_rates"]) / len(p["test_pass_rates"]), 3)
        avg_lint = 0
        if p["lint_errors"]:
            avg_lint = round(sum(p["lint_errors"]) / len(p["lint_errors"]), 1)
        result[name] = {
            "sessions": p["session_count"],
            "lines_added": p["total_insertions"],
            "lines_removed": p["total_deletions"],
            "avg_test_pass_rate": avg_pass,
            "avg_lint_errors": avg_lint,
            "total_session_errors": p["errors_in_sessions"],
        }
    return result


def detect_anti_patterns(sessions: list[dict]) -> list[dict]:
    """반복되는 문제 패턴을 감지한다."""
    patterns = []

    # 패턴 1: 테스트 없는 프로젝트에서 계속 작업
    no_test_projects = Counter()
    for s in sessions:
        tests = s.get("tests", {})
        if tests.get("total", 0) == 0:
            no_test_projects[s.get("project", "unknown")] += 1

    for proj, count in no_test_projects.items():
        if count >= 3:
            patterns.append({
                "pattern": "테스트 없이 반복 작업",
                "project": proj,
                "count": count,
                "suggestion": "기본 테스트를 먼저 추가하면 회귀 버그를 방지할 수 있다",
            })

    # 패턴 2: lint 에러가 계속 있는 프로젝트
    high_lint_projects = Counter()
    for s in sessions:
        lint = s.get("lint", {})
        if lint.get("errors", 0) > 5:
            high_lint_projects[s.get("project", "unknown")] += 1

    for proj, count in high_lint_projects.items():
        if count >= 2:
            patterns.append({
                "pattern": "lint 에러 방치",
                "project": proj,
                "count": count,
                "suggestion": "세션 시작 시 lint를 먼저 돌려서 기존 에러를 정리하면 좋다",
            })

    # 패턴 3: 세션 에러가 많음
    high_error_sessions = 0
    for s in sessions:
        session = s.get("session", {})
        if session.get("errors_in_session", 0) > 3:
            high_error_sessions += 1

    if high_error_sessions >= 3:
        patterns.append({
            "pattern": "세션 중 에러 빈발",
            "count": high_error_sessions,
            "suggestion": "에러가 반복되면 접근 방식을 바꿔보는 것이 낫다 — 같은 방법 재시도보다 원인 분석 먼저",
        })

    # 패턴 4: 미커밋 변경 방치
    uncommitted_count = 0
    for s in sessions:
        git = s.get("git", {})
        if git.get("has_uncommitted", False):
            uncommitted_count += 1

    if uncommitted_count > len(sessions) * 0.7 and len(sessions) >= 3:
        patterns.append({
            "pattern": "미커밋 변경 자주 방치",
            "count": uncommitted_count,
            "suggestion": "작업 단위를 작게 나누어 자주 커밋하면 되돌리기가 쉬워진다",
        })

    return patterns


def detect_trends(sessions: list[dict]) -> dict:
    """시간에 따른 추세를 감지한다."""
    if len(sessions) < 4:
        return {"status": "데이터 부족 (최소 4개 세션 필요)"}

    mid = len(sessions) // 2
    first_half = sessions[:mid]
    second_half = sessions[mid:]

    def avg_metric(sess_list, path):
        vals = []
        for s in sess_list:
            obj = s
            for key in path:
                obj = obj.get(key, {}) if isinstance(obj, dict) else {}
            if isinstance(obj, (int, float)):
                vals.append(obj)
        return sum(vals) / len(vals) if vals else 0

    trends = {}

    # 테스트 통과율 추세
    first_pass = avg_metric(first_half, ["tests", "pass_rate"])
    second_pass = avg_metric(second_half, ["tests", "pass_rate"])
    if first_pass or second_pass:
        diff = round(second_pass - first_pass, 3)
        trends["test_pass_rate"] = {
            "first_half": round(first_pass, 3),
            "second_half": round(second_pass, 3),
            "change": diff,
            "direction": "↑ 개선" if diff > 0 else "↓ 퇴보" if diff < 0 else "→ 유지",
        }

    # 세션 에러 추세
    first_err = avg_metric(first_half, ["session", "errors_in_session"])
    second_err = avg_metric(second_half, ["session", "errors_in_session"])
    diff = round(second_err - first_err, 1)
    trends["session_errors"] = {
        "first_half": round(first_err, 1),
        "second_half": round(second_err, 1),
        "change": diff,
        "direction": "↑ 악화" if diff > 0 else "↓ 개선" if diff < 0 else "→ 유지",
    }

    return trends


def generate_strategies(anti_patterns: list[dict], trends: dict, project_stats: dict) -> list[dict]:
    """안티패턴과 추세에서 전략을 도출한다."""
    strategies = []
    now = datetime.now().strftime("%Y-%m-%d")

    for ap in anti_patterns:
        strategies.append({
            "created": now,
            "source": f"안티패턴 감지: {ap['pattern']}",
            "strategy": ap["suggestion"],
            "project": ap.get("project"),
            "active": True,
        })

    # 추세 기반 전략
    test_trend = trends.get("test_pass_rate", {})
    if test_trend.get("change", 0) < -0.1:
        strategies.append({
            "created": now,
            "source": f"테스트 통과율 하락: {test_trend.get('first_half')} → {test_trend.get('second_half')}",
            "strategy": "코드 수정 전 기존 테스트를 먼저 돌려서 현재 상태를 확인하라",
            "active": True,
        })

    return strategies


# ── 메인 커맨드 ──


def cmd_analyze(project_filter: str | None = None):
    """전체 분석을 실행하고 memory.json을 갱신한다."""
    sessions = load_scores()
    if not sessions:
        print("scores.json에 데이터가 없습니다. 세션을 더 쌓아주세요.")
        return

    if project_filter:
        sessions = [s for s in sessions if s.get("project") == project_filter]

    memory = load_memory()

    # 분석 실행
    project_stats = analyze_by_project(sessions)
    anti_patterns = detect_anti_patterns(sessions)
    trends = detect_trends(sessions)
    new_strategies = generate_strategies(anti_patterns, trends, project_stats)

    # memory 갱신 (기존 전략에 새 전략 추가, 중복 제거)
    existing_sources = {s["source"] for s in memory.get("strategies", [])}
    for ns in new_strategies:
        if ns["source"] not in existing_sources:
            memory.setdefault("strategies", []).append(ns)

    memory["anti_patterns"] = anti_patterns
    memory["trends"] = trends
    memory["domain_knowledge"] = project_stats
    memory["last_analyzed"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    memory["total_sessions_analyzed"] = len(sessions)

    save_json(MEMORY_FILE, memory)

    # 결과 출력
    print(json.dumps({
        "sessions_analyzed": len(sessions),
        "projects": project_stats,
        "anti_patterns": anti_patterns,
        "trends": trends,
        "new_strategies": new_strategies,
    }, indent=2, ensure_ascii=False))


def cmd_summary():
    """memory.json의 간단 요약을 출력한다."""
    memory = load_memory()
    if not memory.get("last_analyzed"):
        print("아직 분석한 적이 없습니다. `python3 memory.py analyze`를 먼저 실행하세요.")
        return

    print(f"마지막 분석: {memory['last_analyzed']}")
    print(f"분석한 세션: {memory['total_sessions_analyzed']}개")
    print()

    strategies = memory.get("strategies", [])
    if strategies:
        print(f"활성 전략 ({len(strategies)}개):")
        for s in strategies:
            prefix = f"  [{s.get('project', '전체')}]" if s.get("project") else "  [전체]"
            print(f"{prefix} {s['strategy']}")
    else:
        print("활성 전략: 없음")

    anti_patterns = memory.get("anti_patterns", [])
    if anti_patterns:
        print(f"\n감지된 안티패턴 ({len(anti_patterns)}개):")
        for ap in anti_patterns:
            print(f"  - {ap['pattern']} (x{ap['count']})")

    trends = memory.get("trends", {})
    if trends and trends.get("status") != "데이터 부족 (최소 4개 세션 필요)":
        print(f"\n추세:")
        for key, t in trends.items():
            if isinstance(t, dict) and "direction" in t:
                print(f"  {key}: {t['direction']} ({t.get('first_half')} → {t.get('second_half')})")


if __name__ == "__main__":
    args = sys.argv[1:]
    cmd = args[0] if args else "summary"

    if cmd == "analyze":
        project = None
        if "--project" in args:
            idx = args.index("--project")
            if idx + 1 < len(args):
                project = args[idx + 1]
        cmd_analyze(project)
    elif cmd == "summary":
        cmd_summary()
    else:
        print(f"알 수 없는 명령: {cmd}")
        print("사용법: python3 memory.py [analyze|summary] [--project NAME]")
