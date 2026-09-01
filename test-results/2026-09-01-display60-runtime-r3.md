# Display60 V1 runtime result

Result: **FAIL before display acceptance; fallback PASS**.

## One question

Does the exact 60 Hz AMS678/Iris-bypass target register DRM/fbdev and render the
minimal status console while preserving V11 fallback?

## Evidence

- Source exitrd: `ROG5_EXITRD native-kexec enter`.
- Target boot ID: `5036da82-6d9c-44ee-b246-f7144a958b04`.
- Target release: `7.1.4-rog5-display60-v1`.
- UFS ready, storage locked, userdata resolved, and userdata mounted.
- Terminal record: sequence 21, `runtime FAIL`.
- The target returned to exact fastboot; product `lahaina`, serial
  `M5AIKN00F0353YH`, slot B, 8.583 V, `battery-soc-ok=yes`.
- Normal fastboot reboot restored V11 boot
  `eb1bc093-bf27-45b1-ab89-d5bae66e1995` with p24 read-only.
- Pstore was empty and remains inconclusive; there was no panic evidence.
- Claim: consumed; never retry this candidate.
- Phone storage, slot metadata, GPT, and persistent selector: unchanged.

## Cause and regression

Class: **R3**. The optional status installer ran before switch-root, used
`install` although the sealed archive has no `/bin/install` link, targeted
`/usr/local` rather than `/newroot/usr/local`, and assumed the multi-user wants
directory existed.

The tracked runtime now uses only the sealed `mkdir`, `cp`, `chmod`, `ln`, and
`stat` command surface, writes into `/newroot`, creates the wants directory,
and requires an all-or-none five-file payload. Focused host tests and a replay
through the exact sealed AArch64 BusyBox pass before any successor build.
