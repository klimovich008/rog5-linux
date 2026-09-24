# Denial ARM64 engine and phone bundle — September 24

Milestone 6 host side: the pinned Denial Flutter engine, host tools and the
mobile shell's AOT bundle are built for the phone. Nothing ran on the phone.
Recipe: `rog5-denial-20260910-r1/engine-recipe-r1/RECIPE.md`; stage runners
now in `scripts/host/denial/` (copies of the ones used, in the private
`engine-build-r1`).

| Stage | Result |
|---|---|
| gclient sync (resumed the priority-stopped September job) | PASS, 438 s, +24 GB |
| runhooks (sysroots, toolchains) | PASS, 80 s |
| GN: ARM64 release embedder + x64 host graph | PASS; `target_cpu=arm64`, `dart_target_arch=arm64`, `embedder_for_target=true`, `enable_lto=false`, release |
| target: `libflutter_engine.so`, platform dill, `clang_x64/gen_snapshot` | PASS, 6677 steps in 1950 s (-j4, 4 CPU/8 GiB, no network) |
| host: dart_sdk, frontend_server, const_finder, font_subset, GTK | PASS, 4082 steps in 1335 s |
| `flutter assemble … -dTargetPlatform=linux-arm64 release_bundle_linux-arm64_assets` | PASS: AArch64 `libapp.so` (10.6 MB, the five Dart snapshot symbols), 4.9 MB `flutter_assets` |

- The engine exports exactly the Denial entry points that `deniald` looks up
  (`DenialFlutterEngineSetRenderOutputs`, `…RenderOutputs`,
  `…SetExternalTextureGlStateCallback`, `…RequestFrameForExternalTextures`,
  `…ScheduleFrameForExternalTextures`). The two names in
  `configs/denial/mobile-runtime-linkage.json` are stale.
- The Flutter tool ran on the host graph's Dart SDK (Dart 3.12.2) instead of a
  download. Two environment fixes: `TAR_OPTIONS=--no-same-owner` (rootless
  podman) and a local `3.44.7` tag on the pinned framework commit (the
  no-history checkout reads as 0.0.0 otherwise). `pub get --enforce-lockfile`.
- Deviation from the recipe: -j4 instead of -j1 (wall time only).

Phone bundle `rog5-production-boot-20260923/denial-bundle-r1` (SHA256SUMS
`62286774…`, 57 MB): `deniald`, `denialctl`, `lib/libflutter_engine.so`,
`lib/libapp.so`, `data/icudtl.dat`, `data/flutter_assets`.

Still needed on the phone: `deniald` needs `libgbm.so.1` (Mesa), `libseat.so.1`,
`libinput.so.10`, `libxkbcommon.so.0`; the engine needs `libfontconfig.so.1`.
That needs a persistent root (packages survive reboots) and working GPU/DRM
from milestone 2, then the ROADMAP completion criteria on the real phone.
