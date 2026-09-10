# Read-only RPMh state transport

Question: what APPS voltage/enable/mode votes are inherited for S12 before any
Wi-Fi power request? V10 established that acknowledged AUTO did not prevent the
first-enable reset. No further voltage-setting experiment is authorized by this
checkpoint; V11 and the stock slot-A rescue remain unchanged.

## Implementation

Patch0035 adds a separate `rpmh_read()` transport, based on Qualcomm's read
message encoding. It does not import regulator-registration/readback policy,
add S12 nodes, modify voltage constraints, or update wake/sleep vote caches.

- Read commands omit the WRITE bit and do not program command DATA.
- Busy/conflicting slots return EAGAIN without queuing; writes retain their
  original waiting behavior.
- Reads require a dedicated ACTIVE TCS. Independent review caught that borrowing
  WAKE would overwrite wake commands without dirtying the cache; a fail-first
  regression reproduced this and now passes with refusal before reservation.
- Caller and IRQ hold separate heap references. Timeout changes no caller data
  and leaves the IRQ's request alive until completion. A late IRQ never touches
  a caller-owned stack/completion/output pointer.
- Completion consumes the stashed read pointer, copies the response, then wakes
  the caller. Read response data is available before tracing/completion.
- The response wait remains10s. Existing bounded MMIO synchronization precedes
  it; no claim of protection against a wedged CPU or bus is made.

The pending allocation/TCS may remain if hardware never completes. The observer
must stop after timeout, not accumulate new requests. Existing write-timeout
behavior is not redesigned by this patch.

## Offline validation

Three focused tests execute the exact added C and changed transport functions.
They cover allocation/submission errors, completion before/during waiting,
timeout followed by late IRQ, unchanged caller data on error,500 threaded
completion races under ASan/UBSan, read opcode/data suppression, busy admission,
read-slot clearing and unchanged writer behavior. Early-free and write-opcode
mutations are rejected. The no-ACTIVE/Wake fallback test failed before its fix.

The new read object, existing RPMh object and controller object compile against
the exact V11 headers with the patched TCS/API declarations. This is object-level
verification, not a complete kernel or phone qualification. The first controller
compile lacked its local trace header; the header was supplied and the failed
object alone was rebuilt. The original source and module kit were untouched.

## Build preparation

The new virtual Git checkout is source commit
`84be487359a51844cbeb64d84932e8dcc433857a`, tree
`26f28eb8076ac9bfa46320715d078dbbff8d04c9`. It reuses read-only baseline
directories and overlays only changed source files; no1.7GiB checkout copy.
Its Git status is clean inside the pinned builder.

The already-deployed high-speed UFS source is included in-tree, with exact
source hash `f7bcbad6ce6307e1fbbf8757e5d37f135791292ae2cdd1b875c33bd937935b95`.
The V11 base+Tailscale fragment composition was recovered instead of silently
using the current generic fragment alone. A21.811s configuration preflight
reproduced the exact V11 config hash
`889d836fdc2928034d5d2a66062e4fa7d6ca204f82d506acc9fd17bb4a651bef`.
Expected kernel release is `7.1.4-g84be487359a5`.

The first build invocation stopped at the ancestry gate, before creating kernel
output: the shared source clone lacked the original shallow-history boundary.
Copying that exact metadata fixed the ancestry check; source commit/tree and
kernel release did not change. The failed log is retained, and the first actual
compilation continues as attempt a-r2, not a discarded/restarted kernel build.

Clean builds use bounded project-owned RAM scratch space and a pinned Clang18
container, not deletion of retained builds. Scratch may be unmounted only after
its required artifacts/evidence are verified in durable storage; failure retains
the scratch for diagnosis. No kernel candidate has been issued or booted.
The clean twins use separate output directories/leases, two CPUs each, with
read-only shared source. Both build processes may run concurrently; neither
can modify the other's output or the preserved V11 inputs.

## Observer

The fixed-resource module requires the baseline DT: no S12 regulator node and
PCIe disabled, exact PM8350/RSC identities and command-DB addresses. It reads
S12 voltage/enable/mode first, then the optional L6 sanity reference. It never
requests regulator changes. Only unqueued EAGAIN is retried (five attempts,
20ms spacing); a timeout stops all further requests. Its snapshot reports
unavailable data explicitly and is not a physical-voltage measurement. The
debugfs file owns a module reference while open.

## Completed clean-build checkpoint

Both clean builds passed: A2371.747s, B2416.962s. Config, Image/Image.gz,
vmlinux, symbol tables, build metadata and all19 UFS/power modules match.
Both observer modules match after compilation against each completed kernel;
their builds took19.396s and17.503s. No preserved source/kit was modified.

- Image: `a0cae27023188dfb4f9dfc9dd9e9ed73a33dafd11f80e3917e70192867a58e25`
- Initramfs: `58485719f2025d649c1b3211385c23fbf33e22e33bd98c87dce782e7ae2992d3`
- Read-only observer: `ec136d9231e998505249f729e8d31b1109d5c5c392e47d2f643c55602d6d5edb`

