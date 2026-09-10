# Generation 159 result and V51 offline correction

- Generation 159 is consumed. Target NCM appeared, but no stage arrived before
  exact slot-A stock recovery returned. No storage write ran.
- Classification: R2, deployed composition. The `ae717` target config builds
  `CONFIG_NVMEM_SPMI_SDAM` and `CONFIG_NVMEM_REBOOT_MODE` as modules, while the
  V50 initramfs packaged neither module before `wait_for_reboot_mode()`.
- V51 adds only the two exact `7.1.4-gae717d919f87` modules, loaded in dependency
  order before the existing reboot-mode wait. Kernel, DTB, local image, read-only
  mount policy, charging stack, transport, and wrapper kernel remain unchanged.
- Clean module twins matched. Clean target-initramfs twins matched at SHA-256
  `d2810bc803e262ea0628913d9db18d5615dead8f4b84e2e72ddfa0773d536c81`.
- Focused checkpoint passed in 11.7 seconds. Full local `ci` passed once in
  456.377 seconds. Exact-head, merge-compat, QEMU, and candidate-publication CI
  passed for `b5816d5f86a647020289b8f13c07f44fa5059fbd`. V51 is admitted once.

## Generation 160 live result

- Recovery transfer, verification, PREPARE, COMMIT, and kexec handoff passed.
- Host kernel evidence proves `ROG5 persistent root` NCM enumerated at 15:17:28
  and remained present for 23 seconds. The runner incorrectly selected
  `ROG5 local image stage`, so target networking and stage reception never ran.
- Classification: R7 host-only identity selector. The target did execute, so
  Generation 160 remains irreversibly consumed.
- No target storage write ran. Exact slot-A fastboot fallback and host cleanup
  passed; battery remained healthy.
- The host selector now derives the identity used by the sealed persistent-root
  gadget. Existing stage reporting is moved before the reboot-mode module gate
  so the next fresh identity either continues or returns the exact early target
  failure.
