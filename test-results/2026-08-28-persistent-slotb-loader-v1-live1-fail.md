# Persistent slot-B loader v1 — RAM-only test 1

- Result: failed closed before target USB NCM; loader image accepted by `fastboot boot`; target Arch identity never appeared.
- p24 prerequisite: the signed release bundle was staged successfully with one exact allocated-RAW transfer in 60.628 seconds. GPT, boot partitions, slot metadata, and protected partitions were untouched.
- Fallback: the phone reached slot-A stock recovery with unauthorized ADB, not callable fastboot. The USB descriptor uses VID/PID `18d1:d001` but advertises ADB interface protocol/string, so `fastboot` correctly refuses it.
- Earliest exact loader stage: unknown until the retained ramoops snapshot is collected. Do not infer mount, selector, signature, Haven-watchdog, or kexec failure from missing target USB.
- Classification: likely R3/R8 boundary, pending pstore; not a mainline kernel regression.
- Candidate disposition: loader v1 RAM-only execution is consumed and must not be retried unchanged. `boot_b` remains unmodified.
- Next gate: physically enter bootloader fastboot, boot canonical observation recovery without PREPARE/COMMIT, read pstore, add the exact failure as a regression, then issue a corrected loader.
