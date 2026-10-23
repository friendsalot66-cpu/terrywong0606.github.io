#!/usr/bin/env bash
# deploy.sh — stamp the build marker, sanity-check, commit and push.
#
# Every deploy goes through here so the running page is always identifiable:
# the header chip and window.BUILD_INFO change with each push, which is the
# fastest way to tell "the deploy is live" from "the browser is serving cache".
#
#   ./code/deploy.sh -m "fix: ..."            # patch bump + push
#   ./code/deploy.sh -m "feat: ..." --minor   # minor bump
#   ./code/deploy.sh -m "chore: ..." --no-bump
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

MSG=""
BUMP="patch"
while [ $# -gt 0 ]; do
  case "$1" in
    -m|--message) MSG="$2"; shift 2 ;;
    --minor) BUMP="minor"; shift ;;
    --major) BUMP="major"; shift ;;
    --no-bump) BUMP=""; shift ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

if [ -z "$MSG" ]; then echo "usage: $0 -m \"commit message\" [--minor|--major|--no-bump]" >&2; exit 2; fi

PY="${PY:-/home/erry/ai-stack-venv/bin/python3}"
NODE="${NODE:-/home/erry/.hermes/node/bin/node}"

# 1. stamp the marker (bumps semver unless --no-bump)
if [ -n "$BUMP" ]; then
  "$PY" code/bump_build.py --bump "$BUMP"
else
  "$PY" code/bump_build.py
fi

# 2. syntax-check the inline script before it ever reaches the remote
"$PY" - <<'PYEOF'
import io, re, sys
s = io.open("index.html", encoding="utf-8").read()
blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", s, re.S)
if not blocks:
    sys.exit("no inline script found")
io.open("/tmp/_deploy_check.js", "w", encoding="utf-8").write(max(blocks, key=len))
PYEOF
"$NODE" --check /tmp/_deploy_check.js

# 3. never ship a secret
if git -C "$ROOT" diff | grep -qE "sk-[A-Za-z0-9]{12,}"; then
  echo "REFUSING: diff contains something that looks like an API key" >&2
  exit 1
fi

# 4. commit + push
git -c safe.directory='*' add -A
git -c safe.directory='*' commit -q -m "$MSG"
git -c safe.directory='*' push -q origin main

BUILD=$("$PY" -c "
import io,re
s=io.open('index.html',encoding='utf-8').read()
m=re.search(r\"build: '([^']*)'\", s)
print(m.group(1) if m else '?')
")
echo
echo "deployed: $MSG"
echo "build   : $BUILD"
echo "npm/Actions need ~1 min; GitHub Pages CDN caches for up to 10 min."
echo "verify  : open the page and read the version chip (should read $BUILD)"
