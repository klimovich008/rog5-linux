#!/bin/sh
set -eu
repo=$(CDPATH='' cd -- "$(dirname -- "$0")/../.." && pwd -P)
fragment=$repo/configs/kernel/rog5-tailscale-netfilter.fragment
builder=$repo/scripts/device/build-tailscale-netfilter-kernel.sh
settings=$(grep '^CONFIG_' "$fragment")
[ "$settings" = CONFIG_NF_CONNTRACK_MARK=y ]
[ "$(grep -c '^CONFIG_' "$fragment")" -eq 1 ]
! grep -q '^# CONFIG_' "$fragment"
for setting in CONFIG_NF_CONNTRACK=y CONFIG_NF_TABLES=y CONFIG_NFT_CT=y; do
	grep -Fxq "$setting" "$repo/configs/kernel/rog5-mainline.fragment"
done
sh -n "$builder"
grep -Fq 'rog5-tailscale-netfilter.fragment' "$builder"
grep -Fq 'NF_CONNTRACK_MARK n -> y' "$builder"
grep -Fq 'cd "$output_dir"' "$builder"
grep -Fq 'expected_baseline=6329b42fac5876d3f42557802bd530ba2c077aa73c4543f0bbc37ea65902eeb4' "$builder"
! grep -Eq 'fastboot|flash|erase|set_active' "$builder"
echo 'PASS Tailscale netfilter build is one-symbol, baseline-bound and build-only'
