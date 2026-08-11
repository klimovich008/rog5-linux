#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
wrapper=$repo/scripts/host/build-headless-ssh-deployment-candidate.sh
diagnostic_wrapper=$repo/scripts/host/build-early-target-diagnostic-deployment-candidate.sh
builder=$repo/scripts/host/build-corrected-headless-candidate-offline.sh
builder_impl=$repo/scripts/host/build-corrected-headless-candidate-offline-impl.sh
stager=$repo/scripts/host/stage-recovery-deployment-signing-inputs.py
legacy_stager=$repo/scripts/host/stage-headless-ssh-deployment-signing-inputs.py
diagnostic_preparer=$repo/scripts/host/prepare-early-target-diagnostic-deployment-candidate.py
full_path_test=$repo/scripts/host/test-full-diagnostic-deployment-path.sh
runbook=$repo/docs/minimal-headless-live-cycle.md
test_root=$(mktemp -d)
trap 'rm -rf -- "$test_root"' EXIT HUP INT TERM

for script in "$wrapper" "$diagnostic_wrapper" "$builder"; do
	[[ -f $script && ! -L $script && -x $script ]] ||
		fail "deployment-candidate builder is missing: ${script#"$repo"/}"
	/usr/bin/python3 -m py_compile "$script"
done
[[ -f $builder_impl && ! -L $builder_impl && -x $builder_impl ]] ||
	fail 'deployment-candidate Bash implementation is missing or unsafe'
bash -n "$builder_impl"
[[ -f $stager && ! -L $stager && -x $stager ]] ||
	fail 'deployment signing-input stager is missing or unsafe'
grep -Fxq '#!/usr/bin/env -S -i /usr/bin/python3 -I -S' "$stager" ||
	fail 'deployment signing-input stager does not isolate Python startup'
[[ -f $legacy_stager && ! -L $legacy_stager && -x $legacy_stager ]] ||
	fail 'deployment signing-input compatibility entry point is missing or unsafe'
grep -Fq 'stage-recovery-deployment-signing-inputs.py' "$legacy_stager" ||
	fail 'deployment signing-input compatibility entry point is not neutral'
grep -Fxq '#!/usr/bin/env -S -i /usr/bin/python3 -I -S' "$legacy_stager" ||
	fail 'deployment signing-input compatibility entry point is not isolated'
grep -Fq 'os.execve(' "$legacy_stager" ||
	fail 'deployment signing-input compatibility entry point does not use exact exec'
"$legacy_stager" --help >/dev/null ||
	fail 'deployment signing-input compatibility entry point does not execute'
mkdir -m 0700 "$test_root/legacy-hostile-python"
printf '%s\n' \
	'from pathlib import Path' \
	"Path('$test_root/legacy-python.log').write_text('executed\\n')" \
	'raise SystemExit(96)' >"$test_root/legacy-hostile-python/sitecustomize.py"
PYTHONPATH="$test_root/legacy-hostile-python" \
	PYTHONINSPECT=1 \
	"$legacy_stager" --help >/dev/null ||
	fail 'isolated deployment signing-input compatibility entry point failed'
[[ ! -e $test_root/legacy-python.log ]] ||
	fail 'compatibility entry point executed caller Python startup code'
[[ -f $diagnostic_preparer && ! -L $diagnostic_preparer &&
	-x $diagnostic_preparer ]] ||
	fail 'diagnostic deployment-candidate preparer is missing or unsafe'
[[ -f $full_path_test && ! -L $full_path_test && -x $full_path_test ]] ||
	fail 'full disposable diagnostic path test is missing or unsafe'
bash -n "$full_path_test"
grep -Fq -- '--bundle headless-ssh-network-root-v3-r2' "$runbook" ||
	fail 'deployment runbook does not explicitly select the fresh successor bundle'
grep -Fq -- 'prepare-early-target-diagnostic-deployment-candidate.py' \
	"$runbook" ||
	fail 'deployment runbook omits exact diagnostic candidate preparation'
grep -Fq -- 'build-early-target-diagnostic-deployment-candidate.sh' \
	"$runbook" ||
	fail 'deployment runbook omits the guarded diagnostic signing wrapper'

