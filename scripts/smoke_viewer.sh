#!/usr/bin/env bash
# Start the Data Viewer for a few seconds and check that it stays alive (window opened) and ends without errors.
#   smoke_viewer.sh linux <file.AppImage> | macos <path-to-.app>
set -uo pipefail
kind="$1"; target="$2"; wait_s=12
if [ "$kind" = linux ]; then
  export APPIMAGE_EXTRACT_AND_RUN=1 GDK_BACKEND=x11 LIBGL_ALWAYS_SOFTWARE=1 WEBKIT_DISABLE_COMPOSITING_MODE=1 NO_AT_BRIDGE=1
  inner=$(mktemp)
  cat > "$inner" <<EOS
#!/usr/bin/env bash
"$target" > "\$1" 2>&1 &
pid=\$!
sleep $wait_s
if ! kill -0 \$pid 2>/dev/null; then wait \$pid; echo "exited early, code \$?"; exit 1; fi
tree=\$(xwininfo -root -tree 2>/dev/null || true)
echo "\$tree" | grep -i -E 'ddc|viewer' >/dev/null || { echo "no application window found"; kill \$pid; exit 1; }
kill -TERM \$pid; sleep 2; kill -KILL \$pid 2>/dev/null || true
exit 0
EOS
  chmod +x "$inner"
  log=$(mktemp)
  xvfb-run -a --server-args="-screen 0 1280x800x24" "$inner" "$log"; rc=$?
else
  exe=$(ls "$target"/Contents/MacOS/* | head -1)
  log=$(mktemp)
  "$exe" > "$log" 2>&1 &
  pid=$!
  sleep $wait_s
  if kill -0 $pid 2>/dev/null; then rc=0; kill -TERM $pid; sleep 2; kill -KILL $pid 2>/dev/null || true; else wait $pid; rc=$?; echo "exited early, code $rc"; fi
fi
if grep -a -i -E 'panicked|cannot open shared object|error while loading|segmentation fault|Gtk-WARNING \*\* .*cannot|failed to' "$log" >/dev/null; then
  echo "errors in the start-up output:"; grep -a -i -E 'panicked|cannot open shared object|error while loading|segmentation fault|failed to' "$log" | head -5 | cut -c1-200
  rc=1
fi
cp "$log" "${RUNNER_TEMP:-/tmp}/dbg/viewer-start.log" 2>/dev/null || true
[ "$rc" = 0 ] && echo "viewer smoke OK"
exit "$rc"
