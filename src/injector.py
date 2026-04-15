#!/usr/bin/env python3
"""
Self-Improving Skill — Phase 3: Strategy Proposer

전략을 CLAUDE.md에 자동 주입하지 않고, 제안 파일에 저장만 한다.
사용자가 /self-improve로 리뷰하고 승인해야 CLAUDE.md에 반영된다.

Stop hook에서 자동 실행:
    hook-runner.py → evaluator → memory → injector(이 파일)

이 파일은 .self-improve-strategies.md에 제안을 저장할 뿐,
CLAUDE.md는 건드리지 않는다.
"""

import json
import os
import sys
from pathlib import Path

MEMORY_FILE = Path.home() / ".config" / "self-improving-skill" / "memory.json"

MARKER_START = "<!-- self-improve:start -->"
MARKER_END = "<!-- self-improve:end -->"


def load_memory() -> dict:
    if MEMORY_FILE.exists():
        try:
            with open(MEMORY_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


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


def generate_proposals(memory: dict, project_name: str | None = None) -> str:
    """해당 프로젝트에 맞는 전략 제안을 생성한다."""
    all_strategies = [s for s in memory.get("strategies", []) if s.get("active")]
    all_anti_patterns = memory.get("anti_patterns", [])
    last_analyzed = memory.get("last_analyzed", "없음")

    # 해당 프로젝트 + 전체 전략만 필터링
    strategies = [s for s in all_strategies
                  if s.get("project") is None or s.get("project") == project_name]
    anti_patterns = [ap for ap in all_anti_patterns
                     if ap.get("project") is None or ap.get("project") == project_name]

    if not strategies and not anti_patterns:
        return ""

    lines = [
        f"# 자기 개선 제안 (자동 생성)",
        f"",
        f"> 이 파일은 self-improving-skill이 자동으로 갱신합니다.",
        f"> CLAUDE.md에 적용하려면 `/self-improve`를 실행하고 승인하세요.",
        f"> 마지막 분석: {last_analyzed}",
        "",
    ]

    if strategies:
        lines.append("## 제안된 전략")
        for s in strategies:
            verified = s.get("verified", "pending")
            badge = {"verified": "[검증됨]", "unverified": "[미검증]", "neutral": "[효과불명]"}.get(verified, "[대기]")
            lines.append(f"- {badge} {s['strategy']}")
            if s.get("source"):
                lines.append(f"  - 근거: {s['source']}")
        lines.append("")

    if anti_patterns:
        lines.append("## 감지된 안티패턴")
        for ap in anti_patterns:
            lines.append(f"- {ap['pattern']} (x{ap['count']})")
            lines.append(f"  - 제안: {ap['suggestion']}")
        lines.append("")

    return "\n".join(lines)


def main():
    # stdin에서 hook 데이터 읽기
    try:
        hook_input = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        hook_input = {}

    cwd = hook_input.get("cwd", os.getcwd())

    # .self-improve가 있는 프로젝트만 처리
    project_root = find_project_root(cwd)
    if project_root is None:
        return

    project_name = Path(project_root).name
    proposals_path = Path(project_root) / ".self-improve-strategies.md"

    memory = load_memory()
    content = generate_proposals(memory, project_name)

    if content:
        proposals_path.write_text(content)
    elif proposals_path.exists():
        proposals_path.unlink()  # 제안이 없으면 파일 삭제


if __name__ == "__main__":
    main()
