# Memory footprint: where the RAM goes, and the plan to get ~0.65 GiB of MemTotal back

Date: 2026-10-01, bundle `main-k111-d10-261001b` (kernel k111, DTB d10).
Phone access was read-only: nothing was installed, no sysctl or service was
changed. The user was in GNOME desktop mode on a 3840x1080 monitor (XR30),
with Steam and, partway through, a Proton game under FEX and Steam's shader
pre-compilation (`fossilize_replay`) running. Phosh was not running, so this
report has no idle-Phosh baseline (see the test plan).
Tools: `scripts/device/rog5-mem-report` (new; snapshot JSON kept in the
session scratchpad), `/proc`, debugfs (`dri/{0,1}/gem`, swiotlb, dma_buf;
never the DP connector files), `/proc/kpageflags`, and the ASUS 5.4
wrapper's own boot (`trial-stockcap-c1-session`: runtime FDT, dmesg,
subsystem table).

## 1. Where the 12 GB goes

| | MiB | Notes |
|---|---:|---|
| LPDDR5 fitted | 12288 | |
| Not in the memory map at all | 143 | `0xb7100000-0xbfffffff`: ABL gives the same 3-bank map to the wrapper. Firmware-owned, not reclaimable. |
| Memory node | 12145 | `Memory: 10790452K/12436480K available` |
| DT `no-map` carve-outs | 841 | table below |
| DT mapped, non-reusable | 360 | `0xedc00000` 288, `0xcbc00000` 68, ramoops 4 |
| `struct page` array | 190 | 64 B per 4 KiB page of the whole node, carve-outs included |
| SWIOTLB bounce pool | 64 | `io_tlb_used_hiwater` = **4 slabs (8 KiB)** after the game session |
| Kernel image | 31 | 16 MiB code, 9 MiB rodata, 4.5 MiB data (no KASAN/kmemleak; SLUB_DEBUG compiled in, off) |
| initrd (freed at boot) | 34 | returns to MemTotal |
| Other early allocations | ~49 | linear-map page tables, percpu (5 MiB), log buffer, unflattened DT |
| **MemTotal** | **10611** | (CMA 32 MiB is inside MemTotal: reusable, 28 MiB free) |

The DT reservations by owner (`/sys/firmware/devicetree/base/reserved-memory`,
d10):

| Range | MiB | What | Under the wrapper (stockcap-c1) | Verdict |
|---|---:|---|---|---|
| `0x8b800000` | 256 | modem PIL | modem OFFLINING, never loaded since cold boot | **reclaim candidate** (`pil`) |
| `0xd8800000` | 168 | removed_mem (static, stock too) | - | keep |
| `0xd0800000` | 119 | upstream `pil_trustedvm` | stock FDT has **no reg**; wrapper's trustedvm OFFLINING; Haven "HYPX NOT ENABLED" | **reclaim candidate** (`stockcma`) |
| `0x80c00000` | 70 | CDSP secure heap | ION SECURE_CARVEOUT heap the wrapper creates at 0.72 s (secure carve-outs are assigned to their VM) | keep |
| `0x34a000000` | 64 | memx | wrapper's qtee_shmbridge, R/W but no X (SEAs) | keep |
| `0xe5000000` | 35 | boot splash | scanned out until msm takes over | keep (see P3) |
| `0x86100000` | 33 | ADSP PIL | Linux boots it | keep |
| `0x89700000` | 30 | CDSP PIL | the standby bisect kit boots it | keep |
| `0x88200000` | 21 | SLPI PIL | Linux boots it | keep |
| `0xd0000000` | 8 | upstream `hyp_reserved_mem` | stock FDT has no reg | **reclaim** (`stockcma`) |
| `0xd8000000` | 8 | memshare (modem) | wrapper creates the DMA pool; memshare may assign it | keep |
| `0x80000000` | 6 | hyp | | keep |
| `0x85200000`, `0x85c00000` | 5+5 | camera, CVP PIL | OFFLINING (evass), no Linux driver | **reclaim** (`pil`) |
| `0x85700000` | 5 | video PIL | OFFLINING | keep for a future venus |
| `0xd7ef7000..0xd7ffffff` | 1 | upstream qrtr/neuron shbufs | stock FDT has no reg | **reclaim** (`stockcma`) |
| rest | 7 | AOP, cmd-db, SMEM, cpucp, IPA, GPU zap, SPSS, DFPS | | keep |
| `0xcbc00000` (mapped) | 68 | board DTS "stock span" | stock: start of the reusable `secure_display` CMA (164 MiB, ION HYP_CMA, assigned per allocation only) | **reclaim** (`stockcma`) |
| `0xedc00000` (mapped) | 288 | board DTS "stock span" | stock CMA pools, see next table | split (`ionpool`) |

