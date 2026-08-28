# Persistent slot-B loader v3 — RAM-only test 1

- Result: consumed and permanently non-retryable. Exact fastboot accepted AVB boot `806933a8fb98b118127fc72d703620e38e41bd94da56257df362c8a425a1a313` from exact commit `031f9ddf90e49e6abd1acb651933a78ff4ceaa16`; no phone partition or slot metadata was written.
- Timeline: fastboot detached at 14:21:13.963 UTC. No Loader-v3 USB identity, ACM node, or progress byte appeared. Stock slot-A recovery unauthorized ADB appeared at 14:22:11.568 UTC, 57.605 seconds later. Host kernel USB history confirms no transient loader enumeration.
- Hypothesis result: the peripheral-mode/exact-UDC correction was necessary but insufficient. V3 physically falsified it as the complete cause.
- Confirmed root cause: loader `/init` still executed `set -f`. BusyBox `ash` therefore left `/sys/class/udc/*`, `/sys/class/block/sd[a-z]`, and partition globs literal. V2 immediately classified zero UDCs; v3 could only wait to its UDC bound and fail. Storage resolution would also have failed later.
- Regression: the original fixture sourced `single_expected_udc()` without reproducing the loader's shell options and masked the defect. A corrected fail-first test now explicitly rejects `set -f`, demonstrates the helper fails with glob expansion disabled, restores expansion, and runs the full hostile UDC matrix. It exited 1 before the one-line correction and passes afterward.
- Classification: R3 exact shell/runtime semantics, matching the documented Generation-146 `set -f` failure. This is not a kernel, DT, charging, UFS, or host-lifecycle defect.
- Review escalation: Claude Opus was unavailable because local OAuth had expired. OpenCode 1.18.20 exposed no OX Alpha model in its actual model inventory. Neither absence is treated as a technical verdict.
- Next gate: build Loader v4 from the one-line `set -f` removal, run the required focused/active/full/exact-head checks, then one RAM-only v4 attempt. Never retry v3.
