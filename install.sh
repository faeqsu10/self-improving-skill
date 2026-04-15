#!/bin/bash
# Self-Improving Skill 설치 스크립트
# 사용법: curl -fsSL https://raw.githubusercontent.com/faeqsu10/self-improving-skill/main/install.sh | bash
set -e

REPO_URL="https://github.com/faeqsu10/self-improving-skill.git"
INSTALL_DIR="$HOME/.config/self-improving-skill"
SETTINGS_FILE="$HOME/.claude/settings.json"

echo "╭──────────────────────────────────────╮"
echo "│   Self-Improving Skill 설치          │"
echo "╰──────────────────────────────────────╯"
echo

# 1. Python 확인
if ! command -v python3 &>/dev/null; then
  echo "❌ python3이 필요합니다."
  exit 1
fi
echo "  Python: $(python3 --version)"

# 2. 소스 다운로드
echo
if [ -d "$INSTALL_DIR/src" ]; then
  echo "  기존 설치 발견 → 업데이트 중..."
  cd "$INSTALL_DIR/repo" && git pull --quiet 2>/dev/null || true
else
  echo "  소스 다운로드 중..."
  mkdir -p "$INSTALL_DIR"
  git clone --depth 1 "$REPO_URL" "$INSTALL_DIR/repo" 2>/dev/null
fi

# src 심볼릭 링크
ln -sfn "$INSTALL_DIR/repo/src" "$INSTALL_DIR/src"
echo "  설치 경로: $INSTALL_DIR/src/"

# 3. Claude Code settings.json에 Stop hook 등록
echo
mkdir -p "$HOME/.claude"

if [ ! -f "$SETTINGS_FILE" ]; then
  echo '{}' > "$SETTINGS_FILE"
fi

HOOK_CMD="python3 $INSTALL_DIR/src/evaluator.py && python3 $INSTALL_DIR/src/memory.py analyze > /dev/null 2>&1 && python3 $INSTALL_DIR/src/injector.py"

# 이미 등록되어 있는지 확인
if grep -q "self-improving-skill" "$SETTINGS_FILE" 2>/dev/null; then
  echo "  Hook: 이미 등록됨 (스킵)"
else
  python3 -c "
import json, os

f = '$SETTINGS_FILE'
s = json.load(open(f))
if 'hooks' not in s:
    s['hooks'] = {}
if 'Stop' not in s['hooks']:
    s['hooks']['Stop'] = []

s['hooks']['Stop'].append({
    'matcher': '.*',
    'hooks': [{
        'type': 'command',
        'command': '$HOOK_CMD'
    }]
})
json.dump(s, open(f, 'w'), indent=2)
print('  Hook: Stop hook 등록 완료')
"
fi

# 4. 스킬 설치
SKILL_DIR="$HOME/.claude/skills/self-improve"
mkdir -p "$SKILL_DIR"
cp "$INSTALL_DIR/repo/skill/SKILL.md" "$SKILL_DIR/SKILL.md"
echo "  Skill: /self-improve 설치 완료"

# 5. 완료
echo
echo "╭──────────────────────────────────────╮"
echo "│   설치 완료!                          │"
echo "╰──────────────────────────────────────╯"
echo
echo "  사용법:"
echo "    1. 프로젝트에서 활성화:"
echo "       cd ~/your-project"
echo "       touch .self-improve"
echo
echo "    2. 이후 Claude Code를 쓰면 자동으로 데이터 수집"
echo
echo "    3. 분석 보기:"
echo "       /self-improve"
echo
echo "    4. 비활성화:"
echo "       rm .self-improve"
