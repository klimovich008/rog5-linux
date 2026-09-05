# Power/USB v14 incident: module isolation was applied after coldplug

ID/date: power-usb-v14 / 2026-08-21
Earliest failed stage: candidate-module absence gate, before explicit ADSP startup.
Observed evidence: runtime/SSH, accepted-DT geometry, armed rollback, and post-SSH unit masking passed; `qcom_q6v5_pas` was already loaded by earlier systemd coldplug. Exact fallback passed.
Root cause: proven R6 mutable target-state ordering defect. Runtime masks were correct but applied after the services they were meant to suppress.
Was the candidate consumed?: yes. Phone storage modified: no.
Regression: V15 creates both runtime masks in initramfs `/run` before switch-root; clean probe refusals retain NFS for a bounded 20-second reboot grace.
Successor: V15; kernel, DTB, firmware, recovery, and charging protocol are unchanged.