if "$wrapper" \
	--candidate-record "$test_root/candidate" \
	--signing-key "$test_root/key" \
	"$test_root/output" \
	>"$test_root/wrapper.out" 2>"$test_root/wrapper.err"; then
	fail 'deployment wrapper ran without explicit guards'
fi
grep -Fq 'set --authorize-recovery-deployment-build' \
	"$test_root/wrapper.err" ||
	fail 'deployment wrapper did not enforce its first guard'

if ALLOW_RECOVERY_DEPLOYMENT_BUILD=1 \
	ALLOW_HEADLESS_SSH_DEPLOYMENT_BUILD=1 \
	ALLOW_PHONE_CREDENTIAL_USE=1 \
	ROG5_DEPLOYMENT_CANDIDATE_RECORD="$test_root/environment-candidate" \
	ROG5_DEPLOYMENT_SIGNING_KEY="$test_root/environment-key" \
	"$wrapper" \
	--candidate-record "$test_root/candidate" \
	--signing-key "$test_root/key" \
	"$test_root/environment-only-authorization" \
	>"$test_root/explicit-denial.out" \
	2>"$test_root/explicit-denial.err"; then
	fail 'deployment wrapper accepted environment-only authorization'
fi
grep -Fq 'set --authorize-recovery-deployment-build' \
	"$test_root/explicit-denial.err" ||
	fail 'deployment wrapper did not clear environment-only authorization'

if "$diagnostic_wrapper" \
	--candidate-record "$test_root/candidate" \
	--signing-key "$test_root/key" \
	"$test_root/diagnostic-output" \
	>"$test_root/diagnostic-wrapper.out" \
	2>"$test_root/diagnostic-wrapper.err"; then
	fail 'diagnostic deployment wrapper ran without explicit guards'
fi
grep -Fq 'set --authorize-recovery-deployment-build' \
	"$test_root/diagnostic-wrapper.err" ||
	fail 'diagnostic deployment wrapper did not enforce its first guard'

if "$full_path_test" "$repo/build/rejected-full-diagnostic" \
	>"$test_root/full-path.out" 2>"$test_root/full-path.err"; then
	fail 'full disposable diagnostic path ran without its expensive-test guard'
fi
grep -Fq 'set ROG5_RUN_FULL_DISPOSABLE_DIAGNOSTIC=1' \
	"$test_root/full-path.err" ||
	fail 'full disposable diagnostic path did not enforce its first guard'

ROG5_DEPLOYMENT_BUILD=1 \
	ROG5_DEPLOYMENT_CANDIDATE_RECORD="$test_root/candidate" \
	ROG5_DEPLOYMENT_SIGNING_KEY="$test_root/key" \
	/usr/bin/python3 -I -S - "$builder" \
		"$test_root/rejected-deployment-inputs" <<'PY'
from __future__ import annotations

import argparse
import importlib.machinery
import importlib.util
from pathlib import Path
import sys

launcher = Path(sys.argv[1])
output_root = sys.argv[2]
loader = importlib.machinery.SourceFileLoader("rog5_offline_launcher_test", str(launcher))
specification = importlib.util.spec_from_loader(loader.name, loader)
if specification is None:
    raise SystemExit("cannot load offline builder launcher")
module = importlib.util.module_from_spec(specification)
loader.exec_module(module)

module.parse_arguments = lambda: argparse.Namespace(
    output_root=output_root,
    candidate="headless-network-root-v1",
    expected_dtb=module.DEFAULT_DTB,
    expected_target="headless-network-root",
    wrapper_jobs="8",
)
captured: dict[str, object] = {}


class ExecveCaptured(Exception):
    pass


def capture_execve(
    executable: str, arguments: list[str], environment: dict[str, str]
) -> None:
    captured["executable"] = executable
    captured["arguments"] = arguments
    captured["environment"] = environment
    raise ExecveCaptured


module.os.execve = capture_execve
try:
    module.main()
except ExecveCaptured:
    pass
else:
    raise SystemExit("offline launcher did not execute its fixed implementation")