The 288 MiB span is where the wrapper's kernel puts its dynamic CMA pools
(its dmesg: "created CMA memory pool at ..."):

| Range | MiB | Wrapper pool | Verdict |
|---|---:|---|---|
| `0xedc00000` | 28 | audio_cma (ION DMA heap) | **reclaim** |
| `0xef800000` | 48 | mem_dump (`msm_mem_dump` registers it with TZ as the crash dump table) | keep |
| `0xf2800000` | 16 | sp (SPSS ION **HYP_CMA** heap: assigned per allocation; SPSS never boots, but nobody has checked for assignments) | keep |
| `0xf3800000` | 100 | non_secure_display (ION DMA heap) | **reclaim** |
| `0xf9c00000` | 20 | cnss_wlan: WLAN is **ONLINE** under the wrapper, the chip may DMA there until ath11k resets it | keep |
| `0xfb000000..0xfc7fffff` | 24 | fastrpc adsp, sdsp, cdsp pools | keep |
| `0xfc800000` | 16 | user_contig | keep |
| `0xfd800000`, `0xfec00000` | 20+16 | qseecom, qseecom_ta: TZ rejected PAS metadata at `0xfe400000` (2026-07-25) | keep |

Note the 2026-07-25 evidence only proved the qseecom part of this span
secure; the other stock spans were added in the same commit without a
per-pool test. The reclaim candidates rest on CMA placement, the stock DT
and the wrapper's subsystem table: that makes them candidates, not proof.
Nobody has captured the wrapper's hypervisor assignments right before
kexec, so every part gets its own RAM trial with SEA monitoring, and pools
whose heap type assigns memory per allocation (sp, secure carve-outs) stay
reserved.

### Userspace and GPU (GNOME desktop mode + Steam, uptime 11-36 min)

| | MiB | |
|---|---:|---|
| MemAvailable | 8202 → 4960 | Steam idle → game + shader pre-compilation |
| Process PSS, GNOME session | 1426 | gnome-shell 232, gnome-software **132**, Xwayland 55, mutter-x11-frames 48, evolution-* 135 (alarm-notify 46), localsearch 54, 3 xdg-desktop-portals 73, ~20 gsd-* 7-19 each |
| Process PSS, Steam | 881 → 1610 (+1679 fossilize) | steamwebhelper 10 processes 1147, steam 463; **fossilize_replay 8 processes 1679** |
| Process PSS, system services | 341 | tailscaled 69 (Go), journald 42 (mostly mmapped journal files), udisksd 26, rog5-touchpad 20 + rog5-healthd 16 (python3) |
| **AnonHugePages** | 903 → 1291 → 1710 | THP is "madvise", yet every glibc process has huge pages |
| GPU GEM (msm, all clients) | 303 → 584 | gnome-shell 258, steamwebhelper 176, Xwayland 71, steam 24, fossilize 19 |
| KMS GEM | 115-120 | DSI + DP framebuffers (16 MiB each at 3840x1080x4, triple buffered), fbdev console |
| dma-buf | 64 | shared scan-out buffers |
| Slab | 150-304 | ext4/overlay inodes and dentries, mostly reclaimable |
| tmpfs `/run` | 79 | ADSP+Wi-Fi firmware kit 43 + 18 (the 15 MiB `adsp.mbn` duplicates the `adsp.bNN` split image Linux loads), module tree 17 |
| `/dev/shm` | 278 | Steam/CEF shared memory |
| zram | 5.2 GiB zstd, unused (pswpout 0) | vmalloc'd table 20 MiB |

