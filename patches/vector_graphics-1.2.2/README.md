# Temporary icon decode diagnostics

Apply `0001-trace-icon-encoding-and-decoding.patch` to a private copy of pinned
vector_graphics1.2.2 with the flutter_svg2.3.0 and Denial0018 diagnostics.
Keep original package source/licenses/cache intact. The patch logs existing
picture requests, pending/cache results, decode begin/end, mounted error,
setState and widget-build boundaries. It adds no timers, retries, Future chain,
cache changes or frame requests. A build-picture record is not presentation.
Each isolate limits this package to64 records; worker-isolate totals are separate.
These patches require explicit VM build overrides and grant no phone authority.

Apply `0002-trace-picture-paint.patch` after0001 for capped picture-paint
records with object identity, size, opacity, monotonic time and frame timestamp.
This adds no frame scheduling, strategy, canvas operation or lifetime changes.
It remains VM-only diagnostic instrumentation, not a rendering correction.

Run `test-vector-picture-paint.py --package PATCHED_PACKAGE --baseline-package
BASELINE_PACKAGE --dart DART --output FRESH_DIRECTORY` to execute the actual
paint method and helper with recording-canvas adapters; this does not prove
Flutter/GPU painting. Compile the real shell against the patched package and
retain exact input hashes. The existing mandatory collector tests cover bounded
transport; its shared budget can truncate late records, so absence alone is not
proof that painting failed to occur.
