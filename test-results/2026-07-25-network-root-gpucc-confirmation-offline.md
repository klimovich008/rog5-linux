# Network-root v16 trace-free GPUCC confirmation — offline acceptance

Date: 2026-07-25

Result: **offline acceptance passed; no full GPUCC, GPU, DRM/MSM, or
acceleration claim**. V16 is eligible only for one attended RAM-only,
zero-storage confirmation. The phone remained in the exact persistent
fallback while this checkpoint was designed, tested, and verified. Nothing
was flashed.

V15 made the runtime-PM-enabled DISPCC provider active, completed all seven
observed RCG reads that previously stalled, and advanced GPUCC common-clock
registration through completed index 6 and into index 7. Its independent
75-second watchdog reset after 73.901 seconds of uninterrupted 100 ms
Qualcomm/CCF/RCG2 trace delivery. No marker gap exceeded 0.116 seconds.
Therefore v16 changes only the attended runtime configuration: keep the exact
v15 behavior and binaries, disable all high-volume core traces, and retain the
bounded delay-free outer GPUCC module trace.

## Unchanged kernel and package identity

V16 introduces no kernel, module, DTB, initramfs, wrapper, or Android-package
change. Rebuilding those products would recreate the already accepted v15
bits and would not test the changed runtime contract. The v16 exact verifier
therefore invokes the complete v15 bundle verifier and requires the same
fourteen-file manifest.

The behavioral source remains:

| Source identity | Value |
|---|---|
| Linux base | `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` |
| v15 candidate commit | `d9ac316489f4258d389d6298659d5e9c22183400` |
| v15 candidate tree | `c796deb1cc54e942f8bb46a2c76a7199e19e5c92` |
| runtime-PM patch SHA-256 | `a309fe55dc6221f4475c22beb43018dde0f2eb107fa60e84f8e43f28e17a4a25` |
| outer GPUCC trace patch SHA-256 | `50ec8d394583951ab00e65c38686775031d0abadc6a3faf1730edda13eb7be94` |

The exact artifacts remain:

| Artifact | SHA-256 |
|---|---|
| Linux 7.1.4 config | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| Linux 7.1.4 Image | `d30df38804750ded48607135a7d23d4f95e0947c49b68395a8f6818c4a27c54b` |
| Linux 7.1.4 Image.gz | `a620dd40df6d495e00a8f7f84e707c9ceb7483f0828afb2372792985e69f008e` |
| matching module archive | `9350e5a010c0af11fe4bde48527d056701c83a0072be4ad29cce2565a75204a1` |
| external `gpucc-sm8350.ko` | `9ac07151490fe4844462945014e0a74674b43841e4cea1cfc4c3560231067d2a` |
| exported symbol table | `008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365` |
| GPUCC-only DTB | `e6f86c3022f58a765351b5b761c8bc815b093209517adb4678107d542ff5bcb5` |
| target initramfs | `4f3077d02c40b5d27ab602562534cacf11324554ae75b0246fd4429bced9bbac` |
| nested staging initramfs | `68b8729c5aef7f9a3eacba07685fe952f4df6cac29eb8c35d9559fda98722fab` |
| ASUS wrapper Image | `bf4abdad89941b34f769af25f80d8b93ac202a77c31005d572bc559255d61b7e` |
| raw boot image | `392ee5b0aa674f95da1b2dd544d25aab8d201f8d5a310fda2c8ab805fc1a6793` |
| temporary-boot AVB image | `bb4a6e34c98475f991a9575defe57c52ac732da0cea96a10585ee0bb92ae7730` |
| fourteen-file manifest | `a739f975f87ac30918625178007b4cd7302449ae96c26e5c42185e9e1a0425cc` |

The two v15 mainline builds and two independently prepared nested
wrapper/package paths already match byte-for-byte. V16's exact verifier
rechecks their accepted artifact identities, nested payload, AVB round-trip,
zero credentials, disabled consumers, and zero-storage boundary.

## Trace-free transport and probe contract

The host ACM helper now exposes one explicit fixed action named
`load-gpucc-confirmation`. It loads diagnostic systemd masks and the
900-second initial rollback timer but supplies none of:

- `ROG5_QCOM_CC_PROBE_TRACE`;
- `ROG5_CCF_REGISTER_TRACE`; or
- `ROG5_RCG2_PARENT_TRACE`.

The existing traced `load-gpucc-diagnostic` action remains separate. Kexec
execute remains its own one-shot action and is never retried.

The guarded module probe retains traced diagnostic behavior as its default.
V16 must explicitly set `ROG5_GPUCC_TRACE_MODE=confirmation`. In that mode,
before arming the independent watchdog, the probe requires for each of the
three core parameters:

- exact command-line count zero;
- the built-in mode-`0400` parameter to exist;
- parameter value `N`; and
- no writable control.

An omitted confirmation mode fails closed because the default diagnostic
contract expects all three parameters enabled. Confirmation mode is rejected
for every module except `gpucc_sm8350`.

