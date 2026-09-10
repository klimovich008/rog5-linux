#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/device/verify-gpucc-trace-free-confirmation.sh
probe=$repo/scripts/device/probe-mainline-coldplug-module.sh
acm=$repo/scripts/host/network-root-acm.py
gpucc_patch=$repo/patches/linux-7.1.4/0005-gpucc-sm8350-add-attended-probe-trace.patch
stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

[ -x "$verifier" ]
"$verifier" "$probe" "$acm" "$gpucc_patch" >/dev/null

reject_mutation() {
	label=$1
	mutant_probe=$2
	mutant_acm=$3
	mutant_patch=$4
	if "$verifier" "$mutant_probe" "$mutant_acm" "$mutant_patch" \
		>"$stage/$label.output" 2>&1
	then
		echo "FAIL confirmation verifier accepted $label mutation" >&2
		exit 1
	fi
}

make_mutation() {
	label=$1
	mutation=$2
	mutant_probe=$stage/$label.probe
	mutant_acm=$stage/$label.acm
	mutant_patch=$stage/$label.patch
	cp "$probe" "$mutant_probe"
	cp "$acm" "$mutant_acm"
	cp "$gpucc_patch" "$mutant_patch"
	python3 - "$mutant_probe" "$mutant_acm" "$mutant_patch" \
		"$mutation" <<'PY'
from pathlib import Path
import sys

probe = Path(sys.argv[1])
acm = Path(sys.argv[2])
patch = Path(sys.argv[3])
mutation = sys.argv[4]

probe_text = probe.read_text()
acm_text = acm.read_text()
patch_text = patch.read_text()

if mutation == "confirmation-count-one":
    probe_text = probe_text.replace(
        "trace_expected_count=0", "trace_expected_count=1", 1
    )
elif mutation == "confirmation-state-enabled":
    probe_text = probe_text.replace(
        "trace_expected_state=N", "trace_expected_state=Y", 1
    )
elif mutation == "default-confirmation":
    probe_text = probe_text.replace(
        "${ROG5_GPUCC_TRACE_MODE:-diagnostic}",
        "${ROG5_GPUCC_TRACE_MODE:-confirmation}",
        1,
    )
elif mutation == "omit-rcg2":
    probe_text = probe_text.replace(
        "\t\trog5_rcg2_parent_trace\n", "", 1
    )
elif mutation == "allow-disabled-argument":
    probe_text = probe_text.replace(
        "trace_prefix=$parameter=", "trace_prefix=$boot_argument", 1
    )
elif mutation == "disable-outer-trace":
    probe_text = probe_text.replace(
        'insmod "$module_file" probe_trace=1',
        'insmod "$module_file" probe_trace=0',
        1,
    )
elif mutation == "traced-load-action":
    marker = '"load-gpucc-confirmation": ('
    start = acm_text.index(marker)
    command = acm_text.index(
        '"ROG5_SYSTEMD_DIAGNOSTIC=1 ', start
    )
    acm_text = (
        acm_text[:command]
        + '"ROG5_CCF_REGISTER_TRACE=1 '
        + acm_text[command + 1 :]
    )
elif mutation == "outer-delay":
    marker = '+\tif (probe_trace)\n+\t\tdev_notice'
    patch_text = patch_text.replace(
        marker,
        '+\tmsleep(100);\n' + marker,
        1,
    )
else:
    raise SystemExit(f"unknown mutation: {mutation}")

probe.write_text(probe_text)
acm.write_text(acm_text)
patch.write_text(patch_text)
PY
	reject_mutation "$label" "$mutant_probe" "$mutant_acm" "$mutant_patch"
}

make_mutation confirmation-count-one confirmation-count-one
make_mutation confirmation-state-enabled confirmation-state-enabled
make_mutation default-confirmation default-confirmation
make_mutation omit-rcg2 omit-rcg2
make_mutation allow-disabled-argument allow-disabled-argument
make_mutation disable-outer-trace disable-outer-trace
make_mutation traced-load-action traced-load-action
make_mutation outer-delay outer-delay

echo 'PASS trace-free confirmation verifier rejects enabled/missing traces, unsafe defaults, and outer delay mutations'
