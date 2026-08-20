# Power/USB v7 incident: target selector omitted the canonical candidate

ID/date: power-usb-v7 / 2026-08-20
Primary question of the cycle: Can the side-port candidate expose UCSI and charging telemetry while NCM remains active?
Earliest failed stage: target dispatch after accepted systemd/key-only-SSH runtime and before charging-probe entry.
Observed evidence: recovery, bundle transfer, PREPARE/COMMIT, exact NCM, NFSv4.2, OverlayFS, systemd, 29-zone runtime acceptance, key-only SSH, watchdog fallback, stock slot-A return, intent resolution, and host cleanup passed. No charging-probe record or progress stage was produced.
Root cause: proven R1 target identity propagation defect. `network-root-init` selected charging mode only for three historical `headless-full-ucsi-charging-early-*` literals; the canonical `headless-power-usb-observer-v7` identity followed the normal systemd path.
Was the candidate consumed?: yes; COMMIT was claimed and target execution was proven.
Was phone storage modified?: no.
Why existing host tests missed it: canonical closure covered host runners and generated policy but not the target initramfs selector.
New regression fixture/test: the generator emits the active target identity, the initramfs embeds that exact generated file, and a normal non-diagnostic command line for the active identity must select charging mode.
Systemic prevention change: one canonical manifest now controls the target selector as well as host candidate, policy, Python, shell, and lock outputs.
Successor prerequisites: rebuild only the changed target initramfs, preserve Image/DTB and recovery raw bytes, sign a fresh bundle, issue a fresh AVB generation, and pass exact composition checks before one v8 cycle.
