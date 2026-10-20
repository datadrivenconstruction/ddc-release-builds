#!/usr/bin/env bash
# The public builds are Community only: the licensing / activation modules must not ship.
#   community_guard.sh <dir-with-built-product>
set -euo pipefail
n=$(grep -rlaE 'ddc_licensing|licensing_host' "$1" 2>/dev/null | wc -l | tr -d ' ')
if [ "$n" != 0 ]; then echo "licensing modules found in $n file(s)"; exit 1; fi
echo "community guard OK"
