#!/usr/bin/env python3
"""
Self-Improving Skill — Phase 3: Strategy Injector

memory.json의 전략을 ~/.claude/CLAUDE.md에 자동 주입한다.
Claude Code가 매 세션 시작 시 CLAUDE.md를 읽으므로,
여기에 전략을 넣으면 다음 세션부터 자동 반영된다.

Stop hook에서 evaluator.py 다음에 실행:
    python3 evaluator.py  →  python3 injector.py

또는 단독 실행:
    python3 injector.py
"""

import json
from datetime import datetime
from pathlib import Path

MEMORY_FILE = Path.home() / ".config" / "self-improving-skill" / "memory.json"
CLAUDE_MD = Path.home() / ".claude" / "CLAUDE.md"

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


def generate_block(memory: dict) -> str:
    """memory.json에서 Claude Code가 읽을 전략 블록을 생성한다."""
    strategies = [s for s in memory.get("strategies", []) if s.get("active")]
    anti_patterns = memory.get("anti_patterns", [])
    last_analyzed = memory.get("last_analyzed", "없음")

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


def inject(block: str):
    """CLAUDE.md에 전략 블록을 주입/갱신한다."""
    if not CLAUDE_MD.exists():
        CLAUDE_MD.parent.mkdir(parents=True, exist_ok=True)
        CLAUDE_MD.write_text(block + "\n")
        return

    content = CLAUDE_MD.read_text()

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

    CLAUDE_MD.write_text(content)


def main():
    memory = load_memory()
    block = generate_block(memory)
    inject(block)


if __name__ == "__main__":
    main()
