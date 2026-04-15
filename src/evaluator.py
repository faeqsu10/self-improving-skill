#!/usr/bin/env python3
"""
Self-Improving Skill — Phase 1: Auto Evaluator

Claude Code Stop hook에서 호출되어 세션 결과를 자동 평가하고 저장한다.
HyperAgents의 PerformanceTracker 개념을 축소 구현.

사용법:
    echo '{"session_id":"...","cwd":"...","transcript_path":"..."}' | python3 evaluator.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# 평가 결과 저장 경로
SCORES_DIR = Path.home() / ".config" / "self-improving-skill"
SCORES_FILE = SCORES_DIR / "scores.json"


def run_cmd(cmd: list[str], cwd: str, timeout: int = 30) -> tuple[int, str]:
    """명령 실행 후 (returncode, stdout) 반환."""
    try:
        result = subprocess.run(
            cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return -1, ""


def is_git_repo(cwd: str) -> bool:
    code, _ = run_cmd(["git", "rev-parse", "--is-inside-work-tree"], cwd)
    return code == 0


def get_git_metrics(cwd: str) -> dict:
    """git diff에서 변경량 지표를 추출한다."""
    metrics = {"files_changed": 0, "insertions": 0, "deletions": 0, "has_uncommitted": False}

    # 커밋되지 않은 변경 확인
    code, output = run_cmd(["git", "status", "--porcelain"], cwd)
    if output:
        metrics["has_uncommitted"] = True
        metrics["files_changed"] = len([l for l in output.splitlines() if l.strip()])

    # 최근 커밋의 diff stat (이번 세션에서 커밋했을 수 있음)
    code, output = run_cmd(["git", "diff", "--shortstat", "HEAD~1"], cwd)
    if code == 0 and output:
        parts = output.split(",")
        for part in parts:
            part = part.strip()
            if "file" in part:
                metrics["files_changed"] = max(metrics["files_changed"], int(part.split()[0]))
            elif "insertion" in part:
                metrics["insertions"] = int(part.split()[0])
            elif "deletion" in part:
                metrics["deletions"] = int(part.split()[0])

    return metrics


def detect_test_runner(cwd: str) -> str | None:
    """프로젝트의 테스트 러너를 감지한다."""
    checks = [
        (["pytest", "--version"], "pytest"),
        (["python3", "-m", "pytest", "--version"], "pytest"),
        (["npm", "test", "--", "--help"], "npm"),
    ]
    # pyproject.toml이나 package.json으로 빠르게 판단
    if (Path(cwd) / "pyproject.toml").exists() or (Path(cwd) / "setup.py").exists():
        return "pytest"
    if (Path(cwd) / "package.json").exists():
        return "npm"
    return None


def run_tests(cwd: str) -> dict:
    """테스트를 실행하고 결과를 반환한다."""
    result = {"runner": None, "passed": 0, "failed": 0, "total": 0, "pass_rate": None}
    runner = detect_test_runner(cwd)

    if runner == "pytest":
        code, output = run_cmd(
            ["python3", "-m", "pytest", "--tb=no", "-q", "--no-header"], cwd, timeout=60
        )
        result["runner"] = "pytest"
        # "5 passed, 1 failed" 같은 마지막 줄 파싱
        for line in reversed(output.splitlines()):
            if "passed" in line or "failed" in line:
                for part in line.split(","):
                    part = part.strip()
                    if "passed" in part:
                        result["passed"] = int(part.split()[0])
                    elif "failed" in part:
                        result["failed"] = int(part.split()[0])
                break
        result["total"] = result["passed"] + result["failed"]
        if result["total"] > 0:
            result["pass_rate"] = round(result["passed"] / result["total"], 3)

    return result


def run_lint(cwd: str) -> dict:
    """린트 검사를 실행한다."""
    result = {"tool": None, "errors": 0, "warnings": 0}

    # ruff 우선, 없으면 flake8
    code, output = run_cmd(["ruff", "check", "--statistics", "-q", "."], cwd, timeout=30)
    if code != -1:
        result["tool"] = "ruff"
        result["errors"] = len([l for l in output.splitlines() if l.strip()])
        return result

    code, output = run_cmd(["flake8", "--count", "--statistics", "."], cwd, timeout=30)
    if code != -1:
        result["tool"] = "flake8"
        result["errors"] = len([l for l in output.splitlines() if l.strip()])

    return result


def count_transcript_turns(transcript_path: str) -> dict:
    """대화 로그에서 턴 수와 도구 사용 횟수를 센다."""
    result = {"turns": 0, "tool_uses": 0, "errors_in_session": 0}
    if not transcript_path or not Path(transcript_path).exists():
        return result

    try:
        with open(transcript_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    if entry.get("role") == "assistant":
                        result["turns"] += 1
                    if entry.get("role") == "tool_result":
                        result["tool_uses"] += 1
                    # 에러 감지
                    text = str(entry.get("content", ""))
                    if "error" in text.lower() or "traceback" in text.lower():
                        result["errors_in_session"] += 1
                except json.JSONDecodeError:
                    continue
    except Exception:
        pass

    return result


def load_scores() -> dict:
    """기존 scores.json을 로드한다."""
    if SCORES_FILE.exists():
        try:
            with open(SCORES_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"version": 1, "sessions": []}


def save_scores(data: dict):
    """scores.json에 저장한다."""
    SCORES_DIR.mkdir(parents=True, exist_ok=True)
    with open(SCORES_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def evaluate(hook_input: dict) -> dict:
    """세션을 평가하고 결과를 반환한다."""
    cwd = hook_input.get("cwd", os.getcwd())
    session_id = hook_input.get("session_id", "unknown")
    transcript_path = hook_input.get("transcript_path", "")

    # 프로젝트 이름 추출
    project_name = Path(cwd).name

    # 각 지표 수집
    git_metrics = get_git_metrics(cwd) if is_git_repo(cwd) else {}
    test_result = run_tests(cwd)
    lint_result = run_lint(cwd)
    transcript_info = count_transcript_turns(transcript_path)

    # 세션 레코드 구성
    session_record = {
        "session_id": session_id,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "project": project_name,
        "cwd": cwd,
        "git": git_metrics,
        "tests": test_result,
        "lint": lint_result,
        "session": transcript_info,
    }

    return session_record


def find_project_root(cwd: str) -> str | None:
    """cwd에서 위로 올라가며 .self-improve 파일이 있는 프로젝트 루트를 찾는다."""
    current = Path(cwd).resolve()
    home = Path.home().resolve()
    while current >= home:
        if (current / ".self-improve").exists():
            return str(current)
        if current == home:
            break
        current = current.parent
    return None


def load_project_config(project_root: str) -> dict:
    """프로젝트의 .self-improve 파일에서 커스텀 설정을 읽는다."""
    config_path = Path(project_root) / ".self-improve"
    try:
        content = config_path.read_text().strip()
        if content:
            return json.loads(content)
    except (json.JSONDecodeError, IOError):
        pass
    return {}


def main():
    # stdin에서 hook 데이터 읽기
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    cwd = hook_input.get("cwd", os.getcwd())

    # .self-improve 파일이 있는 프로젝트만 수집
    project_root = find_project_root(cwd)
    if project_root is None:
        return  # 이 프로젝트는 자기 개선 대상이 아님 → 조용히 종료

    # 프로젝트 루트를 cwd로 사용 (하위 디렉토리에서 실행해도 일관성 유지)
    hook_input["cwd"] = project_root

    # 평가 실행
    record = evaluate(hook_input)

    # 프로젝트별 커스텀 설정 반영
    config = load_project_config(project_root)
    if config:
        record["config"] = config

    # 저장
    scores = load_scores()
    scores["sessions"].append(record)

    # 최근 100개만 유지
    if len(scores["sessions"]) > 100:
        scores["sessions"] = scores["sessions"][-100:]

    save_scores(scores)


if __name__ == "__main__":
    main()
