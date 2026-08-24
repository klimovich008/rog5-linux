# Generation 112 optional-hotplug guard

Date: 2026-08-24

Result: **OFFLINE PASS; UNISSUED.** No phone contact or boot authority.

Primary question: does guarding the absent optional `kernel.hotplug` sysctl let
the otherwise byte-identical controlled writer reach target NCM/ACM and key-only
SSH?

Generation 101 and 111 both terminated before target USB. Exact Image config,
Linux source, archived initramfs bytes, and sealed AArch64 BusyBox behavior prove
that `set -e` exits PID 1 when `/proc/sys/kernel/hotplug` is absent under
`CONFIG_UEVENT_HELPER=n`. Generation 102 used the same Generation-101 Image and
DTB with non-errexit mature init and reached NCM/ACM. A bounded Opus review
independently confirmed the defect is fatal while retaining initramfs delivery
as an alternative until observation evidence is collected.

Generation 112 changes one source command only:

```sh
echo /sbin/mdev >/proc/sys/kernel/hotplug || :
```

Identities:

- Image: `a7e0cd84238d9e0c399a6c93d3c7a5996571dc3536b10c7323cbe1455dbad01e`;
- DTB: `4f6518b3fddd1695c9059f1faeedf0458dabdba5c779ee72bededff9c56c76b8`;
- clean-twin initramfs: `0cb40afda8d0068f9c504dde10b155dc71f74b85bc4612e89d368f97b05c8701`;
- signed manifest: `d3e3dc8627c19356ca187aec1ca7abe23a635ed98ed9c10ed9fa82db9cda043a`;
- Generation 112 wrapper: `dafa103015313aa0d879aaea1f24e5ead375b236abf3170b2e6ac61f3b96d8b8`.

The fail-first test executes both unguarded and guarded commands against the
exact archived AArch64 BusyBox and real procfs EACCES behavior. The unguarded
form exits before its marker; the guarded form reaches it. Active CI passed in
8 seconds before packaging. The candidate remains revoked pending independent
ramoops collection from fastboot.
