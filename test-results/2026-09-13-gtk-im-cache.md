# GTK Wayland input-method cache — 2026-09-13

The extracted GTK3 package included its Wayland input-method module but not
`immodules.cache`: package extraction had not run the shipped
`gtk-query-immodules-3.0.hook`. In the prior qualified authenticated VM,
Mousepad advertised the compositor's v3 global but never bound text-input;
Foot bound it and submitted caret rectangles. The retained unpanned editor
capture and shell source already established the automatic-visibility defect,
so another unchanged VM was not needed to rediscover it.

The new preparation runs the packaged query tool with a10-second deadline and
128KiB limits on each output file. It validates the Wayland module/context stanza,
rejects query errors or stderr, and publishes a readable RAM cache without
replacing an existing path. `GTK_IM_MODULE_FILE` joins the existing explicit
schema/MIME environment allowlist for direct and activated clients; each of the
three user-manager values must match exactly once. The combined runner freezes
and stages the helper. No package, kernel, native Denial or shell AOT was rebuilt.
No phone session or installed root was changed.

A cache interruption regression initially failed because foreground timeout
owned a separate process group while the shell deferred its trap. The helper now
waits interruptibly and its cleanup signals/reaps that timeout, retaining kill
escalation and original status. Independent review found another concrete race:
plain `ln` could create a nested file if its destination became a directory.
Two query-seam regressions fail before and pass with `ln -T`, including a symlink
to a directory. This final correction followed the completed VM; its source is
qualified by host tests and was not rerun physically or in a second VM.

The starting repository commit was69252f790ee7f20a19866050c09914bebc3bc1ea,
tree126556ebea267fc94e7169b51fe196527ae932a8.
The VM ran frozen source aab9139271d06f039d8d2b91f14c94195fdef7d6,
tree7b38dc2e05ddd80928f9012b36e0499a6ef162e5.
Final executable source and integrated-tier identities are in the qualification
JSON. Later documentation commits do not identify the VM-producing source.

The real packaged ARM64 query completed0 in0.259s, listing the Wayland module
from GTK3.24.52. A separate display-free dynamic GTK consumer experiment was
inconclusive: both cache arms encountered GTK/GObject initialization failures;
no default-module or client success is inferred from it. Its logs and sources
remain private. The primary GTK implementation also distinguishes module
registration, backend matching and context selection:
[GTK3.24.52 input-method module implementation](https://github.com/GNOME/gtk/blob/3.24.52/gtk/gtkimmodule.c).
The actual VM below establishes the client result.

One authenticated ARM64 VirGL VM passed in288.405s wrapper /288.333s runner;
the VM step took274.818s under its unchanged300s bound. Actual GTK cache generation
and environment transfer passed. The service start returned0 across an18.108s
monotonic bracket under the unchanged25s limit. Early periodic startup snapshots
were observations of a live process, not failure or authority to restart it.

Mousepad now binds `zwp_text_input_manager_v3`, obtains a text-input object,
enables it and publishes10 caret-rectangle requests. Distinct rectangles include
(29,90,0,20) through(65,90,0,20). Zero caret width is legitimate; do not discard
this rectangle merely because a generic rectangle `isEmpty` predicate is true.
The prior matching-runtime log contains zero Mousepad rectangle requests.
Source-local rectangles still need careful content/coordinate conversion before
controlling the shell viewport.

Both launcher app starts, app switching, exact OSK events, and original-resolution
captures showing test/tes/test passed. Both clients exited0 normally. Denial
reported207raster frames and207page flips, with no recorded rendering errors.
The exact completion handshake, authenticated PAM/logind session and scope
cleanup, final filesystem unmount and normal VM poweroff passed. This still uses
the retained manual viewport pan. Automatic caret positioning, settled keyboard
close geometry, startup reliability and phone hardware remain unqualified.

The next concrete source change is optional focused-caret transport through the
existing native text-input state and bridge, followed by one shared visibility
calculation for paint and native hit testing. Include geometry in event dedup;
carry owning surface/window and activation identity, preserve missing geometry,
and clear stale ownership on focus/lock/destruction. Do not reuse the existing
IME-global helper unchanged: it substitutes a default rectangle when absent and
depends on active IME state. Keep the manual fallback for unsupported clients.
Now Mousepad can provide real caret input to exercise this work.

No phone/USB/SSH, protected-storage mutation, signing, admission, claim or new
phone candidate operation occurred. All physical mobile rows remain NOT RUN;
headless S06/R01 remain FAIL. Prior525 artifact sets and historical failures are
preserved; the new set is an offline fixture with authority none. Existing signed,
accepted and previously qualified session pointers retain their exact identities.
The long-term goal remains active and requires real-phone acceptance.

Final validation:15 cache helper tests PASS (see exact time below),55 runner
fixtures PASS11.714s. Environment regression failed7 assertions against the
previous source; two publication-directory races failed before correction.
The final active tier:102PASS,0FAIL/BLOCKED/SKIPPED suites,255NOT_SELECTED,
with three declared optional subchecks SKIPPED;150.154s,532.3MiB peak, no swap.
No new GitHub CI execution is claimed.

Final helper regression elapsed0.683s.
Host-tested source `05ce1d6f66d3fa5b72ce0efebfe7a1edcc08cea3`, tree `a955546293dc7ba99e9056fa3366928f0f982e46`.

[Exact commands, test/build durations, source/artifact hashes and evidence](2026-09-13-gtk-im-cache-qualification.json).

Final metadata:5 checker tests PASS0.857s;8 status tests PASS0.018s.
Inventory, generated status and whitespace checks PASS.30 unchanged VM inputs
were streaming-hash verified; final helper differs only by the separately tested
publication guard. Host disk retained at least3GiB; final free3,287,511,040bytes.

Changed files for this follow-up:

- `configs/project-status.json`
- `configs/repository-tests.json`
- `docs/current-state.md`
- `docs/development-lessons.md`
- `docs/development.md`
- `manifests/artifact-sets.json`
- `manifests/current-artifact.json`
- `scripts/host/test-logind-gtk-im-cache.py`
- `scripts/host/test-qemu-logind-runner.py`
- `scripts/host/test-qemu-logind.py`
- `scripts/host/test-repository-linux.sh`
- `test-results/2026-09-13-gtk-im-cache-qualification.json`
- `test-results/2026-09-13-gtk-im-cache.md`
- `tools/qemu-virtio-drm/logind-denial-prepare.sh`
- `tools/qemu-virtio-drm/logind-denial.sh`
- `tools/qemu-virtio-drm/logind-gtk-im-cache.sh`
