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

The assembled cases execute the generated shutdown script, but the shim
reports mountpoints absent except for the injected unclean case. They do not
exercise actual mount moves, loop detachment or storage relocking. The
`real-netcat` case sets both diagnostic addresses on loopback inside a fresh
network namespace; it verifies the sealed applet and wire exchange, not USB
or IP survival during physical shutdown. A PASS grants no phone or release
qualification authority.
