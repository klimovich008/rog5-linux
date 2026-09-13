# Native Wayland editor and OSK VM qualification — 2026-09-13

**Native Mousepad startup and exact OSK key delivery pass in the ARM64 VirGL
VM. Visible text editing fails:** after revealing the OSK, the application area
becomes white and the expected `test` / `tes` / restored `test` cannot be seen.
The initial capture does show the correct Mousepad window. The final guest
records114 raster frames/page flips without reported rendering errors. A key
protocol PASS is not a visible editing PASS, and neither is phone evidence.

The supplied framebuffer review at `410b6935526a977ca727359f23ee43fc4ebe45b2`
was rechecked against current patch0001: strict explicit intersection,
Invalid-only pool dispatch and stored/exported descriptor validation are already
present. Their later qualified binaries are reused unchanged. This turn fixes
VM runtime preparation and test observation; it does not change the renderer,
engine, AOT shell, package closure, generic kernel or phone artifacts.

## Identities and results

Starting commit: `dfdbf39d212bc0c6dedb6a004d0b928673a0651d`;
tree: `03e5189898a1197f2e7dd5a5235a8749197688ba`.
Final executed source: `d50b19fbebb0369fe9fe4baf72a71a77c2e237af`;
tree: `17ca575d82d96cd935d7a8264a3a7eef54c564d6`.
The subsequent evidence commit is distinct from these executed source bytes.

Native binary SHA256:
`878ff4c6155279264782523837cf7672273f333a9a45318a7db9cc9fbf7ce19a`,
built from source `02796f069819b9df2ad11013f69ce3d1ddf39362`.
Engine SHA256:
`a75c88d8f12d9ec7a24bb107ff9dc0349b6bb2d5b0f18cb4d40b9e54227e9418`,
source `66db5ff08065972bf9cf7e3d2c4b845633170052`.
Generic VM Image SHA256:
`34279d12dee925c4c58de9f49411c5e5f9fe85d016214e3939f80cd2f8b797f9`.
Installed phone bytes were not queried or changed.

The [qualification JSON](2026-09-13-mobile-vm-editor-qualification.json) records
all three exact VM commands, source commits, durations, input/output hashes,
all88 integrated suite commands/results, cache source identities and visual
findings. SHA256:
`e3f0a0fa9b73f5f943a35a90a2c6f36b97bcbec86168d0c0c51dc39cd2ead417`.
Raw logs, PNGs and intermediate failed tests remain in private state
`/home/deck/.local/state/rog5-vm-editor-input-20260913-r1`.

| Executed check | Result | Seconds |
| --- | --- | ---: |
| R1, source064f7bb6: unprepared GTK runtime | FAIL: no editor;66 frames/flips | 66.972 |
| R2, sourcece85952a: RAM caches, strict readiness | FAIL: observed full-path title refused; no input;30 frames/flips | 72.901 |
| R3, sourced50b19fb: observed title and retained buffer semantics | Protocol/capture PASS; visual text FAIL;114 frames/flips | 103.088 |
| Observer transport/input/cleanup focused tests, Python -O | 40 PASS | 1.245 unittest /1.368 wall |
| Prerequisite/protocol/cache focused tests, Python -O | 22 PASS | 0.085 unittest /0.198 wall |
| Replay real R2 log with corrected parser | Mapping/readiness observed; key result remains FAIL | 0.020 |
| Frozen active tier | 88 PASS;0 FAIL/BLOCKED/SKIPPED;255 NOT_SELECTED | 128.453 |

Three declared optional subchecks are SKIPPED, separately from suite counts.
The active tier used two workers,1GiB memory/no swap,600-second deadline and
349.6MiB peak. No prior CI or build result is represented as freshly executed.
The final VM kept network disabled, read-only runtime/payload, only the host
render node exposed,1536MiB/no swap,2 CPUs,64 processes,8MiB serial limit and
120-second outer deadline. The editor mode reserves90 seconds for Denial and95
for its owned Mousepad timeout; the default locked probe remains45 seconds.
All three VM containers were removed. No phone operation occurred.

