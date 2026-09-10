# Generation 150 bounded UFS write benchmark

Result: **CONSUMED; POST-CRASH PARTIAL IDENTITY REFUSAL.** Never flash or retry.

Primary question: does aligned direct I/O avoid the UFS stall seen during
Generation 149's buffered dense image write?

The exact target preserves the 825,884,672-byte partial image and writes only
two disposable 32 MiB files in a new fixed benchmark directory: aligned
`O_DIRECT` first, buffered second. Each operation has a 180-second command
bound. It records timings, UFS error-line count, and battery temperature,
removes the disposable files on success, relocks all block nodes, and returns
fastboot. A separate 420-second watchdog invokes restart2 in the background
and then SysRq without calling `sync`, so D-state I/O cannot block fallback.

The target reuses the exact clean-twin Generation-149 write-capable Image,
DTB, and matching 4+15 modules. Target initramfs twins built in 6.399 seconds
and match at SHA-256
`5180199dc15777cc635b1e2dc1ff94039296c563a89dd49d6f64025e19fd7513`,
size 23,804,916 bytes. The exact sealed BusyBox executes both direct and
buffered fixture writes under QEMU.

Signed bundle manifest SHA-256:
`48022ec8595d57b4cb64445fd4802879e0c652a96db31937dc2bd6826a23361a`.
Generation-150 RAM-only AVB SHA-256:
`e28b4c489e9507a5dba48b5c94af844c087fcf5d01efc7371343830db577cb12`.

The bounded Opus review timed out after five minutes without a verdict. No
recommendation from it was treated as evidence.

The sole cycle passed power/USB, UFS, runtime, and key-only SSH, then emitted
exact `reason=partial-identity` before creating the benchmark directory or
writing data. Ext4 recovery changed the partial file from its pre-crash exact
tuple. Exact fastboot fallback and host cleanup passed. The successor accepts
only absence or one root-owned regular mode-0600/0644 partial no larger than
the previously observed 825,884,672 bytes and reports its exact state.