Findings:

1. **glibc 2.43 madvises every malloc heap and arena for 2 MiB pages.**
   wireplumber's `[heap]` and 8 arenas carry VmFlags `hg`; a python3 test
   gives RSS 32.5 MiB with the default, 25.7 MiB with
   `GLIBC_TUNABLES=glibc.malloc.hugetlb=0` (-21 %), 34.4 MiB with `=1`. With
   `defrag=defer+madvise` those faults compact synchronously: compact_stall
   95 → 428 during the session (69 of the first 95 failed). The THP mode "madvise" set on
   2026-09-30 therefore did not stop the padding it was meant to stop.
2. `khugepaged/max_ptes_none` = 511: khugepaged collapses a 2 MiB range with
   a single page in it, and the 7.2 underused-THP shrinker never splits.
3. The SWIOTLB pool is 64 MiB and ~0 % used: every DMA master Linux drives is
   behind an SMMU. The size can only be lowered by `swiotlb=`, and the command
   line is built inside the signed slot-B loader.
4. Steam's background Vulkan shader processing runs 8 `fossilize_replay`
   workers (1.7 GiB PSS, 1.9 GiB of huge pages).
5. msm already evicts idle GEM objects to swap (`enable_eviction=Y`) and
   shmem objects use `within_size` huge pages, which suits the GPU SMMU.
   There is no GPU carve-out besides the 8 KiB zap region: "VRAM" is GEM
   objects allocated on demand.

Light performance baseline (`rog5-mem-report perf`, during shader
pre-compilation, so noisy): `true` 4.6 ms, `python3 -c pass` 31.6 ms, GTK4
import 251 ms (median of 3); first-touch anonymous faults 1133 MiB/s with
4 KiB pages vs 2484 MiB/s with MADV_HUGEPAGE.

## 2. Savings, ranked

| # | Change | Saves | Risk | Performance | State |
|---|---|---:|---|---|---|
| 1 | DT `stockcma`: free `0xcbc00000-0xd7ffffff` | 196 MiB | low-medium (stock runs CMA there) | neutral (more ZONE_DMA) | **opt-in composer**, RAM trial |
| 2 | DT `pil`: modem + camera + CVP PIL | 266 MiB | medium (stock never gives HLOS this RAM; only "never booted" evidence) | neutral | **opt-in composer**, RAM trial |
| 3 | DT `ionpool`: audio_cma + non_secure_display | 128 MiB | low-medium (stock CMA, plain ION DMA heaps in the wrapper) | neutral | **opt-in composer**, RAM trial |
| 4 | `malloc_thp=off` (glibc tunable via the service managers) | est. 250-500 MiB of session RSS; more under Steam | low (functional) | fewer compaction stalls; first-touch faults of big malloc heaps 4 KiB instead of 2 MiB | **implemented**, default in `/etc/rog5/memory` |
| 5 | SWIOTLB 64 → 4 MiB (+ dynamic growth) | 60 MiB | low | neutral | **opt-in patch + fragment**, kernel trial |
| 6 | `thp_max_ptes_none=409` + shrink_underused | under pressure: the sparse remainder of the THPs | low | keeps dense THPs | **implemented** |
| 7 | Steam: shader background threads 8 → 2 | ~1.2 GiB while it runs | none | slower pre-caching, cooler phone | recommendation (Steam setting / `steam_dev.cfg unShaderBackgroundProcessingThreads 2`) |
| 8 | gnome-software resident in GNOME | 132 MiB | low | none | recommendation: drop the package (pacman has no backend; its unit is D-Bus activatable, masking would break its launcher) |
| 9 | evolution-alarm-notify, localsearch-3 | 46 + 54 MiB | low (no reminders / slow Files search) | indexer stops eating CPU | **implemented as opt-in** (`mask_user_units`) |
| 10 | `watermark_boost_factor=0` | page cache kept after fragmentation events | low | less kswapd churn | **implemented** |
| 11 | `/run` firmware kit: drop `adsp.mbn`; zstd firmware/modules | 15 + ~40 MiB | low, but boot-chain change | none | plan (initramfs) |
| 12 | Free the splash region after the DPU takes over | 35 MiB | medium (kernel patch, map + free_reserved_area) | none | plan |
| 13 | tailscaled `GOGC`/`GOMEMLIMIT` | ~20-30 MiB | low | more GC CPU | plan |
| 14 | `anon_mthp_64k=always` (contiguous PTEs) | costs a little | low | fewer faults, fewer TLB misses | **implemented as opt-in**, A/B first |
| - | Not worth it: gsd-* daemons (Phosh/GNOME RequiredComponents), CMA 32 MiB (reusable), fbdev console (~10 MiB, loses the panel console), NR_CPUS/VA_BITS/KALLSYMS (<5 MiB), zram size (already 50 %, zstd) | | | | |

