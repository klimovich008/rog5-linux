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
