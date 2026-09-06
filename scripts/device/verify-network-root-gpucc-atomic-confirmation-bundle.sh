#!/bin/sh
set -eu

artifact_dir=${1:?usage: verify-network-root-gpucc-atomic-confirmation-bundle.sh ARTIFACT_DIR MKBOOTIMG_DIR AVBTOOL EXPECTED_SHA256 EXPECTED_MANIFEST_SHA256}
mkbootimg_dir=${2:?missing mkbootimg directory}
avbtool=${3:?missing avbtool}
expected_sums=${4:?missing SHA-256 manifest}
expected_manifest=${5:?missing expected manifest SHA-256}
repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
v15_verifier=$repo/scripts/device/verify-network-root-gpucc-runtime-pm-candidate-bundle.sh
confirmation_verifier=$repo/scripts/device/verify-gpucc-trace-free-confirmation.sh
confirmation_test=$repo/scripts/device/test-gpucc-trace-free-confirmation.sh
baseline=$repo/scripts/device/check-network-root-gpucc-confirmation-baseline.sh
baseline_test=$repo/scripts/device/test-network-root-gpucc-confirmation-baseline.sh
probe=$repo/scripts/device/probe-mainline-coldplug-module.sh
probe_test=$repo/scripts/device/test-probe-mainline-coldplug-module.sh
acm=$repo/scripts/host/network-root-acm.py
acm_test=$repo/scripts/host/test-network-root-acm.py
recovery=$repo/scripts/host/recovery-linux.sh
atomic_verifier=$repo/scripts/host/verify-network-root-gpucc-atomic-confirmation.py
atomic_test=$repo/scripts/host/test-network-root-gpucc-atomic-confirmation.sh
gpucc_patch=$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch
accepted_manifest=a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc

[ "$expected_manifest" = "$accepted_manifest" ]
"$v15_verifier" "$artifact_dir" "$mkbootimg_dir" "$avbtool" \
	"$expected_sums" "$expected_manifest" >/dev/null
"$confirmation_verifier" "$probe" "$acm" "$gpucc_patch" >/dev/null
"$confirmation_test" >/dev/null
"$baseline_test" >/dev/null
"$probe_test" >/dev/null
python3 "$atomic_verifier" "$acm" "$acm_test" >/dev/null
"$atomic_test" >/dev/null
PYTHONDONTWRITEBYTECODE=1 python3 "$acm_test" >/dev/null 2>&1

check_hash() {
	file=$1
	expected=$2
	[ "$(sha256sum "$file" | cut -d ' ' -f1)" = "$expected" ]
}

check_hash "$acm" \
	105bc5f7ca91693b0ed42c70686162c93fe84a56c6a9643189e43a49c2759176
check_hash "$acm_test" \
	08aee76f4505d9e27dc435eac25d080584c175116f0ae3f6d93f36e520ef8e6d
check_hash "$recovery" \
	2c4e95537bf796a942f9e73e2a5eb3db71abf8e5bf9aae1f0617ecb08e9290ca
check_hash "$atomic_verifier" \
	435c84b7ed990aaa6f27b959977cebbc0fc978dad928063af5ed6a1644964bce
check_hash "$atomic_test" \
	23311b66521a18fbb1645dfd7cb9ae91b7fdefa2df486c96882a94db44844095
check_hash "$baseline" \
	cbbbce7149ea35c67cfefac6b312c86a88ecf81dc34b0f77d124d6d0007267a6
check_hash "$baseline_test" \
	b745eabbfdd7a19d49f178b9100b6b12bc47e73f07eef26da6f965bd6c731a5b
check_hash "$probe" \
	7fbc01a2308ea258c51e2f88c01346bd8397dcb545f8f7cab7e13b6f23fba33e
check_hash "$confirmation_verifier" \
	d2220b3f53f6f2d7c9c90e5d6f8f31dc1c5b8017cfd44b12cc6e52b6cf7a53ee
check_hash "$confirmation_test" \
	0f865b6ab581d89af5defb54f4a7ff3755a5d7f03af58a59529e7a22403fcd9c
check_hash "$gpucc_patch" \
	50ec8d394583951ab00e65c38686775031d0abadc6a3faf1730edda13eb7be94

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
assert module.SEQUENCES == {
    "confirm-gpucc": ("load-gpucc-confirmation", "execute"),
}
assert module.ACTIONS["load-gpucc-confirmation"][0] == (
    "ROG5_SYSTEMD_DIAGNOSTIC=1 ROG5_RECOVERY_TIMEOUT=900 "
    "/usr/local/sbin/rog5-load-mainline-recovery"
)
assert module.ACTIONS["execute"][0] == "kexec -e"
PY

echo 'PASS exact v17 atomic confirmation reuses v15 artifacts and v16 target gates while eliminating the operator gap'
