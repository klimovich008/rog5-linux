# Generation-4 lifecycle profile — offline transition

Date: 2026-08-03

Result: **PASS reviewed offline**. The one-shot diagnostic lifecycle now
selects generation 4, while the generation-4 recovery remains absent from
temporary boot policy. Focused tests and the complete local CI tier pass, and
the constrained read-only Claude Opus review reports `NO FINDINGS`. No
connected preflight or phone action occurred.

## Exact transition

The immutable `headless-diagnostic-generation4-offline-v1` profile still
permits only `policy-preflight` and `artifact-preflight`. The new
`headless-diagnostic-generation4-live-v1` profile pins the identical recovery,
kernel, raw wrapper, initramfs, control, fetcher, verifier, runtime manifest,
trust root, host verifier, AVB-generation record, AVB salt, and AVB digest.

The lifecycle constant changed from the consumed
`headless-diagnostic-generation3-live-v1` profile to
`headless-diagnostic-generation4-live-v1`. No payload or kernel identity
changed.

## Test-first evidence

Before production code changed, two tests failed for the intended reasons:

- the live gate rejected the unknown generation-4 live profile; and
- diagnostic lifecycle preflight rejected the generation-4 profile expected
  by its mock because the controller still selected generation 3.

After implementation:

- both generation-4 profiles pass the exact policy mutation matrix;
- both pass the complete retained-artifact preflight;
- offline-profile connected preflight and boot fail before host inspection;
- live-profile direct boot fails before host inspection unless the one-shot
  lifecycle guard is present; and
- all 42 lifecycle tests pass with generation 4 selected.

The complete `scripts/host/test-repository-linux.sh ci` tier also passes,
including documentation links, the stable-recovery gate, and all 42 lifecycle
tests. A self-contained, credential-free Claude Opus review ran in safe mode
with no tools and no session persistence. It specifically checked the absent
authority, lifecycle-only boot guard, generation selection, identical artifact
pins, unchanged boot policy, and mutation coverage, and returned
`NO FINDINGS`.

## Authority boundary

`manifests/temporary-boot-images.tsv` is unchanged and contains no `allow` row.
The generation record remains `authority=none`. The live-capable profile is
necessary wiring, not boot admission: connected preflight still cannot pass
the policy gate, and no boot is authorized by this result.

## Host and phone state

The repository began clean and synchronized at `51bf4a1`. The installed host
controller and bundle server match their reviewed source hashes exactly:

- controller: `5f6ec19cbe87d57cfda4d95d872d07db1888cb631f8a01faa6f9aa756020b7d4`
- server: `9258c0e72ca7adb626fdafccfc1bababb68263b40ad23b635b0cc8c19b7ffac0`

The phone was observed only as the persistent fallback Linux composite gadget,
not fastboot. One stale host-only `fastboot getvar product` diagnostic from the
same Codex task had been waiting without a timeout for over an hour; its exact
shell and child were terminated. Subsequent fastboot discovery was bounded to
five seconds and returned no device. No phone reboot, SSH command, recovery
connection, NFS startup, payload transfer, COMMIT, or phone-storage access
occurred.

## Next gate

Publish this exact checkpoint and require green GitHub CI. Only then may a
separate change add one exact temporary-boot `allow` row for connected
preflight.
