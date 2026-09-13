# Temporary release icon diagnostics

Apply `0001-trace-icon-encoding-and-decoding.patch` to a private copy of the
pinned `flutter_svg` 2.3.0 package. Pair with Denial patch0018 and the matching
vector_graphics1.2.2 diagnostic. Preserve the original package cache and license.
This is an explicitly selected VM investigation, not a production dependency.

The patch retains the existing cache, Future chain and release `compute` call.
It records prepare/encode stages with capped type/hash labels. Debug builds use
a different compute implementation; debug widget tests do not qualify release
isolate behavior. The manual test executes the actual `_load` method through
real host Dart isolates with a compiler adapter:

```sh
python3 scripts/host/test-svg-stage-diagnostics.py --source COPIED_PACKAGE/lib/src/loaders.dart --dart BOUNDED_DART --output FRESH_DIRECTORY
```

Keep package source hashes, patch identities, package overrides, compiler inputs
and ARM64 AOT output identities together. The test is not real SVG decoding,
Flutter rendering, VM or phone proof. No phone builder selects this patch.