Totals: DT + SWIOTLB **650 MiB of MemTotal** (10611 → ~11261 MiB, +6.1 %),
plus 250-500 MiB of session RSS from the malloc change, without changing
what runs.

## 3. What is implemented (branch agent/memory-footprint-20261001, not installed)

- `configs/rog5/memory` → `/etc/rog5/memory`, `scripts/device/rog5-memory-tune`
  (`status|apply|revert`), `configs/systemd/rog5-memory-tune.service`
  (enabled; `After=` the existing sysctl/tmpfiles memory settings). `apply`
  writes `khugepaged/max_ptes_none`, `shrink_underused`,
  `vm.watermark_boost_factor`, the 64 KiB mTHP choice, the
  `GLIBC_TUNABLES=glibc.malloc.hugetlb=0` drop-ins in
  `/etc/systemd/{system,user}.conf.d/60-rog5-malloc-thp.conf` (effective from
  the next boot; removed again only if it wrote them) and the user-unit masks
  (recorded, so only its own are removed; Settings Daemon, Shell, Phosh and
  gnome-software are refused). `revert` restores kernel defaults. Registered
  in `configs/rootfs/userspace.tsv`. A same-named drop-in it did not write is
  never overwritten or removed (exit 1); every write is checked. User-unit
  masks take effect at the next login. Tests:
  `scripts/device/test-rog5-memory-tune.py` (9).
- `scripts/device/compose-memslim-dtb.sh BASE OUT stockcma|pil|ionpool[,...]`:
  pinned to d10 (sha256 `dda8b280...`), deletes the two phandle-less mapped
  spans it replaces, sets `status = "disabled"` on the others (phandles stay
  valid; Linux skips unavailable reserved-memory nodes; the loader's
  verifier still counts their `reg` in its overlap check), refuses if the
  modem remoteproc is enabled or any other `memory-region` user exists,
  re-checks every kept reservation (memx, memshare, removed_mem, CDSP
  secure heap, ramoops, splash, PILs in use) and that nothing outside
  `/reserved-memory` changed. Markers `/rog5,memslim`, `/rog5,memslim-base`.
  On the real d10, all four outputs pass the loader's `verify_fdt`:

  | parts | SHA-256 |
  |---|---|
  | stockcma | 57091d95fa248635889344a2442d2683e768f69a563552d64d4b99ec40d876de |
  | pil | 0e92f5eac56623a3cec50e125d6f51c7f8f684c00566e8ab98731952ab51a314 |
  | ionpool | 292266c136b6f644d4dfc19b54d92c657e8cc0d7117d1528e3251fcff03ee978 |
  | stockcma,pil,ionpool | 40eba9a9f13634dbcc23befc52427ab90acda55ba088d5f752084ed2ad1782f4 |

  Tests: `scripts/device/test-memslim-dtb.py` (synthetic tree + refusals; the
  real d10 and the loader check as declared optional subchecks).
