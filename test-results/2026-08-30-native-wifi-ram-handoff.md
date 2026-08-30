# Native Wi-Fi RAM handoff checkpoint

Primary question: can the stock-derived WCN6855 DTB and exact V11 modules expose
a working radio while preserving UFS, charging and USB rescue?

The kernel/module/firmware checkpoint remains unchanged. No Wi-Fi execution or
radio activation has occurred at this checkpoint. V11 is still running.

## Minimal handoff correction

The installed standalone exitramfs always normal-rebooted, including when
systemd requested kexec. This R3 capability mismatch would prevent a native
RAM trial. The exitramfs now dispatches one syscall-only static executor only
for the kexec verb, clean storage teardown and a verified RAM-staged executor.
Missing/changed tools, incomplete teardown or any returned syscall fall through
to normal reboot. Ordinary V11 shutdown remains unchanged.

`load-native-ram-bundle.sh` checks source boot/kernel/model, safe power, exact
tools/libraries/trust, the signed target and all 117 UFS nodes read-only before
loading once and requesting normal systemd kexec shutdown. The existing exact
record consumer permanently consumes the trial before that request. The target
bundle keeps V11's unchanged initramfs/rollback; neither p24's selector nor a
boot partition is changed. The new helper is staged only in `/run/initramfs`.

## Offline and connected evidence

- Existing Wi-Fi commit `f1c432a` passed exact-head, merge, QEMU and publication
  CI in GitHub run `33308991547`.
- Two independent static executor builds are identical. No ELF interpreter is
  present; an unprivileged QEMU invocation returns failure, never success.
- Dispatch fixtures cover reboot/kexec, clean/unclean teardown, missing and
  symlinked files, wrong checksums and both zero/nonzero executor returns.
- Full-system QEMU loaded and executed the exact V11 kernel a second time with
  the verified kexec tools and new static syscall helper. It reached the unique
  target marker. No disk or network device was attached. This is not physical
  Qualcomm kexec or Wi-Fi acceptance.
- Connected non-consuming preflight passed on the still-running V11 phone.
  The native root lacked the verifier's public key; the exact public key was
  staged into its volatile overlay, not persistent storage.
- CI exposed an R1 fixture mismatch: runtime tests used current program bytes
  against historical process identities. Refreshing that historical pin was
  rejected by its own admission chain. The historical identities are now left
  unchanged; offline fixtures consistently bind their current test programs.
  The fast tier runs this regression first. New native RAM claims are read from
  the one canonical registry instead of copied into another historical list.

## Live prerequisites and limitations

Before entry, require successful current-head CI, pinned SSH and continuous
source boot/topology identity, signed deployed bytes and durable one-use entry.
Stop persistent state, prove all 117 UFS nodes read-only, then execute once.
Never retry an ambiguous handoff. After SSH returns, stop state again before
loading Wi-Fi modules and arm a separate bounded radio-test rollback.

The target's existing initramfs rollback is userspace, not a hardware watchdog;
it cannot resolve a kernel hard lock. Keep USB observation and the verified
persistent V11/ASUS slot-A rescue. Hardware kexec, shared-rail tolerance, PCIe,
firmware/BDF selection, association and Wi-Fi SSH remain unproven.
