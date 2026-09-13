#!/usr/bin/env bash
# Synthetic authentication only, in the isolated VM. Never source on a target.
set -euo pipefail
source /run/nonroot-session.sh
nonroot_guest_guard
[[ " $(cat /proc/cmdline) " == *' rog5.pam_fixture=1 '* && $EUID == 0 ]]
nonroot_prepare
# Generic kernel has no qualified RTC. Fix only this disposable guest clock so
# account aging is tested deterministically rather than against the Unix epoch.
date -u -s '2026-09-13 00:00:00' >/dev/null
printf 'synthetic accounts only\n' > /run/pam-fixture
chmod 644 /run/pam-fixture
cp /usr/bin/unix_chkpwd /run/unix_chkpwd
chown 0:0 /run/unix_chkpwd
mount --bind /run/unix_chkpwd /usr/bin/unix_chkpwd
cp /run/payload/pam-probe /run/pam-probe
chmod 755 /run/pam-probe
cp -r /etc/pam.d /run/pam.d
mount --bind /run/pam.d /etc/pam.d
cat > /etc/pam.d/rog5-fixture <<'PAM'
auth required pam_unix.so nodelay
account required pam_unix.so
PAM
chmod 644 /etc/pam.d/rog5-fixture
mkdir /run/faillock
chmod 755 /run/faillock
# Public test password. Only its synthetic hash exists in guest RAM.
password_hash=$(printf 'rog5-public-pam-fixture\n' | openssl passwd -6 -stdin)
printf 'root:!*:1:0:99999:7:::\nmobile:%s:20000:0:99999:7:::\n' "$password_hash" > /run/shadow
unset password_hash
chmod 600 /run/shadow
mount --bind /run/shadow /etc/shadow
failures=0
run_case() {
    local name=$1 mode=$2 nnp=$3 service=$4 response=$5 expected=$6 actual exit_status=0
    local -a flags=(--reuid=1000 --regid=1000 --clear-groups --bounding-set=-all --inh-caps=-all --ambient-caps=-all)
    [[ $nnp == 0 ]] || flags+=(--no-new-privs)
    chmod "$mode" /run/unix_chkpwd
    [[ $(stat -c '%u:%g:%a' /usr/bin/unix_chkpwd) == "0:0:$mode" ]]
    actual=$(DENIAL_PAM_SERVICE=$service timeout -k 1s 8s setpriv "${flags[@]}" /run/pam-probe "$response" 2>&1) || exit_status=$?
    printf 'CASE %s mode=%s nnp=%s service=%s exit=%s %s\n' "$name" "$mode" "$nnp" "$service" "$exit_status" "$actual"
    if [[ $exit_status != 0 || $actual != "PAM_BACKEND result=$expected secret_prompts=1" ]]; then
        failures=$((failures+1))
    fi
}
run_case stripped_valid 755 0 rog5-fixture valid Failure
run_case packaged_nnp_valid 6755 1 rog5-fixture valid Failure
run_case packaged_valid 6755 0 rog5-fixture valid Success
run_case packaged_wrong 6755 0 rog5-fixture wrong Failure
run_case login_valid 6755 0 login valid Success
run_case login_wrong 6755 0 login wrong Failure
awk -F: 'BEGIN {OFS=":"} $1 == "mobile" {$8=1} {print}' /run/shadow > /run/shadow.next
cat /run/shadow.next > /run/shadow
rm /run/shadow.next
run_case login_expired 6755 0 login valid Error
awk -F: 'BEGIN {OFS=":"} $1 == "mobile" {$2="!*"; $8=""} {print}' /run/shadow > /run/shadow.next
cat /run/shadow.next > /run/shadow
rm /run/shadow.next
run_case login_locked 6755 0 login valid Failure
[[ $failures == 0 ]]
echo 'PASS actual Denial PAM backend: eight privilege/password/account boundary cases'
