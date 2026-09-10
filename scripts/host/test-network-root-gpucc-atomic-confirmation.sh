#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname "$0")/../.." && pwd)
verifier=$repo/scripts/host/verify-network-root-gpucc-atomic-confirmation.py
acm=$repo/scripts/host/network-root-acm.py
tests=$repo/scripts/host/test-network-root-acm.py

[ -x "$verifier" ]
python3 "$verifier" "$acm" "$tests" >/dev/null

stage=$(mktemp -d)
trap 'rm -rf "$stage"' EXIT INT TERM

reject_mutation() {
	label=$1
	expression=$2
	cp "$acm" "$stage/network-root-acm.py"
	sed -i "$expression" "$stage/network-root-acm.py"
	if python3 "$verifier" "$stage/network-root-acm.py" "$tests" \
		>/dev/null 2>&1
	then
		echo "FAIL atomic confirmation verifier accepted: $label" >&2
		exit 1
	fi
}

reject_mutation reversed-sequence \
	's/("load-gpucc-confirmation", "execute")/("execute", "load-gpucc-confirmation")/'
reject_mutation duplicated-execute \
	's/("load-gpucc-confirmation", "execute")/("load-gpucc-confirmation", "execute", "execute")/'
reject_mutation traced-load \
	's/("load-gpucc-confirmation", "execute")/("load-gpucc-diagnostic", "execute")/'
reject_mutation operator-delay \
	'/def run_fixed_sequence/a\    time.sleep(5)'
reject_mutation optional-kexec-guard \
	's/if needs_kexec and os.environ.get/if False and os.environ.get/'
reject_mutation retryable-execute \
	's/        if action == "execute":/        if False:/'

cp "$tests" "$stage/test-network-root-acm.py"
sed -i \
	'/def test_atomic_confirmation_never_executes_after_load_failure/,/run.assert_called_once_with/d' \
	"$stage/test-network-root-acm.py"
if python3 "$verifier" "$acm" "$stage/test-network-root-acm.py" \
	>/dev/null 2>&1
then
	echo 'FAIL atomic confirmation verifier accepted missing failure-order test' >&2
	exit 1
fi

echo 'PASS atomic confirmation verifier rejects ordering, replay, delay, guard, and test regressions'
