#!/usr/bin/env bash
# Smoke test of the packaged rvt-decode on a small open sample (MIT, fixed commit, sha256 verified).
#   smoke_rvt.sh <path-to-rvt-decode> <work-dir>
set -euo pipefail
exe="$1"; work="$2"
url="https://raw.githubusercontent.com/mcneel/rhino.inside-revit/9d33c8545c29d344e54185f67ceebc47070e4e24/docs/static/src/gh-screencaps/revit-openings_v22.rvt"
want="0873240d8078bbe75f1c372e681f3dd2af46661b5658880522c68977baac29d4"
mkdir -p "$work"
"$exe" --version > "$work/version.txt" && [ -s "$work/version.txt" ] || { echo "no version output"; exit 1; }
curl -fsSL --retry 3 "$url" -o "$work/sample.rvt"
if command -v sha256sum >/dev/null; then got=$(sha256sum < "$work/sample.rvt" | cut -d' ' -f1); else got=$(shasum -a 256 < "$work/sample.rvt" | cut -d' ' -f1); fi
[ "$got" = "$want" ] || { echo "sample hash mismatch"; exit 1; }
set +e
"$exe" "$work/sample.rvt" --out "$work/out" --ifc
rc=$?
set -e
echo "exit code $rc"
[ "$rc" = 0 ] || [ "$rc" = 2 ] || exit 1
ifc=$(find "$work/out" -name '*.ifc' | head -1)
glb=$(find "$work/out" -name '*.glb' | head -1)
csv=$(find "$work/out" -name 'elements.csv' | head -1)
[ -s "$ifc" ] && head -c 20 "$ifc" | grep -q 'ISO-10303-21' || { echo "IFC missing or invalid"; exit 1; }
[ -s "$glb" ] && [ "$(head -c 4 "$glb")" = "glTF" ] || { echo "GLB missing or invalid"; exit 1; }
[ -s "$csv" ] && [ "$(wc -l < "$csv" | tr -d ' ')" -gt 1 ] || { echo "elements.csv missing or empty"; exit 1; }
echo "ifc $(wc -c < "$ifc") glb $(wc -c < "$glb") csv lines $(wc -l < "$csv" | tr -d ' ')"
