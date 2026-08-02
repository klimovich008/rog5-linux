#!/usr/bin/env bash
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
fetcher=$repo/scripts/host/fetch-android-boot-tools.sh
workflow=$repo/.github/workflows/offline-smoke.yml

[[ -f $fetcher && ! -L $fetcher && -x $fetcher ]] ||
	fail 'missing executable Android boot-tool bootstrap'
[[ -f $workflow && ! -L $workflow ]] ||
	fail 'missing offline-smoke workflow'
bash -n "$fetcher"

for token in \
	https://android.googlesource.com/platform/system/tools/mkbootimg \
	https://android.googlesource.com/platform/external/avb \
	d2bb0af5ba6d3198a3e99529c97eda1be0b5a093 \
	ec2958179691a434df917cd1b6f196edaa80e31d \
	a3f1a508796b5af54216397b05637f1f5e692a3d \
	739c61b04a9dbd95cafa5196533e3a472c31f2d9 \
	a4a2d67bcfe479adb3d54d6127abb11afbc76701 \
	9c437c76d112662810ea1c14be122bbe8592fec5 \
	d99136f30bda966e8820c8ae53a82c659ca36e6d1aaf49a4cd63ae4795a6845a \
	7012fe91c4032446f23f3bd6f86fe1bc274517eb4e7aef923ed8396a5b619aef \
	6418646bb5bf3c57c3c702bfd1e157917e59f9ce25c3c81bcce79d85655e56ff \
	'--proto '\''=https'\''' \
	'git hash-object' \
	'line_ending_transform=lf-to-crlf' \
	'state=exact-historical-bytes-recovered' \
	'authority=none' \
	'mv -T -- "$publish" "$output_root"'; do
	grep -Fq -- "$token" "$fetcher" ||
		fail "Android boot-tool bootstrap omits contract token: $token"
done
grep -Fq 'run: scripts/host/fetch-android-boot-tools.sh' "$workflow" ||
	fail 'clean recovery CI does not bootstrap the exact Android boot tools'
if grep -Eq \
	'\b(fastboot|adb|sudo|pkexec)\b|(^|[;&|[:space:]])(ssh|scp)([[:space:]]|$)|/dev/(sd|nvme|ufs)' \
	"$fetcher"; then
	fail 'Android boot-tool bootstrap contains phone, privilege, or storage transport'
fi

echo 'PASS Android boot-tool bootstrap is authoritative, commit/blob pinned, and exact-byte gated'