- `patches/opt-in/memory/0001-dma-swiotlb-default-pool-size-from-Kconfig.patch`
  (`CONFIG_SWIOTLB_DEFAULT_SIZE_MB`, default 64 = unchanged) and
  `configs/kernel/rog5-memory-slim.fragment` (4 MiB + `SWIOTLB_DYNAMIC`).
  Not in `series.production` or the build JSON. Applies to the r111 tree
  (`patch --dry-run`); not compiled yet.
- `scripts/device/rog5-mem-report`: `snapshot` (everything in section 1, with
  `--ranges` showing how much of a physical range is free/reserved/in use),
  `compare`, `perf` (start-up times, fault throughput with and without THP,
  the GLIBC_TUNABLES the session really has) and `pressure --yes` (stepwise
  compressible allocation into zram, re-touch timing, PSI/zram/fault deltas;
  with `--ranges` it writes and verifies every test page that landed in a
  reclaimed range and executes a RET on up to N of them per range, with a
  pass/inconclusive/fail verdict per range). The whole probe runs in a child
  process: a user-mode SEA on a secure-owned page ends the child and is
  reported; a fault in kernel context or an SError can still crash the
  phone, which is what the RAM trial accepts. Tests:
  `scripts/device/test-rog5-mem-report.py` (10; a FIFO in place of
  `dri/1/DP-1` hangs the test if the tool ever opens it).

## 4. Trial plan

Userspace (one install, one reboot, no RAM trial needed):

1. Same scenario before and after: boot, 10 min idle Phosh → `rog5-mem-report
   snapshot --label phosh-idle`; Desktop mode, 10 min idle →
   `--label gnome-idle`; Steam started, idle 5 min → `--label gnome-steam`.
   Then `perf --label ...` (panel on, performance mode off).
2. `rog5-install-userspace`, then `rog5-memory-tune apply` once (the drop-ins
   must exist before PID 1 and the user manager start, so the service that
   writes them at boot only helps from the second boot on), reboot,
   `rog5-memory-tune status` (drop-in present, max_ptes_none 409), `perf`
   shows `GLIBC_TUNABLES` on gnome-shell/phoc/steam; repeat 1 and `compare`.
3. Performance gates: GB6 Vulkan in performance mode within run-to-run noise
   of 5405 (3 runs each); startup medians within 5 %; a FEX/Proton game: load
   time to menu (stopwatch) and `pressure --yes --target-mib 6144` with the
   game in the background: retouch MiB/s and PSI full not worse. A run only
   counts for zram if it reports `zram_exercised: true` (pages went out and
   came back); otherwise raise `--target-mib` or lower `--floor-mib`.
   If a game is slower, it can opt back in with `GLIBC_TUNABLES=glibc.malloc.hugetlb=1 %command%`.

DT parts (one RAM trial each through `production-ram-trial.py`, d10 +
k111 otherwise unchanged, order `stockcma` → `ionpool` → `pil`):

1. Boot reaches multi-user, all remoteprocs (ADSP, SLPI) `running`, GPU zap
   loaded, Wi-Fi associated, audio and sensors work, DP desktop mode starts;
   dmesg `Memory:` reserved down by the part's size, MemTotal up by it; no
   `qcom_scm`/PAS error (the 2026-07 failure mode: PAS metadata allocated in
   a secure range returns -EINVAL).
2. `rog5-mem-report snapshot --ranges <part's ranges>`: the ranges show
   buddy/in-use pages, not reserved.
