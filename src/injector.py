#!/usr/bin/env python3
"""
Self-Improving Skill — Phase 3: Strategy Injector

memory.json의 전략을 해당 프로젝트의 CLAUDE.md에 자동 주입한다.
프로젝트별로 분리되어 다른 프로젝트에 영향을 주지 않는다.

Stop hook에서 evaluator.py 다음에 실행:
    python3 evaluator.py  →  python3 injector.py

stdin으로 hook 데이터를 받아 cwd에서 프로젝트를 판별한다.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path.home() / ".config" / "self-improving-skill" / "memory.json"

# 주입 블록의 시작/끝 마커
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


def generate_block(memory: dict, project_name: str | None = None) -> str:
    """memory.json에서 해당 프로젝트에 맞는 전략 블록을 생성한다."""
    all_strategies = [s for s in memory.get("strategies", []) if s.get("active")]
    all_anti_patterns = memory.get("anti_patterns", [])
    last_analyzed = memory.get("last_analyzed", "없음")

    # 해당 프로젝트 + 전체(project=null) 전략만 필터링
    strategies = [s for s in all_strategies
                  if s.get("project") is None or s.get("project") == project_name]
    anti_patterns = [ap for ap in all_anti_patterns
                     if ap.get("project") is None or ap.get("project") == project_name]

    if not strategies and not anti_patterns:
        return ""

    lines = [
        MARKER_START,
        "# 자기 개선 전략 (자동 생성)",
        f"<!-- 마지막 분석: {last_analyzed} | 이 블록은 self-improving-skill이 자동 관리합니다 -->",
        "",
    ]

    if strategies:
        lines.append("## 작업 전략")
        for s in strategies:
            scope = f"[{s['project']}]" if s.get("project") else "[전체]"
            lines.append(f"- {scope} {s['strategy']}")
        lines.append("")

    if anti_patterns:
        lines.append("## 주의할 패턴")
        for ap in anti_patterns:
            proj = f" ({ap['project']})" if ap.get("project") else ""
            lines.append(f"- {ap['pattern']}{proj} — {ap['suggestion']}")
        lines.append("")

    lines.append(MARKER_END)
    return "\n".join(lines)


def inject(claude_md_path: Path, block: str):
    """프로젝트의 CLAUDE.md에 전략 블록을 주입/갱신한다."""
    if not claude_md_path.exists():
        if not block:
            return  # 전략도 없고 CLAUDE.md도 없으면 아무것도 안 함
        claude_md_path.write_text(block + "\n")
        return

    content = claude_md_path.read_text()

    # 기존 블록이 있으면 교체
    if MARKER_START in content:
        start = content.index(MARKER_START)
        end = content.index(MARKER_END) + len(MARKER_END)
        if block:
            content = content[:start] + block + content[end:]
        else:
            # 전략이 없으면 블록 자체를 제거
            content = content[:start].rstrip("\n") + content[end:].lstrip("\n")
    elif block:
        # 기존 블록이 없으면 맨 끝에 추가
        content = content.rstrip("\n") + "\n\n" + block + "\n"

    claude_md_path.write_text(content)


def main():
    # stdin에서 hook 데이터 읽기 (cwd 판별용)
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
    claude_md_path = Path(project_root) / "CLAUDE.md"

    memory = load_memory()
    block = generate_block(memory, project_name)
    inject(claude_md_path, block)


if __name__ == "__main__":
    main()
