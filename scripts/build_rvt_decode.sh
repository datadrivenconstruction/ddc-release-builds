#!/usr/bin/env bash
# Attested-style release build of rvt-decode (same gates as the engine CI), run inside the source checkout.
set -euo pipefail
sha() { if command -v sha256sum >/dev/null; then sha256sum < "$1"; else shasum -a 256 < "$1"; fi | cut -d' ' -f1; }
rustup show active-toolchain >/dev/null 2>&1 || rustup toolchain install
export RUSTC="$(rustup which rustc)"
export RVT_ATTESTED_RELEASE=1
export RVT_RELEASE_GIT_PATH="$(command -v git)"
export RVT_RELEASE_EXPECTED_COMMIT="$(git rev-parse HEAD)"
export RVT_RELEASE_EXPECTED_CARGO_LOCK_SHA256="$(sha Cargo.lock)"
export RVT_RELEASE_EXPECTED_RUSTC_SHA256="$(sha "$RUSTC")"
ws="$(pwd)"; home="${CARGO_HOME:-$HOME/.cargo}"; hm="$HOME"
export RUSTFLAGS="-C debuginfo=0 --remap-path-prefix=${ws}=. --remap-path-prefix=${home}=cargo --remap-path-prefix=${hm}=~"
export CARGO_PROFILE_RELEASE_LTO=fat CARGO_PROFILE_RELEASE_CODEGEN_UNITS=1 \
       CARGO_PROFILE_RELEASE_PANIC=abort CARGO_PROFILE_RELEASE_STRIP=symbols CARGO_PROFILE_RELEASE_DEBUG=0
cargo build -q --release --locked -p rvt-cli --bin rvt-decode
