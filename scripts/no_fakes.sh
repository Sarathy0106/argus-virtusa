#!/usr/bin/env bash
#
# no_fakes.sh — anti-fake CI gate (Part 7).
#
# Fails the build if banned "fabricated result" patterns appear in the frontend
# or the backend code paths that feed the UI. Demo behaviour must come from
# seeded input data and real chaos injection, never from faked outputs.
#
# Scanned scopes:
#   - web/app, web/components, web/lib        (frontend render paths)
#   - services/gateway                        (API routers)
#   - services/agents                         (pipeline agents)
#
# Excluded: tests/ and legacy/ (retired v1 code is allowed to contain anything).

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

fail=0
report() {
  # $1 = human description, $2 = matches (may be empty)
  if [[ -n "$2" ]]; then
    echo "FAIL: $1"
    echo "$2" | sed 's/^/    /'
    fail=1
  fi
}

have_rg=0
if command -v rg >/dev/null 2>&1; then have_rg=1; fi

scan() {
  # scan <regex> <path...>; prints file:line matches, case-insensitive
  local pattern="$1"; shift
  local paths=()
  for p in "$@"; do [[ -e "$p" ]] && paths+=("$p"); done
  [[ ${#paths[@]} -eq 0 ]] && return 0
  if [[ $have_rg -eq 1 ]]; then
    rg -n --no-heading -i -e "$pattern" "${paths[@]}" 2>/dev/null
  else
    grep -rniE "$pattern" "${paths[@]}" 2>/dev/null
  fi
}

FRONTEND=(web/app web/components web/lib)
ROUTERS=(services/gateway)
AGENTS=(services/agents)

# 1. Banned literal result strings in frontend/routers.
m=$(scan 'HASH MATCH' "${FRONTEND[@]}" "${ROUTERS[@]}")
report "literal 'HASH MATCH' string" "$m"

m=$(scan 'ROLLED BACK IN' "${FRONTEND[@]}" "${ROUTERS[@]}")
report "literal 'ROLLED BACK IN' string" "$m"

# 2. 'divergence' next to a numeric literal.
m=$(scan 'divergence[^A-Za-z]{0,8}[0-9]' "${FRONTEND[@]}" "${ROUTERS[@]}")
m2=$(scan '[0-9][^A-Za-z]{0,8}divergence' "${FRONTEND[@]}" "${ROUTERS[@]}")
report "'divergence' next to a numeric literal" "$(printf '%s\n%s' "$m" "$m2" | sed '/^$/d')"

# 3. Long hex literals (>= 32 hex chars) — pre-baked hashes/merkle roots.
m=$(scan '[0-9a-f]{32,}' "${FRONTEND[@]}" "${ROUTERS[@]}")
report "hex literal of 32+ chars (pre-baked hash?)" "$m"

# 4. Mock/fake markers outside tests/ and legacy/.
m=$(scan 'sample_packet|\bmock\b|\bfake\b|\bhardcoded\b' "${FRONTEND[@]}" "${ROUTERS[@]}" "${AGENTS[@]}")
report "mock/fake/hardcoded marker" "$m"

# 5. Fixed result multipliers in agents (e.g. '* 0.04', '* 0.01').
m=$(scan '\*[[:space:]]*0\.0[0-9]+' "${AGENTS[@]}")
report "fixed result multiplier (e.g. * 0.04) in services/agents" "$m"

if [[ $fail -ne 0 ]]; then
  echo ""
  echo "no_fakes.sh: FAILED — remove fabricated values; derive them from real computation."
  exit 1
fi

echo "no_fakes.sh: PASS — no banned fabricated-result patterns found."
exit 0