3. `rog5-mem-report pressure --yes --ranges <...> --exec-sample 256` (the
   budget is per range) until every range reports `pass` (hits, executed
   pages, no write mismatch); `inconclusive` means repeat with more memory,
   `fail` or a killed probe (exit 1) ends the trial; no rog5-sea / SError /
   external-abort lines; then a GNOME + Steam + game session with
   `journalctl -k -f | grep -E 'rog5-sea|SError|abort'` running.
4. Three s2idle cycles and a Wi-Fi restart (TZ/hyp and WLAN transitions),
   then `snapshot` again.
5. Pass: no SEA/SError/panic, every check of 1 green, the pressure hits in
   every freed range. Then compose-production-dtb.sh gets a `memslim`
   feature, a DTB dN+1 and the normal install path (two committed boots).

SWIOTLB: a trial kernel (series.production + the opt-in patch, fragment
appended): dmesg `software IO TLB: mapped ... (4MB)`; after USB storage,
USB Ethernet behind a hub, USB audio, Wi-Fi iperf, DP and a game:
`io_tlb_used_hiwater` and no "swiotlb buffer is full" / DMA mapping errors.

Not covered: idle Phosh numbers (the phone was in desktop mode), the actual
gain of the malloc change per process (needs the reboot), and any phone
evidence for the DT parts and the SWIOTLB patch (they have none yet).

## 5. Review (GPT-6.1-Sol, read-only)

Eleven findings, all addressed before commit:
- reclaim evidence overstated, `sp` is a per-allocation HYP_CMA heap →
  claims qualified (candidates, RAM trial decides), `sp` kept reserved
  (ionpool 144 → 128 MiB);
- data probes ran in the parent, so a data-abort SIGBUS would kill the
  reporter → the whole pressure probe runs in a supervised child;
- one global exec budget could leave a range untested → budget and
  pass/inconclusive/fail verdict per range, exit 1 on fail;
- PFN could change during the exec test → checked again after the call
  (`moved-after`); child exceptions were silent → `error (exit N)`,
  `not run`, a deadline;
- drop-in write failures were masked inside `$(...)`, and `apply` replaced a
  foreign drop-in → every step checked, foreign files left alone (exit 1);
- first install needs `apply` before the reboot; masks need a new login →
  documented and printed;
- pressure could finish without touching zram → `zram_exercised`;
- watermark-boost wording → described as a cache/fragmentation trade-off.

The phone stopped answering on 192.168.1.83 after the snapshots, so the
aarch64 exec self-test (`test_exec_pages_native`, root on the phone) has not
run yet.

## 6. RAM trials on the phone (2026-10-01 15:50-17:35, kernel k112)

Cumulative, in plan order, each part installed as a try-once main bundle
(fallback `safe-k111-d10-261001a`, d10, untouched). Phone on USB power
through the hub, idle, no monitor.

| Trial | Bundle | DTB | MemTotal kB | vs d10 |
|---|---|---|---:|---:|
| baseline | `main-k112-d10-261001b` | d10 | 10866028 | |
| A stockcma | `main-k112-d11-261001a` | d11 `57091d95` | 11066476 | +196 MiB |
| B + ionpool | `main-k112-d12-261001a` | d12 `363c4cd8` | 11197548 | +324 MiB |
| C + pil | `main-k112-d13-261001a` | d13 `1d690d39` | 11469392 | +590 MiB |

Every trial: committed healthy on the first boot, ADSP and SLPI `running`,
GPU up (`msm.gpu_inits_ok`), Wi-Fi associated, both amps' speaker protection
running, no `rog5-sea`/SError/external-abort/qcom_scm/PAS line; then
`pressure --yes --ranges <all freed ranges so far> --exec-sample 256`, three
`rtcwake -m freeze -s 20` cycles and a Wi-Fi off/on, then the error check
again (0 each time).

