#!/usr/bin/env bash
# No local paths, e-mail addresses, tokens, private keys or third-party DWG SDK names in a binary.
#   leak_guard_bin.sh <binary>   (prints counts only)
set -euo pipefail
exe="$1"
p=$(strings -n 6 "$exe" | grep -cE 'C:\Users\|D:\a\|/home/runner|/Users/runner|/home/[a-z]+/|/Users/[A-Za-z]+/' || true)
s=$(strings -n 6 "$exe" | grep -cE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.(com|org|net|io|ru|de)\b|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_|AKIA[0-9A-Z]{16}|BEGIN [A-Z ]*PRIVATE KEY' || true)
k=$( { strings -n 3 "$exe" | grep -E '(^|[^A-Za-z])ODA([^A-Za-z]|$)' || true; strings -n 3 "$exe" | grep -Ei 'teigha|open design alliance|bimrv' || true; } | wc -l | tr -d ' ')
if [ "$p" != 0 ] || [ "$s" != 0 ] || [ "$k" != 0 ]; then echo "leak guard FAILED: paths=$p secrets/mails=$s sdk=$k"; exit 1; fi
if [ "$(uname)" = Linux ] && file "$exe" | grep -q 'not stripped'; then echo "binary not stripped"; exit 1; fi
echo "leak guard OK"
