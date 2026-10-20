#!/usr/bin/env bash
# Quiet runner for a PUBLIC repository whose logs are visible to everyone.
#   q.sh <label> <command...>
# The full output goes to $RUNNER_TEMP/dbg/<label>.log (encrypted at the end of the job, never
# printed). On failure only a sanitized summary is shown: no source lines, no paths, no messages.
label="$1"; shift
dbg="${RUNNER_TEMP:-/tmp}/dbg"; mkdir -p "$dbg"
log="$dbg/$label.log"
if "$@" >"$log" 2>&1; then
  echo "[$label] ok ($(wc -l <"$log" | tr -d ' ') output lines hidden)"
else
  rc=$?
  echo "[$label] FAILED, exit code $rc (output hidden, see the encrypted debug artifact)"
  {
    grep -oE '^error(\[E[0-9]{4}\])?' "$log" | sort | uniq -c | sed 's/^/  rust: /'
    grep -oE '^[A-Za-z_.]*(Error|Exception)\b' "$log" | sort | uniq -c | sed 's/^/  python: /'
    grep -cE '^(FAIL|ERROR):' "$log" | sed 's/^/  test failures: /'
  } | head -15
  exit "$rc"
fi