The external module still loads with its read-only `probe_trace=1` parameter.
That outer trace emits eight notices when the probe returns: begin, map
complete, two begin/complete PLL pairs, registration begin, and registration
complete. Source verification proves it adds no sleep or deliberate delay.

The independent probe watchdog remains 75 seconds and the required post-load
settle interval remains 30 seconds. With the one-second dmesg-follower setup
and no deliberate core-trace delay, approximately 44 seconds remain for
registration before the stability interval. The watchdog remains a hard
safety bound, not a prediction that registration will complete.

## Test-first evidence

The new confirmation test failed against the traced-only workflow before
implementation. After implementation, all focused tests pass:

- semantic confirmation verification;
- a read-only pre-disarm target baseline proving the original 900-second
  watchdog remains armed while all three core traces are absent and `N`;
- source verification that the baseline checks exact network-root,
  zero-storage, consumer-isolation, thermal, module-tree, and quiet-log gates
  without a control or persistent-write path;
- mutation rejection for confirmation count `1`, state `Y`, an unsafe
  confirmation default, omitted RCG2 checking, an allowed `trace=0` argument,
  disabled outer trace, a traced confirmation load action, and an added outer
  delay;
- the existing allowlist, zero-storage, watchdog, module-hash, consumer, and
  post-load probe contract;
- all 9 pseudoterminal ACM transport tests, including bounded identical-load
  replay and never-retried execute;
- exact v16 bundle contract; and
- the complete exact v16 bundle verifier, including the nested v15 verifier.

The pinned procedure sources are:

| Procedure source | SHA-256 |
|---|---|
| guarded coldplug probe | `7fbc01a2308ea258c51e2f88c01346bd8397dcb545f8f7cab7e13b6f23fba33e` |
| control-safe ACM helper | `cd5cfabca51a4709e87e268ac93d3f37eb61e5c3100d1406bfdf46941834ec33` |
| semantic confirmation verifier | `d2220b3f53f6f2d7c9c90e5d6f8f31dc1c5b8017cfd44b12cc6e52b6cf7a53ee` |
| confirmation mutation test | `0f865b6ab581d89af5defb54f4a7ff3755a5d7f03af58a59529e7a22403fcd9c` |
| pre-disarm confirmation baseline | `cbbbce7149ea35c67cfefac6b312c86a88ecf81dc34b0f77d124d6d0007267a6` |
| pre-disarm baseline source test | `b745eabbfdd7a19d49f178b9100b6b12bc47e73f07eef26da6f965bd6c731a5b` |

No boot image, kernel, module, firmware, credential, private identifier, or
personal data is committed.

## Offline acceptance

The checkpoint passes:

- the complete v15 lock model, source/mutation tests, KUnit suite, duplicate
  build/package evidence, and exact bundle verifier;
- an explicit fixed confirmation load action with all core traces absent;
- a hash-pinned read-only baseline that must pass while the initial watchdog
  is still armed;
- a fail-closed probe mode requiring command-line count zero and mode-`0400`
  `N` state for each core parameter;
- a delay-free read-only outer trace with exactly eight notices on return;
- the exact 75-second watchdog and 30-second stability interval;
- exact module hash, ABI, tmpfs path, ownership, and mode;
- GPUCC `okay` while GPU, GMU, Adreno SMMU, display consumers, UFS, RTC,
  input, and every remote processor remain disabled;
- no GPU firmware or GPUCC module inside either initramfs;
- zero physical-storage path, read-only NFS lower, credential-free staging,
  header-v3/AVB round-trip, and inherited automatic rollback; and
- source hashes pinned by the exact v16 verifier.

## Safety and one-shot live gate

The AVB footer remains algorithm `NONE`. It is a deterministic temporary-boot
container, never a flash target. V15 must not be rerun.

Before one v16 attempt, re-audit the exact persistent fallback, host
NFS/firewall/profile/inhibitor state, candidate hashes, strict SSH identities,
clean logs, pstore, thermals, and synchronized Git checkpoint. Keep the
900-second target rollback armed through baseline and tmpfs payload checks,
then atomically replace it with the independent 75-second probe watchdog.

Accept the GPUCC-only candidate only if all of these pass:

1. the eight outer markers reach `registration-complete ret=0`;
2. `insmod` returns and `gpucc_sm8350` remains loaded;
3. the platform driver binds exactly one GPUCC device;
4. the 30-second stability interval completes;
5. no GPU/GMU/SMMU consumer binds and no DRM render node appears;
6. systemd, zero-storage, read-only NFS, USB carrier, thermal, warning/fatal,
   and failed-unit gates remain clean;
7. the independent watchdog is safely disarmed only after every post-load
   check; and
8. a normal reboot or the watchdog restores exact fallback with complete host
   cleanup.

A module error, a new non-returning outer marker, transport departure, or
post-load regression consumes v16 and is not retried. Even a complete v16
PASS accepts only the GPUCC/CCF foundation. Power domains, regulators, IOMMU,
GMU, firmware, DRM/MSM, and accelerated desktop remain separate tiers.
