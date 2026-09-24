set -eu
export FLUTTER_ROOT=/build/checkout PUB_CACHE=/build/pub-cache FLUTTER_SUPPRESS_ANALYTICS=true CI=true
HOST=/build/engine/out/denial_host_release
cache=/build/checkout/bin/cache
mkdir -p "$cache"
# Tool bootstrap: the host graph's Dart SDK (same Dart revision as the engine
# pin) instead of a download; the stamp marks it current for engine.version.
if [ ! -d "$cache/dart-sdk" ]; then
  cp -a "$HOST/dart-sdk" "$cache/dart-sdk"
  cat /build/checkout/bin/internal/engine.version >"$cache/engine-dart-sdk.stamp"
fi
/build/checkout/bin/flutter --suppress-analytics config --no-analytics >/dev/null 2>&1 || true
/build/checkout/bin/flutter --version
cd /build/denial/dart_shell
/build/checkout/bin/flutter pub get --enforce-lockfile
rm -rf /build/assembly-r1
/build/checkout/bin/flutter assemble \
  --local-engine-src-path=/build/engine \
  --local-engine=denial_linux_release_arm64 \
  --local-engine-host=denial_host_release \
  --suppress-analytics --resource-pool-size=4 --output=/build/assembly-r1 \
  -dTargetFile=lib/main.dart -dBuildMode=release \
  -dTargetPlatform=linux-arm64 -dDartObfuscation=false \
  -dTrackWidgetCreation=true -dTreeShakeIcons=true \
  release_bundle_linux-arm64_assets
ls -la /build/assembly-r1 /build/assembly-r1/lib