implementation = launcher.with_name(
    "build-corrected-headless-candidate-offline-impl.sh"
)
expected_arguments = [
    "/usr/bin/bash",
    "--noprofile",
    "--norc",
    str(implementation),
    output_root,
]
expected_environment = {
    "PATH": "/usr/bin:/bin",
    "LC_ALL": "C",
    "ROG5_DEPLOYMENT_BUILD": "0",
    "ROG5_OFFLINE_CANDIDATE": "headless-network-root-v1",
    "ROG5_OFFLINE_EXPECTED_DTB": module.DEFAULT_DTB,
    "ROG5_OFFLINE_EXPECTED_TARGET": "headless-network-root",
    "ROG5_OFFLINE_WRAPPER_JOBS": "8",
}
if captured != {
    "executable": "/usr/bin/bash",
    "arguments": expected_arguments,
    "environment": expected_environment,
}:
    raise SystemExit("offline launcher exec contract or scrubbed environment changed")
PY

if "$builder" \
	--signing-key "$test_root/key" \
	"$repo/build/rejected-deployment-cli" \
	>"$test_root/diagnostic-builder.out" \
	2>"$test_root/diagnostic-builder.err"; then
	fail 'credential-free builder accepted a signing-key option'
fi
grep -Fq 'unrecognized arguments: --signing-key' \
	"$test_root/diagnostic-builder.err" ||
	fail 'credential-free builder did not reject the signing-key option'

integration_root=$(realpath -e "$test_root")/integration
integration_repo=$integration_root/repository
integration_remote=$integration_root/remote.git
integration_private=$integration_root/private
integration_bin=$integration_root/bin
integration_python=$integration_root/python
integration_bash_env=$integration_root/bash-env.sh
integration_openssl_conf=$integration_root/openssl.cnf
integration_helper_log=$integration_root/helper.log
mkdir -m 0700 -p \
	"$integration_root" "$integration_private" "$integration_bin" \
	"$integration_python"
for helper in bash chmod cmp cut dirname env find git grep id mkdir mktemp \
	openssl podman python3 realpath rm sed sha256sum stat tail; do
	printf '%s\n' \
		'#!/bin/sh' \
		"printf '%s\\n' '$helper' >> '$integration_helper_log'" \
		'echo "FAIL caller PATH helper reached credentialed build" >&2' \
		'exit 97' \
		>"$integration_bin/$helper"
	chmod 0755 "$integration_bin/$helper"
done
printf '%s\n' \
	"printf '%s\\n' BASH_ENV >> '$integration_helper_log'" \
	'exit 96' >"$integration_bash_env"
printf '%s\n' \
	'from pathlib import Path' \
	"Path('$integration_helper_log').write_text('PYTHONPATH\\n')" \
	'raise SystemExit(96)' >"$integration_python/sitecustomize.py"
printf '%s\n' \
	'openssl_conf = init' \
	'[init]' \
	'providers = providers' \
	'[providers]' \
	'hostile = hostile' \
	'[hostile]' \
	'module = /definitely/missing/rog5-hostile-provider.so' \
	'activate = 1' >"$integration_openssl_conf"
git init --bare -q "$integration_remote"
git clone -q "$integration_remote" "$integration_repo"
mkdir -p \
	"$integration_repo/scripts/host/qualified-tool-shims" \
	"$integration_repo/scripts/host/qualified-cpio-path" \
	"$integration_repo/configs/recovery-candidates"
for source in \
	scripts/host/build-early-target-diagnostic-deployment-candidate.sh \
	scripts/host/build-corrected-headless-candidate-offline.sh \
	scripts/host/build-corrected-headless-candidate-offline-impl.sh \
	scripts/host/stage-recovery-deployment-signing-inputs.py \
	scripts/host/prepare-recovery-candidate.py \
	scripts/host/prepare-recovery-runtime-bundle.py; do
	cp -p -- "$repo/$source" "$integration_repo/$source"
done
cp -p -- \
	"$repo/configs/recovery-candidates/headless-netroot-early-diag-v2.json" \
	"$integration_repo/configs/recovery-candidates/"
printf 'build/\n__pycache__/\n' >"$integration_repo/.gitignore"
for stub in \
	scripts/host/verify-steam-deck-builder.sh \
	scripts/host/run-private-arm64-binfmt.sh \
	scripts/host/qualified-tool-shims/cpio \
	scripts/host/qualified-cpio-path/cpio; do
	printf '#!/bin/sh\nexit 99\n' >"$integration_repo/$stub"
	chmod 0755 "$integration_repo/$stub"
