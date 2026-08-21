# Power/USB v18 incident: deployed PDR module BTF was rejected

ID/date: power-usb-v18 / 2026-08-21
Primary question: does candidate-independent probe retention reach ADSP and PMIC/UCSI?
Earliest failed stage: `pdr_interface.ko` insertion after ADSP reached `running`.
Observed evidence: NCM/NFS, systemd, strict SSH, runtime acceptance, PAS authentication, ADSP handover, and fallback passed. Kernel logged `failed to validate module [pdr_interface] BTF: -22`.
Root cause: proven R2 deployed-composition mismatch. The sealed root carried a build-specific PDR `.BTF` section that the exact running kernel rejected. Module code, name, dependency, and vermagic remain correct.
Was the candidate consumed?: yes. Phone storage modified: no.
Regression: V19 retains one exact PDR module whose only removed section is `.BTF`; `.text` is byte-identical, name/dependency/vermagic are pinned, the initramfs verifier requires BTF absence, and the probe inserts it only after `qcom_pdr_msg` is loaded through the existing mapper dependency.
Successor: V19 changes only target initramfs/probe composition. Kernel, DTB, firmware, recovery, and all other modules are unchanged.
