# Persistent slot-B loader v2 — offline checkpoint

- Question: what is the earliest exact loader boundary before mainline target NCM appears?
- Change: add one ACM-only advisory reporter to the existing local signed-bundle loader. It uses exactly one `a600000` UDC and emits bounded repeated stage records from `S00` through `S90`, or one exact terminal failure reason. Storage, signature, Haven-watchdog, kexec, fallback, and one-use execution semantics are unchanged.
- Loader initramfs clean twins: `9afff0524f7ce7a7c818cea5824fcb75b444549843b0c4a4693268b359682c27`, 7,604,268 bytes.
- ASUS wrapper clean twins: Image `55a9da9d9163a399bc07cb4e465910a55b7c1b9445f0b0b65d4e163574b30eb5`; raw boot `1d79ee93bc606913f191695b52371fb8f33f343c47c7055f3eb0db02cad52c80`, 58,109,952 bytes; AVB boot `b54b0e9a03ebf700ec44ff060d58ab6831db4e1f9c5c09e826f85148393270de`, 100,663,296 bytes.
- Wrapper cache: input `36a92c00676671eaff919300ad37a3b89fb7cdd25e73e430c9fb187456549228`; entry `8814b59cadc777fb36aacf170ce32bd4b6566a8d73b6e36b31f86a3b6bfb99d1`.
- Host-only incident: the first build stopped in twin A with `ENOSPC`; R9/resource classification. Six ignored superseded wrapper trees were removed, recovering 55 GiB. The incomplete 962 MiB output was retained as `build/persistent-slotb-loader-v2-wrapper.failed-nospace-20260828-r1`. The successful clean twin consumed 9.2 GiB and left 46 GiB free.
- Focused loader test: PASS. Repository active tier: PASS in 70.867 seconds. Full local CI: PASS in 443.341 seconds.
- Phone state at this checkpoint: stock slot-A recovery exposes unauthorized ADB (`18d1:d001`, interface protocol 1), not fastboot. No Loader-v2 boot has occurred and `boot_b` remains untouched.
- Next gate: full local and exact-head CI, then one RAM-only Loader-v2 boot from exact fastboot with host ACM collection. That cycle answers only the earliest loader boundary while collecting adjacent stage evidence.
