#!/usr/bin/bash
# Offline generic ARM64 VM fixture; never install or run on a phone.
set -euo pipefail
[[ $(id -u) == 1000 && $(id -G) == 1000 ]]
[[ $(cat /proc/1/comm) == systemd ]]
record=$(timeout -k 1 5 loginctl show-session self --no-pager -p Active -p Remote -p User -p Class -p Type -p Seat -p VTNr -p Scope -p Id)
printf 'OBSERVE local session\n%s\n' "$record"
for line in Active=yes Remote=no User=1000 Class=user Type=tty Seat=seat0 VTNr=1; do
    [[ $'\n'$record$'\n' == *$'\n'"$line"$'\n'* ]]
done
[[ $XDG_RUNTIME_DIR == /run/user/1000 && $(stat -c '%u:%g:%a' "$XDG_RUNTIME_DIR") == 1000:1000:700 ]]
printf '%s\n' "$XDG_SESSION_ID" > /run/mobile-home/session-id
manager_state=$(systemctl --user is-system-running) || [[ $manager_state == degraded ]]
echo "OBSERVE user manager state=$manager_state"
[[ $manager_state == running || $manager_state == degraded ]]
systemctl --user show-environment >/dev/null
LIBSEAT_BACKEND=logind /run/payload/logind-seat-probe
echo 'PASS local active tty1 session, user manager and mediated devices'

if [[ -f /run/startup-only ]]; then
    [[ -f /run/session-sha256 ]]
    echo 'PASS startup-only authenticated readiness; Denial NOT RUN'
elif [[ -f /run/session-sha256 ]]; then
    /usr/bin/bash /run/logind-denial.sh
fi