Pressure, last run (d13, `--target-mib 11800 --floor-mib 256 --step-mib 128`,
9728 MiB allocated, `zram_exercised: true`, no write mismatch, no SEA):

| Range | Pages | Hits | Exec | Verdict |
|---|---:|---:|---|---|
| `0x85200000-0x856fffff` camera | 1280 | 1280 | 256/256 ok | pass |
| `0x85c00000-0x860fffff` cvp | 1280 | 1280 | 256/256 ok | pass |
| `0x8b800000-0x9b7fffff` modem | 65536 | 63488 | 256/256 ok | pass |
| `0xcbc00000-0xd7ffffff` stockcma | 50176 | 50176 | 256/256 ok | pass |
| `0xedc00000-0xef7fffff` audio_cma | 7168 | 5547 | 256/256 ok | pass |
| `0xf3800000-0xf9bfffff` non_secure_display | 25600 | 1046 | 256/256 ok | pass |

Notes:
- The freed ranges are all below 4 GiB, so they land in ZONE_DMA, which
  user allocations only reach once ZONE_Normal is at its low watermark. The
  default `--target-mib 8192` never got there (trial A's first run: 0 hits,
  `inconclusive`); fill to `--floor-mib 256` instead.
- The kernel now places the 64 MiB SWIOTLB pool in the freed
  non_secure_display range (16384 `reserved` pages there), so device DMA
  bounces through reclaimed memory as well.
- `monitor-sensor` on d13: accelerometer, light, proximity, compass.
- Second committed boot of d13 at 17:35: same checks, 0 errors.
- Not covered: DP desktop mode (no monitor attached during the trials), a
  long game session with the SEA watch, and unplugged standby.

Result: d13 (all three parts) is the default main DTB from 2026-10-01 17:35.
The fallback stays on d10.

## 7. SWIOTLB trial, kernel k113 (2026-10-01 18:30-19:10)

`main-k113-d13-261001a` = k112 + 0153 (`CONFIG_SWIOTLB_DEFAULT_SIZE_MB=4`,
`SWIOTLB_DYNAMIC=y`, `rog5-swiotlb-slim.fragment`) on d13. dmesg
`software IO TLB: mapped [mem 0xf7800000-0xf7c00000] (4MB)`; MemTotal
11531552 kB (+60 MiB over k112/d13, +650 MiB over k112/d10). Committed
healthy; ADSP/SLPI running, speaker protection running.

Load: 400 MiB over Wi-Fi each way (checksum matched), twice; pressure to
256 MiB free; 15 s2idle cycles; two Wi-Fi off/on. `io_tlb_used_hiwater` 4
slabs at most, `io_tlb_transient_nslabs` 0 (no dynamic pool was needed), no
"swiotlb buffer is full" or DMA mapping error.

One failure, not reproduced: in the first 3-cycle run the WCN6855 firmware
crashed on the second resume (`PCIe Bus Error: Correctable, RxErr`, then
`firmware crashed: MHI_CB_EE_RDDM`, WMI timeouts, `cannot restart radio 0`,
later `failed to process regulatory info -22`); wlan0 stayed down until a
reboot (the phone itself was fine and reachable over USB). The bounce pool
was idle (hiwater 4 slabs), the crash started at the PCIe link, and the same
sequence passed 9 times on k112 (d11-d13) and 9 more times on k113 after
the reboot, including the exact bulk-transfer + 3 cycles + radio toggle
order. Classed as a sporadic WCN6855 resume crash, not a SWIOTLB effect.
Gap: ath11k does not recover from RDDM here; Wi-Fi needs a reboot. dmesg in
`~/.local/state/rog5-production-boot-20260923/evidence-k113-wifi-crash/`.

Not covered: USB storage, USB audio and Ethernet behind the hub, DP and a
game on k113 (SWIOTLB_DYNAMIC adds pools if a device ever needs more).
k113 stays the default; the fallback (k111/d10) keeps the 64 MiB pool.
