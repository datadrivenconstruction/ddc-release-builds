#!/usr/bin/env bash
# Pack and encrypt the hidden build logs (AES-256, key = secret LOG_KEY) so that only the owner can read them.
set -euo pipefail
dbg="${RUNNER_TEMP}/dbg"
[ -d "$dbg" ] || { echo "no logs"; exit 0; }
[ -n "${LOG_KEY:-}" ] || { echo "LOG_KEY not set; logs are discarded"; exit 0; }
mkdir -p debug-out
tar -C "$dbg" -czf - . | openssl enc -aes-256-cbc -pbkdf2 -salt -pass env:LOG_KEY -out "debug-out/$1.enc"
ls -l debug-out | tail -n +2 | awk '{print $5" bytes encrypted"}'
