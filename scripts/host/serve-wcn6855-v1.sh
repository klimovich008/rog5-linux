#!/usr/bin/env bash
# shellcheck disable=SC1090,SC2034,SC2329
set -euo pipefail

fail() {
	echo "FAIL $*" >&2
	exit 1
}

repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)
root=${1:-/var/lib/rog5-network-root-wcn6855-v1}
accepted_serve=$repo/scripts/host/serve-network-root.sh
accepted_serve_sha=e3961cc441ae6cb75f1a3dcbbd5e4ccc99b31c67018159ac10f61c11f1548769
host_ip=169.254.77.1
phone_ip=169.254.77.2
host_cidr=$host_ip/30
firewall_zone=drop
export_mount=/run/rog5-network-root-export
mountd_port=32767
grace_time=10
lease_time=10
serve_timeout=${ROG5_NFS_TIMEOUT:-900}

[[ $EUID == 0 ]] || fail 'run through PolicyKit; do not share a sudo password'
if [[ ! $serve_timeout =~ ^[0-9]+$ ]] ||
	((serve_timeout < 60 || serve_timeout > 86400)); then
	fail 'ROG5_NFS_TIMEOUT must be between 60 and 86400 seconds'
fi
for command in awk date exportfs firewall-cmd findmnt grep install ip mount \
	mkdir mountpoint nmcli pgrep realpath rpc.mountd rpc.nfsd sed sha256sum \
	ss stat sysctl systemctl tr udevadm umount; do
	command -v "$command" >/dev/null || fail "missing host command: $command"
done
[[ -f $accepted_serve && ! -L $accepted_serve ]] ||
	fail 'accepted NFS runtime is absent or linked'
[[ $(sha256sum "$accepted_serve" | cut -d ' ' -f 1) == \
	"$accepted_serve_sha" ]] || fail 'accepted NFS runtime hash mismatch'
[[ -d $root && ! -L $root ]] || fail 'missing prepared WCN6855 v1 root'
root=$(realpath -e "$root")
[[ $root == /var/lib/rog5-network-root-wcn6855-v1 ]] ||
	fail 'unexpected WCN6855 v1 export root'
[[ ${ALLOW_WCN6855_V1_NFS:-} == 1 ]] ||
	fail 'set ALLOW_WCN6855_V1_NFS=1 for the attended WCN6855 enumeration-only window'
"$repo/scripts/host/verify-wcn6855-v1-export.sh" "$root"

[[ $(grep -c '^etab=' "$accepted_serve") == 1 ]] ||
	fail 'accepted NFS runtime boundary changed'
source <(sed -n '/^etab=/,$p' "$accepted_serve")
