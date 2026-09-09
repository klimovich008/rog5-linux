# Source teardown replay limits

`hugetlbfs.mountinfo` models the retained phone's `/dev/hugepages` mount
(`0:35`, `hugetlbfs`, `pagesize=2M`) after shutdown mount transfers. Mount IDs
and parent IDs are synthetic. The second copy models systemd's recursive
bind of `/dev` into the exitrd. Systemd v261.2 skips mounts below API
filesystems in [umount.c](https://github.com/systemd/systemd/blob/v261.2/src/shutdown/umount.c)
and binds `/dev` recursively in
[switch-root.c](https://github.com/systemd/systemd/blob/v261.2/src/shared/switch-root.c).
This is a parser regression fixture, not captured exitrd mountinfo or proof
of the physical missing receipt's cause.

The original `assembled-*` cases execute the generated shutdown script, but
report mountpoints absent except for the injected unclean case. They do not
exercise mount moves, loop detachment or storage relocking. The
`real-netcat` case sets both diagnostic addresses on loopback inside a fresh
network namespace; it verifies the sealed applet and wire exchange, not USB
or IP survival during physical shutdown. A PASS grants no phone or release
qualification authority.

## Stateful shell coverage

The optional `stateful-*` cases execute the same generated shutdown and sealed
BusyBox with a stateful synthetic kernel in `stateful.h`. Runtime records match
the installed overlay/state layout with a fixture boot ID. The fixture starts
with eight mounts, a mounted old root, two attached loops and writable sda/sda23.
It models the service-state stop variant separately. A journal-derived case
also starts with root-ro/state absent and loop0 attached: the retained source
journal reports those unmounts succeeded before exitrd. The already-absent
userdata-ro mount is omitted there too. Loop0 must remain attached until the
overlay root releases its reference even when its ext4 mountpoint is gone.
This inferred entry layout is not a captured exitrd namespace.
Mountinfo, backing-file
entries and read-only flags change as operations succeed. It refuses loop
detachment before unmount, userdata unmount while a loop is attached, and
storage relocking before the writable mounts and loops are gone. Seven direct
refusal cases check these model constraints independently of the shutdown.
They require exit status 1; fixture errors do not count as a correct refusal.

Clean runs require ordered unmount/detach/relock operations, exactly 117 relocks,
an empty final mount/loop state, `clean=1` at the real bounded observer call,
a valid receipt and fallback. Injected move, unmount, backing-file, detach and
relock failures require `clean=0`, no receipt and fallback. False detach success
also exercises the unchanged shell's postcondition check.

Supply `--inert-block-node /absolute/path` to include these cases. The input
must be an existing block node with major/minor **0:0**; the runner never creates
it, elevates privileges or opens it. Read-only namespace binds supply block
metadata for the shell's unchanged `test -b`. A private administrator-created
mode-000 0:0 node can serve as this fixture input. No real host device is valid.
All device stat/ioctl results, mount transfers and loop operations remain
simulated. File contents are already at their destination paths; this model
does not validate Linux mount propagation, actual syscalls, systemd execution,
UFS quiescence or physical transport. Each run retains the operation log,
final state and exact source/artifact hashes without qualification authority.