done
git -C "$integration_repo" config user.name 'ROG5 Test'
git -C "$integration_repo" config user.email 'rog5-test@example.invalid'
git -C "$integration_repo" add .
git -C "$integration_repo" commit -q -m 'diagnostic input preflight fixture'
git -C "$integration_repo" push -q -u origin HEAD

/usr/bin/python3 -I -S - \
	"$integration_repo/scripts/host/build-early-target-diagnostic-deployment-candidate.sh" <<'PY'
from __future__ import annotations

import errno
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import sys

launcher = Path(sys.argv[1])
loader = importlib.machinery.SourceFileLoader("rog5_launcher_test", str(launcher))
specification = importlib.util.spec_from_loader(loader.name, loader)
if specification is None:
    raise SystemExit("cannot load deployment launcher")
module = importlib.util.module_from_spec(specification)
loader.exec_module(module)
repository, reviewed_worktree, checkpoint, descriptor = (
    module.verified_implementation()
)
implementation = launcher.with_name(
    "build-corrected-headless-candidate-offline-impl.sh"
)
reviewed_implementation = reviewed_worktree / implementation.relative_to(repository)
mode = implementation.stat().st_mode & 0o777
os.lseek(descriptor, 0, os.SEEK_SET)
snapshot = os.read(descriptor, 1024 * 1024)
try:
    if reviewed_worktree == repository:
        raise SystemExit("reviewed implementation reused the mutable checkout")
    if module.git_output(reviewed_worktree, "rev-parse", "HEAD") != checkpoint:
        raise SystemExit("reviewed worktree HEAD differs from the checkpoint")
    if module.git_output(
        reviewed_worktree,
        "status",
        "--porcelain",
        "--untracked-files=all",
    ):
        raise SystemExit("reviewed worktree is not clean")
    if reviewed_implementation.read_bytes() != snapshot:
        raise SystemExit("reviewed worktree implementation differs from sealed bytes")
    implementation.write_bytes(b"#!/usr/bin/bash\nexit 97\n")
    os.lseek(descriptor, 0, os.SEEK_SET)
    if os.read(descriptor, 1024 * 1024) != snapshot:
        raise SystemExit("sealed implementation followed pathname replacement")
    if reviewed_implementation.read_bytes() != snapshot:
        raise SystemExit("reviewed worktree followed mutable checkout replacement")
    try:
        os.pwrite(descriptor, b"X", 0)
    except OSError as error:
        if error.errno not in (errno.EPERM, errno.EBUSY):
            raise
    else:
        raise SystemExit("sealed implementation accepted mutation")
finally:
    implementation.write_bytes(snapshot)
    implementation.chmod(mode)
    os.close(descriptor)
    subprocess.run(
        [
            "/usr/bin/git",
            "-C",
            str(repository),
            "worktree",
            "remove",
            "--force",
            str(reviewed_worktree),
        ],
        check=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        env=module.GIT_ENV,
    )
PY
[[ -z $(git -C "$integration_repo" status --porcelain --untracked-files=all) ]] ||
	fail 'sealed implementation replacement test did not restore the repository'

# Advance the remote without refreshing this clone's origin ref. The launcher
# must fetch the exact branch itself; trusting the stale local ref would admit
# the obsolete local HEAD and cross the sealed-implementation boundary.
integration_publisher=$integration_root/publisher
git clone -q "$integration_remote" "$integration_publisher"
git -C "$integration_publisher" config user.name 'ROG5 Test Publisher'
git -C "$integration_publisher" config user.email 'rog5-publisher@example.invalid'
printf 'remote advanced\n' >"$integration_publisher/remote-checkpoint"
git -C "$integration_publisher" add remote-checkpoint
git -C "$integration_publisher" commit -q -m 'advance remote checkpoint'
git -C "$integration_publisher" push -q origin HEAD

/usr/bin/python3 -I -S - \
	"$integration_repo/scripts/host/build-early-target-diagnostic-deployment-candidate.sh" <<'PY'
from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import sys

launcher = Path(sys.argv[1])
loader = importlib.machinery.SourceFileLoader("rog5_stale_ref_test", str(launcher))
specification = importlib.util.spec_from_loader(loader.name, loader)
if specification is None:
    raise SystemExit("cannot load deployment launcher")
module = importlib.util.module_from_spec(specification)
loader.exec_module(module)
try:
    module.verified_implementation()
except SystemExit as error:
    if str(error) != "FAIL deployment-signing checkpoint differs from origin":
        raise
