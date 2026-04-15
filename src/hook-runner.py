#!/usr/bin/env python3
"""
Self-Improving Skill — Stop Hook Runner

Stop hook에서 호출되는 단일 진입점.
stdin의 hook 데이터를 읽어서 evaluator → memory → injector를 순차 실행한다.
각 단계에 동일한 hook_input을 전달한다.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SRC_DIR = Path(__file__).parent


def main():
    # stdin에서 hook 데이터 읽기
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    hook_json = json.dumps(hook_input)

    # ① evaluator: 세션 평가 → scores.json
    subprocess.run(
        ["python3", str(SRC_DIR / "evaluator.py")],
        input=hook_json, text=True, capture_output=True,
    )

    # ② memory: 패턴 분석 → memory.json
    subprocess.run(
        ["python3", str(SRC_DIR / "memory.py"), "analyze"],
        capture_output=True,
    )

    # ③ injector: 전략 → 프로젝트 CLAUDE.md
    subprocess.run(
        ["python3", str(SRC_DIR / "injector.py")],
        input=hook_json, text=True, capture_output=True,
    )


if __name__ == "__main__":
    main()
