# Network-root v1 live result

Status: **PASS twice in systemd diagnostic mode; normal coldplug remains
blocked**. Arch Linux ARM runs natively as PID 1 on Linux 7.1.4 with a
read-only PC-backed root and no phone storage visible. Nothing was flashed.

## Candidate and reproducibility

- Temporary-boot AVB SHA-256:
  `4b5a93337753a02548731a62d1746fa97c85c920342c8c6e2eaca28b93a1fd6b`
- Raw boot image SHA-256:
  `3849f98ffdccd19f719d688044aef9072b00f171aa690093302b1844a13905d8`
- ASUS wrapper Image SHA-256:
  `5b6d8b7566bb409aef246fcd997b9044ea04105464f9ebb08cb8e8cb6b87f845`
- Embedded staging initramfs SHA-256:
  `14d4275a3626dbc2c73e66b34566b8616239238c8dc4da7ea8a0dfe420f93616`
- Target kernel: `7.1.4-g7a5cef0db479`

The staging initramfs was built twice byte-identically. Two clean,
network-disabled ASUS builds used independent output volumes and different
parallelism; their wrapper Image, configuration, initramfs, and metadata
matched. Two header-v3/AVB repacks also matched. The fourteen-file bundle
verifier, global manifest, loader test, initramfs test, host contract, and
shell syntax checks pass.

## Normal-boot failure boundary

Four default-command-line attempts reached the exact network-root USB gadget.
Each target reset after the same 16-second interval. A credential-free ACM
capture proved that Linux 7.1.4 had:

1. configured USB NCM with carrier;
2. mounted the exact NFSv4.2 export;
3. created the tmpfs/OverlayFS root;
4. completed `switch_root`; and
5. entered early systemd coldplug/module startup.

NFS traffic was active until reset. SSH did not become ready in that interval,
and fallback ramoops contained no retained record.

## Diagnostic implementation

`ROG5_SYSTEMD_DIAGNOSTIC=1` adds only these target command-line masks:

- `systemd-udev-trigger.service`
- `systemd-modules-load.service`

The default path receives no mask. The loader accepts only `0` or `1`, and an
invalid value fails before invoking kexec. The wrapper was rebuilt rather than
changing the embedded loader after artifact verification.

## Passing target gates

| Gate | Result |
|---|---|
| kernel / PID 1 | exact Linux 7.1.4 / systemd |
| system state | running; `multi-user.target` active |
| SSH | active; dedicated key accepted for root and `rog5` |
| failed units | 0 at acceptance |
| root | OverlayFS |
| lower | exact NFSv4.2 export, read-only |
| writable state | 2 GiB tmpfs, `nodev,nosuid` |
| physical block devices | 0 |
| block-backed mounts | 0 |
| USB | exact `/30` address, NCM carrier up |
| network | sustained NFS reads and 20-packet ICMP pass |
| kernel fatal signatures | 0 |
| memory | about 10.4 GiB available after boot |
| rollback watchdog | alive until all gates passed, then safely disarmed |

The first diagnostic boot survived stress, accepted a controlled watchdog
disarm, and returned orderly to the persistent fallback. The second repeated
the full acceptance gate and remained healthy after watchdog disarm for the
long-running server test.

## SSH persistence

The dedicated private key stays outside the repository at
`~/.ssh/rog5_linux`, mode 0600. Only its public half is present in the prepared
Arch root for root and `rog5`.

After explicit authorization, the same public key was added to the persistent
Alpine fallback while preserving existing entries. The prior file was backed
up on-device as `/root/.ssh/authorized_keys.before-rog5-linux-key`. Key-only
fallback login passed before and after a complete reboot. No private key,
fingerprint, device serial, or boot identity is recorded here.

Arch SSH host keys remain deliberately ephemeral in the tmpfs overlay, so a
client must capture the new exact host key after each network-root boot. The
client authorization key itself persists.

## Coldplug isolation

Manual `qcomtee` loading returned successfully and remained stable for 30
seconds. It is not the reset trigger by itself. The target exposes these
loadable coldplug candidates:

`gpucc_sm8350`, `nvmem_qcom_spmi_sdam`, `nvmem_reboot_mode`,
`pinctrl_sc7280_lpass_lpi`, `qcom_pon`, `qcom_refgen_regulator`, `qcom_rng`,
`qcom_spmi_adc5`, `qcom_spmi_temp_alarm`, `qcom_stats`, `qcomtee`, `qcrypto`,
`rmtfs_mem`, and `socinfo`.

The deterministic boundary and diagnostic success implicate automatic udev
coldplug, but do not yet prove which rule, device, or driver causes reset.
`systemd-modules-load` had only the `i2c-dev` configuration and is less likely
to be the cause.

## Scope and next gate

Diagnostic mode is a usable native headless server shell, not a complete phone
port. Automatic hardware discovery is masked, so no display, touch, battery,
Wi-Fi, charging, or GPU claim follows from this pass.

Next, retain `systemd-modules-load` while isolating udev coldplug in controlled
batches, remove the `ttyMSM0` startup delay, and identify the exact reset
trigger. Only then enable hardware tiers one subsystem at a time.

The only persistent phone-side change in this work was the explicitly
authorized fallback public-key entry. The kernel target had no physical block
device and could not write UFS.