After the evidence update, five metadata-checker tests pass in0.946 seconds
and eight status tests in0.083 seconds (wall time). Inventory validation takes
0.094 seconds and generated status validation0.040 seconds; diff whitespace
checks pass. Exact commands/timings are retained in `metadata-result.json`.
Streaming comparison verified99 redundant payload files against durable originals
before reclaiming180,278,691 bytes. `duplicate-payload-retention.json` records
every source, destination and hash needed to restore them. Unique logs, captures,
initramfs bytes and recovery inputs remain retained.

## Demonstrated failures and fixes

R1 had package XML and loaders but no generated GSettings or MIME databases.
Schema-dependent activated services crashed. GdkPixbuf could not select the
installed SVG decoder. The retained library imports GLib content-type queries;
the matching [GdkPixbuf source](https://github.com/GNOME/gdk-pixbuf/blob/2.44.6/gdk-pixbuf/gdk-pixbuf-io.c)
explains that MIME lookup boundary. R2 generated both caches in guest RAM before
D-Bus, kept authenticated `/usr` read-only, and opened the native editor without
those errors. Both cache hashes are recorded in serial evidence. No image
loader replacement, sandbox bypass or package download was required.

The original readiness gate accepted compositor presentation even without an
application. R1's alleged empty-editor capture was actually the shell's
`Loading...` screen. The new parser consumes a bounded, Mousepad-only prefixed
protocol stream, links surface/toplevel identities, requires configure/ack and
a buffer commit, and waits for later presentation. Missing or unrelated window
proof cannot start the pointer sequence. R2 exposed the exact title
`/tmp/rog5-text-probe.txt - Mousepad`; replay now maps at61.097 seconds and
becomes ready at62.582 seconds, without retroactively claiming key delivery.

An executable counterexample also caught treating an attachment-free commit
after configure as an unmap. The parser now distinguishes absent pending
attachment from explicit NULL, preserving existing buffer contents across empty
commits. Destruction/unmapping revokes readiness; completed focused key evidence
survives cleanup. Tests reject unfocused/extra/wrong key events, false titles,
stream truncation/overflow, cache command failures and empty generated output.
Before-fix failures and the intermediate failed parser test are retained.

The fixed pointer sequence opens the OSK, presses t/e/s/t, backspace and t.
R3 records exact down/up pairs for evdev20,18,31,20,14,20 on the focused native
surface. The modified window title supports that editing began. All five PNGs
were inspected: the initial empty editor is visible, the OSK appears, but every
expected text checkpoint is white. The qualification therefore remains FAIL
for visible editing even though the harness's narrower protocol result passes.

## Changed files and limits

Source/test changes:

- `scripts/host/qemu-mobile-observer.py`
- `scripts/host/test-qemu-mobile-observer.py`
- `scripts/host/test-qemu-virtio-drm.py`
- `scripts/host/test-qemu-virtio-drm-prerequisites.py`
- `tools/qemu-virtio-drm/guest.sh`
- `docs/development.md`
- `docs/development-lessons.md`

Evidence/status changes: this report and its qualification JSON,
`configs/project-status.json`, the generated header in `docs/current-state.md`,
`manifests/artifact-sets.json` and `manifests/current-artifact.json`. Historical
body text and all496 prior artifact-set entries remain unchanged. The additional
set is an offline fixture with no admission authority.

Mousepad's optional shortcuts/spellcheck libraries are absent. Document portal,
RealtimeKit and PipeWire warnings remain; those services are not qualified.
The guest runs as root for this isolated fixture, which does not qualify the
non-root mobile privilege model. Launcher activation, app switching,
authentication, phone OLED/touch/A660, suspend/wake and charging remain NOT RUN.
S06 and R01 remain FAIL. No signing, candidate creation, claim operation,
phone contact or protected-storage mutation occurred.

The next smallest authorized experiment is a paired compositor-output screencopy
and VNC capture for the same native window. The client uses SHM buffers and its
settled geometry stays unchanged through typing; the current evidence does not
support an OSK-induced client resize or establish whether the white output first
appears in composition or capture. Compare those boundaries before changing the
renderer or repeating a large build. No additional VM experiment was executed.
