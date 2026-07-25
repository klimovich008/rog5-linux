#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-gpucc-confirmation-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256 EXPECTED_MANIFEST_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing SHA-256 manifest}
expected_manifest=${5:?missing expected manifest SHA-256}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
v15_verifier=$repo/scripts/device/verify-network-root-gpucc-runtime-pm-candidate-bundle.sh
confirmation_verifier=$repo/scripts/device/verify-gpucc-trace-free-confirmation.sh
confirmation_test=$repo/scripts/device/test-gpucc-trace-free-confirmation.sh
probe_test=$repo/scripts/device/test-probe-mainline-coldplug-module.sh
acm_test=$repo/scripts/host/test-network-root-acm.py
probe=$repo/scripts/device/probe-mainline-coldplug-module.sh
acm=$repo/scripts/host/network-root-acm.py
gpucc_patch=$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch
accepted_manifest=a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc

[ "$expected_manifest" = "$accepted_manifest" ]
"$v15_verifier" "$artifact_dir" "$mkbootimg_dir" "$avbtool" \
	"$expected_sums" "$expected_manifest" >/dev/null
"$confirmation_verifier" "$probe" "$acm" "$gpucc_patch" >/dev/null
"$confirmation_test" >/dev/null
"$probe_test" >/dev/null
PYTHONDONTWRITEBYTECODE=1 python3 "$acm_test" >/dev/null 2>&1

[ "$(sha256sum "$probe" | cut -d ' ' -f 1)" = \
	7fbc01a2308ea258c51e2f88c01346bd8397dcb545f8f7cab7e13b6f23fba33e ]
[ "$(sha256sum "$acm" | cut -d ' ' -f 1)" = \
	cd5cfabca51a4709e87e268ac93d3f37eb61e5c3100d1406bfdf46941834ec33 ]
[ "$(sha256sum "$gpucc_patch" | cut -d ' ' -f 1)" = \
	50ec8d394583951ab00e65c38686775031d0abadc6a3faf1730edda13eb7be94 ]

for contract in \
	'probe_timeout=${ROG5_PROBE_TIMEOUT:-75}' \
	'settle_seconds=${ROG5_PROBE_SETTLE:-30}' \
	'gpucc_trace_mode=${ROG5_GPUCC_TRACE_MODE:-diagnostic}' \
	'trace_expected_count=0' \
	'trace_expected_state=N' \
	'trace_prefix=$parameter=' \
	'insmod "$module_file" probe_trace=1' \
	'probe_safe=1'
do
	grep -Fq "$contract" "$probe"
done

python3 - "$acm" <<'PY'
from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

source = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("rog5_network_root_acm", source)
assert spec is not None and spec.loader is not None
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
confirmation = module.ACTIONS["load-gpucc-confirmation"][0]
diagnostic = module.ACTIONS["load-gpucc-diagnostic"][0]
assert confirmation == (
    "ROG5_SYSTEMD_DIAGNOSTIC=1 ROG5_RECOVERY_TIMEOUT=900 "
    "/usr/local/sbin/rog5-load-mainline-recovery"
)
assert confirmation != diagnostic
for trace in (
    "ROG5_QCOM_CC_PROBE_TRACE",
    "ROG5_CCF_REGISTER_TRACE",
    "ROG5_RCG2_PARENT_TRACE",
):
    assert trace not in confirmation
    assert trace in diagnostic
PY

echo 'PASS exact v16 trace-free confirmation reuses the v15 bundle, rejects all core traces, and retains bounded rollback'