else:
    raise SystemExit("stale origin ref admitted an obsolete launcher checkpoint")
PY
git -C "$integration_repo" pull -q --ff-only

integration_key=$integration_private/recovery-signing-key.pem
integration_candidate=$integration_private/diagnostic-candidate.json
openssl genpkey -algorithm ED25519 -out "$integration_key" 2>/dev/null
chmod 0600 "$integration_key"
cp -- \
	"$repo/configs/recovery-candidates/headless-netroot-early-diag-v2.json" \
	"$integration_candidate"
chmod 0444 "$integration_candidate"
key_before=$(sha256sum "$integration_key" | cut -d ' ' -f 1)
env -i PATH="$integration_bin:$PATH" HOME="$HOME" \
	BASH_ENV="$integration_bash_env" \
	SHELLOPTS=xtrace \
	PYTHONPATH="$integration_python" \
	PYTHONINSPECT=1 \
	OPENSSL_CONF="$integration_openssl_conf" \
	ROG5_ATTACK_LOG="$integration_helper_log" \
	'BASH_FUNC_id%%=() { printf function >>"$ROG5_ATTACK_LOG"; }' \
	deployment_candidate_record=poison-candidate \
	deployment_private_key=poison-key \
	secret_root=poison-root \
	private_key=poison-private-key \
	public_key=poison-public-key \
	candidate_record=poison-staged-candidate \
	"$integration_repo/scripts/host/build-early-target-diagnostic-deployment-candidate.sh" \
	--authorize-recovery-deployment-build \
	--authorize-phone-credential-use \
	--candidate-record "$integration_candidate" \
	--signing-key "$integration_key" \
	--signing-input-preflight \
	"$integration_repo/build/diagnostic-input-preflight" \
	>"$test_root/diagnostic-input-preflight.out" \
	2>"$test_root/diagnostic-input-preflight.err" || {
	sed -n '1,40p' "$test_root/diagnostic-input-preflight.err" >&2
	fail 'disposable diagnostic wrapper-to-stager input preflight failed'
}
grep -Fxq \
	'PASS guarded deployment signing inputs staged, validated, scrubbed from the child environment, and destroyed without signing' \
	"$test_root/diagnostic-input-preflight.out" ||
	fail 'diagnostic wrapper-to-stager preflight omitted its exact pass marker'
[[ $(sha256sum "$integration_key" | cut -d ' ' -f 1) == "$key_before" ]] ||
	fail 'diagnostic input preflight changed its caller-owned disposable key'
[[ ! -e $integration_repo/build/diagnostic-input-preflight ]] ||
	fail 'signing-input preflight created a build output'
[[ -z $(find "$integration_repo/build" -mindepth 1 -maxdepth 1 \
	-type d -name '.rog5-reviewed-checkpoint-*' -print -quit) ]] ||
	fail 'signing-input preflight retained a reviewed checkpoint worktree'
[[ ! -e $integration_helper_log || ! -s $integration_helper_log ]] ||
	fail 'caller PATH helper intercepted the credentialed build'

for token in \
	'#!/usr/bin/env -S -i /usr/bin/python3 -I -S' \
	'--authorize-recovery-deployment-build' \
	'--authorize-phone-credential-use' \
	'--candidate-record' \
	'--signing-key' \
	'os.execve(' \
	'os.memfd_create(' \
	'F_ADD_SEALS' \
	'f"{checkpoint}:{IMPLEMENTATION_REPOSITORY_PATH}"' \
	'checkpoint_worktree(' \
	'"ROG5_INTERNAL_CHECKPOINT_REPOSITORY_ROOT"' \
	'"ROG5_INTERNAL_REPOSITORY_COMMIT"' \
	'"ROG5_DEPLOYMENT_BUILD": "1"' \
	'headless-ssh-network-root-v3' \
	'headless-ssh-network-root'; do
	grep -Fq -- "$token" "$wrapper" ||
		fail "deployment-candidate wrapper omits token: $token"
done

