# ddc-release-builds

Build runner for the free Community command-line tools and the Data Viewer of DataDrivenConstruction
on Linux (x64, arm64) and macOS (Apple Silicon, Intel).

This repository contains only a build workflow and helper scripts. The program sources live in
private repositories and are never uploaded here; build output is hidden from the public logs and
only the finished archives are published, together with `SHA256SUMS`, a keyless signature and a
build provenance attestation.

All binaries are the Community edition. Licensing and activation code is not part of these builds.

Maintainers: add the secrets `DDC_SOURCES_TOKEN` (fine-grained read-only token) and `LOG_KEY`, then
run the `build` workflow (Actions tab, "Run workflow").
