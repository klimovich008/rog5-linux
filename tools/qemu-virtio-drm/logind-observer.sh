#!/usr/bin/bash
# Offline generic ARM64 VM fixture; never install or run on a phone.
set -u
for ((i=0;i<4;i++)); do
    sleep 25
    echo "OBSERVE independent snapshot=$i uptime=$(cat /proc/uptime)"
    while IFS= read -r line; do
        case $line in MemTotal:*|MemFree:*|MemAvailable:*|Slab:*|SUnreclaim:*|AnonPages:*) echo "OBSERVE memory $line";; esac
    done < /proc/meminfo
    timeout -k 1 5 systemctl list-jobs --no-pager || :
    timeout -k 1 5 systemctl --no-pager --full status systemd-logind dbus rog5-logind-fixture || :
    timeout -k 1 5 journalctl -b --no-pager -u systemd-logind -u dbus -n 45 || :
    for file in /proc/[0-9]*/comm; do
        read -r name < "$file" || continue
        case $name in
            systemd|systemd-logind|systemd-executor|dbus-broker|bash)
                p=${file%/comm};echo "OBSERVE process $p $name"
                cat "$p/wchan" "$p/syscall" || : ;;
        esac
    done
done