for launcher in "$wrapper" "$diagnostic_wrapper"; do
	grep -Fq 'refs/heads/{branch}:refs/remotes/origin/{branch}' "$launcher" ||
		fail "deployment launcher does not refresh its exact origin branch: ${launcher#"$repo"/}"
	for token in \
		'CHECKPOINT_INPUTS = (' \
		'def stage_checkpoint_inputs(' \
		'os.O_EXCL' \
		'os.O_NOFOLLOW' \
		'hasher.hexdigest() != digest' \
		'artifacts/android-boot-tools-v1/gki/generate_gki_certificate.py' \
		'stage_inputs=not arguments.signing_input_preflight'; do
		grep -Fq -- "$token" "$launcher" ||
			fail "deployment launcher omits checkpoint-input gate: $token"
	done
done

for token in \
	'ROG5_RUN_FULL_DISPOSABLE_DIAGNOSTIC' \
	'build-early-target-diagnostic-deployment-candidate.sh' \
	'--authorize-recovery-deployment-build' \
	'--authorize-phone-credential-use' \
	'headless-diagnostic-stage75-v2-superseded-offline-v1' \
	'missing exact consumed recovery guard' \
	'consumed recovery guard changed by fixture rewrite' \
	'fixture image collides with a consumed recovery guard' \
	'fixture image is not the unique stage-75 v2 allowlist pin' \
	'54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc' \
	'833899cb067a28d57e41c5a8291c7f5099c4f7fcc11316c2976d04a7b926e7de' \
	'artifact-preflight' \
	'full disposable-key diagnostic wrapper, twin build, native verification, and artifact-preflight fixture' \
	'authority=none'; do
	grep -Fq -- "$token" "$full_path_test" ||
		fail "full disposable diagnostic path omits token: $token"
done

for token in \
	'headless-netroot-early-diag-v2' \
	'f23626d6ad0b15a660835bd8419cde40a8f8c3c79f83b6feca5cb57952f7b1ab' \
	'DEPLOYMENT.parse_package' \
	'DEPLOYMENT.write_candidate' \
	'candidate and deployment package roots differ' \
	'authority=none'; do
	grep -Fq -- "$token" "$diagnostic_preparer" ||
		fail "diagnostic candidate preparer omits token: $token"
done

for token in \
	'ALLOW_RECOVERY_DEPLOYMENT_BUILD' \
	'ALLOW_PHONE_CREDENTIAL_USE' \
	'"ROG5_DEPLOYMENT_BUILD": "1"' \
	'ROG5_DEPLOYMENT_CANDIDATE_RECORD' \
	'ROG5_DEPLOYMENT_SIGNING_KEY' \
	'headless-netroot-early-diag-v2' \
	'headless-netroot-early-diag-v2'; do
	grep -Fq -- "$token" "$diagnostic_wrapper" ||
		fail "diagnostic deployment wrapper omits token: $token"
done

for token in \
	'credentialed build is limited to one fixed deployment candidate' \
	'ROG5_DEPLOYMENT_SIGNING_INPUT_PREFLIGHT' \
	'stage-recovery-deployment-signing-inputs.py' \
	'rog5-recovery-deployment-signing-inputs-v2' \
	'--candidate-id "$candidate"' \
	'--repository "$checkpoint_repository"' \
	'--expected-repository-commit "$internal_repository_commit"' \
	'--staged-key "$private_key"' \
	'--staged-candidate "$candidate_record"' \
	'--raw-public-key "$public_key"' \
	'--candidate-record' \
	'--candidate-record-sha256' \
	'staged deployment candidate identity changed' \
	'bundle_id_a=' \
	'--trust-key "$public_key" "$bundle_id_a"' \
	'private signing-key snapshot survived candidate build' \
	'deployment credential path or authorization leaked after staging' \
	'private signing-key snapshot survived input preflight' \
	'reviewed checkpoint worktree survived input preflight' \
	'credentialed output publication refused an occupied destination' \
	'authority=none'; do
	grep -Fq -- "$token" "$builder_impl" ||
		fail "shared deployment builder omits token: $token"
done

if grep -Eq '\b(fastboot|adb|scp|systemctl|pkexec|sudo)\b|/dev/(sd|nvme|ufs)' \
	"$wrapper" "$diagnostic_wrapper" "$builder" "$builder_impl" "$stager" \
	"$legacy_stager" \
	"$diagnostic_preparer" "$full_path_test"; then
	fail 'deployment-candidate wrapper contains phone, privilege, or storage transport'
fi

echo 'PASS deployment recovery build executes guarded input staging and remains authority-free and transport-free'
