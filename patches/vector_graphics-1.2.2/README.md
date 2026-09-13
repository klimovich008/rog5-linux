# Temporary icon decode diagnostics

Apply `0001-trace-icon-encoding-and-decoding.patch` to a private copy of pinned
vector_graphics1.2.2 with the flutter_svg2.3.0 and Denial0018 diagnostics.
Keep original package source/licenses/cache intact. The patch logs existing
picture requests, pending/cache results, decode begin/end, mounted error,
setState and widget-build boundaries. It adds no timers, retries, Future chain,
cache changes or frame requests. A build-picture record is not presentation.
Each isolate limits this package to64 records; worker-isolate totals are separate.
These patches require explicit VM build overrides and grant no phone authority.