The refreshed archive changes exactly19 modules plus the single release line
in `init`; all other634-entry archive content/metadata is preserved. The two
refreshes took8.336s/8.093s; independent twin/archive verification21.826s.
Exact-Image QEMU took8.025s: all19 normal modules loaded, both observers
returned ENODEV on the non-ASUS machine, no snapshot or BTF/symbol error.
QEMU does not prove the physical RPMh transaction or inherited vote values.

Source305823e6 passed full local CI606.194s while compilation was active;
GitHub run33365885277 passed exact-head, merge, QEMU and publication checks.
The next publication changes only one generated exact claim and these current
documents; no claim-consumer behavior or historical record is changed.
The admission test refused the unknown profile before insertion, then passed;
all16 existing claim-consumer tests pass. This was the unconsumed build
checkpoint; the subsequent live trial is recorded below and is consumed.

The signed readback bundle uses the unchanged baseline DTB (PCIe disabled,
no S12 node). Voltage-voting and radio-probe tools were excluded from its
source runtime. It is not a voltage-setting or Wi-Fi activation trial.
Runtime manifest:
`efbe767ee49d7fd721176d4a261dec4e8a5dd5407437d91688c13dbf9ca4f426`.

The full completed A output/cache is retained in a909700813-byte compressed
archive, SHA256`fc5f1856ee6dc24ca0515215f9aa67feb7cb02520e509927e1165fe100ba6c82`;
every archived entry was compared with the output and the durable copy was
hash-verified. No older build data was deleted. RAM scratch was released after
the twin/bundle evidence was archived and verified. Disk headroom is low;
do not duplicate the full B cache or start another disk-based clean build.

An initial packaging call failed before signing because `gh` inferred its
repository from the caller's directory (R6/R7). Explicit repository selection
was verified from `/tmp`, then packaging passed in0.311s. No phone cycle was
spent on this host-only defect. Remaining R2/R3 risks are exact deployed
composition and physical capability, not a reason to alter voltage policy.

## Live readback-v11: passed, consumed

Executed once from publication370f7493 after all exact-head/merge/QEMU checks
passed in GitHub run33369696230. Target boot
`deedf8ee-474e-4010-8daa-97097a3ad425` reached Arch, UFS, NCM and strict SSH.
Claim→SSH42.641s; claim→readback47.332s. Six reads returned successfully;
S12's three packets used read message ID0x108 with matching responses and no
S12 write packet. All117 nodes were read-only before kexec and before reads.

| APPS field | Raw response | Decoded vote |
| --- | --- | --- |
| S12 voltage | `0x4c8` | 1224mV |
| S12 enable | `0x80000001` | 1 |
| S12 mode | `0x3` | retention |
| L6 reference voltage | `0x800004b0` | 1200mV |
| L6 reference enable | `0x0` | 0 |
| L6 reference mode | `0x80000007` | code7 |

Voltage/enable/mode masks follow the
[upstream regulator readback change](https://patchew.org/linux/20260801-b4-read-rpmh-v5-v6-0-9fcb54928523@oss.qualcomm.com/20260801-b4-read-rpmh-v5-v6-3-9fcb54928523@oss.qualcomm.com/).
Mode3 is PMIC5 SMPS retention in the exact source. Other bits remain explicitly
uninterpreted. These are control votes, not aggregate physical rail measurements.
The tested decoder retains upper bits and reports errors/missing fields without
inventing zero values. Sanitized live values are a regression case.

Source/target-before-read PON snapshots were identical. After the requested
normal reboot, the FIFO recorded PS_HOLD/HARD_RESET and V11 returned. This is
not a claim that missing pstore excludes a crash. The boot-time SID5 SPMI warning
and probe EIO also exist in V10; they are not newly attributed to the reader.

V11 boot`19c698fe-513d-468b-ada3-485a5902fa5e` was verified after fallback;
reboot→state/Tailscale service restoration61.007s. Normal shared USB networking
was then explicitly restored. Strict SSH via10.77.0.2, Tailscale Running/online
with empty Health, Full/Good battery8.618V/30.0C, NCM-only gadget, and exactly
sda+sda23 writable passed. No GPT, boot-slot, selector or persistent deployment
change occurred. Temporary observers, port8079 and management alias were removed.

Pre-boot host issues were fixed without consuming a phone cycle: over-budget
current docs were compacted (R9/R10), and the old-only stage parser was adapted
to the two exact releases (R1/R7). A simulated target setup failure exposed
an exception path that skipped fallback observation; its fail-first test passes.
After fallback, the private runner omitted the existing shared-profile restore
(R6): the host retained only its management address. Restoring the existing
profile on the identity-verified interface fixed this without another boot.
Do not mistake this host-network cleanup omission for a Wi-Fi/kernel failure.
Sanitized before/after state is retained in
`tests/fixtures/native-wifi/readback-host-recovery.json`; the next runner must
replay it and include the existing post-fallback profile-restoration step.

The next power experiment must preserve the captured S12 vote during first
enable before considering a higher-voltage/radio request. The existing driver
caches DT-min1352mV while enabled-state is unknown and submits it on first
enable; the live inherited vote was1224mV/enabled. This establishes a software
state mismatch, not the electrical cause of the previous reset. Do not deploy
radio at an unqualified voltage or import global regulator policy blindly.
The now-qualified readback kernel can be reused for module/DT-only experiments.
