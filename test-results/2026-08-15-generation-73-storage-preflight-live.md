# Generation 73 read-only storage preflight

Generation 73 ran once on 2026-08-15 and is irreversibly consumed. It must
never be retried.

The sealed RAM-only recovery enumerated on the anchored USB port 18.856
seconds after the host started `fastboot boot`. Its persistent raw ACM channel
delivered one exact terminal report:

```text
status=FAIL stage=S41_EXT4_MINIMUM reason=resize2fs_failed all_read_only=1 block_mounts=0
```

This proves exact UFS topology, whole-disk and `userdata` read-only locking,
GPT validation, and `e2fsck -fn` completed before the failure. No phone block
device was mounted and no storage write path existed in the candidate.

The failure was reproduced hardware-free with the exact sealed ARM64
e2fsprogs 1.47.4 tools. A snapshot taken while ext4 was mounted contains
`needs_recovery`; `e2fsck -fn` returns zero while explicitly skipping journal
recovery, then `resize2fs -P` refuses it and requests a forced filesystem
check. The same tool succeeds on a clean true read-only loop device. The
fallback-to-fastboot path used a direct `RESTART2` syscall without first
remounting its ext4 root read-only, which explains the journal-pending input.
The terminal report did not retain tool stderr, so the live artifact alone
does not prove the text of the refusal; the exact stage sequence, reproduced
tool behavior, and fallback transition make this the leading explanation.

Recovery remained present for 12.558 seconds, then its intentional rollback
disconnected USB. Exact Alpine fallback appeared 18.164 seconds later on the
same port. Signed fallback evidence reported maximum temperature 40.8 C,
PMIC `PS_HOLD` / `HARD_RESET`, no PMIC watchdog signal, and zero fatal tokens.
Pstore was unavailable and the preflight did not emit a target boot ID, so
that postmortem is explicitly uncorrelated and cannot prove that no target
crash occurred.

The successor classifies `needs_recovery` or `orphan_present` before invoking
`resize2fs`, and the guarded fallback reboot remounts exact `/dev/sda23`
read-only and verifies a clean superblock before committing `RESTART2`.
