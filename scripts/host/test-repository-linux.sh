#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
tier=${1:-quick}
case $tier in
	quick|rootfs) ;;
	*) fail 'usage: test-repository-linux.sh [quick|rootfs]' ;;
esac

for command in bash gcc git head nm python3 sh strings; do
	command -v "$command" >/dev/null ||
		fail "missing repository-test command: $command"
done

test_tmp=$(mktemp -d)
trap 'rm -rf -- "$test_tmp"' EXIT HUP INT TERM
shell_list=$test_tmp/tracked-shells
git -C "$repo" ls-files -z '*.sh' >"$shell_list"
[[ -s $shell_list ]] || fail 'git returned no tracked shell scripts'
while IFS= read -r -d '' script; do
	case $(head -n 1 "$repo/$script") in
		*bash*) bash -n "$repo/$script" ;;
		*) sh -n "$repo/$script" ;;
	esac
done <"$shell_list"

python3 - "$repo" <<'PY'
from pathlib import Path
import subprocess
import sys

repo = Path(sys.argv[1])
tracked = subprocess.run(
    ["git", "-C", str(repo), "ls-files", "-z", "*.py"],
    check=True,
    stdout=subprocess.PIPE,
).stdout
for raw in tracked.split(b"\0"):
    if not raw:
        continue
    path = repo / raw.decode()
    compile(path.read_bytes(), str(path), "exec")
PY

python3 - "$repo" <<'PY'
from pathlib import Path
import re
import sys

repo = Path(sys.argv[1])
documents = [
    repo / "README.md",
    repo / "ROADMAP.md",
    *sorted((repo / "docs").glob("*.md")),
]
link = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
broken = []
for document in documents:
    fenced = False
    for number, line in enumerate(document.read_text().splitlines(), 1):
        if line.lstrip().startswith(("```", "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        for match in link.finditer(line):
            target = match.group(1).strip()
            if target.startswith("<") and target.endswith(">"):
                target = target[1:-1]
            target = target.split("#", 1)[0].split("?", 1)[0]
            if (
                not target
                or "://" in target
                or target.startswith(("mailto:", "#"))
            ):
                continue
            candidate = (document.parent / target).resolve()
            try:
                candidate.relative_to(repo)
            except ValueError:
                broken.append((document, number, match.group(1)))
                continue
            if not candidate.exists():
                broken.append((document, number, match.group(1)))

if broken:
    for document, number, target in broken:
        print(
            f"{document.relative_to(repo)}:{number}: "
            f"missing local link target {target}",
            file=sys.stderr,
        )
    raise SystemExit(1)
print(
    f"PASS {len(documents)} source Markdown files have valid local targets"
)
PY

if git -C "$repo" grep -nE \
	'BEGIN (RSA|OPENSSH|EC) PRIVATE KEY|OPENROUTER_API_KEY[[:space:]]*=[[:space:]]*['"'"'"]?[A-Za-z0-9_-]{20}' \
	-- \
	':!scripts/host/test-repository-linux.sh' \
	':!scripts/host/Test-Repository.ps1'
then
	fail 'repository contains a private-key header or literal OpenRouter key'
fi

tests=(
	scripts/host/test-recovery-linux.sh
	scripts/host/test-recovery-control-reference.py
	scripts/host/test-recovery-control-native.py
	scripts/host/test-reboot-fallback-to-fastboot.sh
	scripts/host/test-network-root-acm.py
	scripts/host/test-persistent-root-acm.py
	scripts/host/test-persistent-root-entry-acm.py
	scripts/host/test-network-root-gpucc-atomic-confirmation.sh
	scripts/host/test-network-root-host.sh
	scripts/host/test-capture-vendor-kernel-log.sh
	scripts/host/test-sync-network-root-time.sh
	scripts/host/test-rog5-remote-tunnel-service.sh
)

for test_path in "${tests[@]}"; do
	test_file=$repo/$test_path
	[[ -f $test_file && ! -L $test_file ]] ||
		fail "missing core offline test: $test_path"
	case $test_file in
		*.py) python3 "$test_file" ;;
		*) [[ -x $test_file ]] || fail "offline test is not executable: $test_path"
			"$test_file"
			;;
	esac
done

if [[ $tier == rootfs ]]; then
	rootfs_test=$repo/scripts/host/test-linux-rootfs-tools.sh
	[[ -f $rootfs_test && ! -L $rootfs_test && -x $rootfs_test ]] ||
		fail 'missing executable rootfs offline suite'
	"$rootfs_test"
fi

echo "PASS repository Linux $tier tier"
