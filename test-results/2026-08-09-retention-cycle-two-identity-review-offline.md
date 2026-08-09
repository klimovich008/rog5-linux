# Target/observer two-identity retention review — offline

Date: 2026-08-09

Starting repository SHA: `d78b21cda4d4b7b967fdda3c04b48ecdc1d4c02c`

Decision: **HOLD**

## Defect fixed

The execution recovery and observation-only recovery had separate reproducible
build evidence, but no single machine-enforced review bound their exact roles,
bytes, transition order, claim state, and empty temporary-boot policy. A future
operator could therefore select individually valid but mismatched artifacts, or
mistake offline composition evidence for an issued retention experiment.

`scripts/host/verify-retention-cycle-admission.py` now performs that joint,
read-only review against the repository-owned
`configs/retention-cycles/host-rendezvous-v3-observer-v1.json` profile. It does
not issue a candidate, define a boot claim, use a credential, contact a phone,
or grant boot authority.

## Exact offline identities

The execution side binds:

- candidate record `41c23330fd95d7c7426434ae3c19f948208f221ddc4f502859137f22b7eab9cf`;
- runtime manifest `54f534203fe3efbb95713eaef861b1bdb6ae6c56dad2f1b2b77dd09efed36efc`;
- full recovery initramfs `dd224fb964d4d19c87d8107945ea835c62b97bc34c4faf50cfcc47a5255947c1`;
- wrapper Image `05f702c7f9ed4ebb7f416377b769a80b7f17c8443d7c8d75b374995509899e80`;
- raw boot-v3 image `e8c010ff723a45eb17cbdf4acb9510f2cc4783caaefa70eca6d8137ee7f92e23`;
- unsigned AVB image `142f44f461ab82c586bf06136358370356162826433d11639237299c107706ba`.

The observer side binds:

- observation-only initramfs `613d6e3e61d7818693c0d26b0b7c252479941cc25c98e897ef6aa30469e770db`;
- wrapper Image `efcc4db8a5ad6abbd27a7489bb7f9ae202ab93662e5b7953e77621671e27a6ab`;
- raw boot-v3 image `fdcf9b85951fe696afb56f1b3d3c9e6581ce040fdcce1e51f8ed37d23d4fa163`;
- unsigned AVB image `63fc0a1a6827941d51edb7033fa501ae74dd8c192fad65d84f7816e3caf743b1`.

Both wrappers use `Algorithm: NONE`; that is verified composition evidence,
not production signing. The profile requires this exact order: diagnostic
target, exact Alpine fallback, bootloader, observation recovery, then
`postmortem-status`.

## Enforced review boundary

The verifier fails closed unless:

- the execution and observer evidence roots are distinct, non-nested, ignored
  local directories with exact top-level inventories and closed bundle
  inventories;
- every selected file is owned by the verifier identity, has its exact reviewed
  mode and size, is reached by descriptor-relative no-follow traversal from
  pinned roots, and survives descriptor, ancestor, root, and pathname
  revalidation;
- both signed execution bundles have exact schemas, byte-identical twins, and
  valid Ed25519 signatures under the disposable offline public key;
- the full initramfs contains the execution path while the observer is exactly
  its reviewed observation-only derivation without the fetcher, verifier,
  trust key, kexec binary, or bundle root;
- both Android boot-v3 images embed the exact reviewed Image, initramfs, zero
  padding, and fixed ramoops command line;
- both AVB images contain one exact SHA-256 boot descriptor, zero authentication
  data, valid geometry, recomputed digest, and zero partition padding;
- the built config has the exact pstore/ramoops options;
- the generic claim consumer remains byte-pinned and exposes only the consumed
  Generation-11/12 profiles; neither new role has an issued claim;
- `manifests/temporary-boot-images.tsv` contains zero `allow` rows.

Missing pstore remains `inconclusive`; it is never interpreted as evidence of
no crash or of successful retention.

## Regression evidence

The fail-first run stopped because the repository-owned verifier/profile did
not exist: one test failed in 0.053 seconds. The completed 17-test hostile
suite passes in 1.979 seconds and covers role, sequence, authority, policy,
schema, signature, archive, derivation, boot-v3, AVB,
descriptor/ancestor/root races, symlinks, root crossover, detached signed
manifests, exact modes, bounded reads, late claim mutation, and evidence
inventory failures. Full repository timing is recorded in the final checkpoint
handoff after exact-head execution.

Two independent read-only Opus reviews identified incomplete boot-image
binding, path aliases, heuristic claim inspection, partial schemas, TOCTOU,
AVB geometry, unbounded archives, appended CPIO members, bundle-root aliasing,
and post-definition claim mutation. The formal Standards/Spec review then
reproduced ancestor replacement, detached signed manifests, claim-profile
extension/rebinding, non-exact modes, top-level inventory additions, embedded
NUL CPIO aliases, and unbounded buffered input. The implementation and hostile
fixtures were tightened for every material finding before final CI.

## Remaining uncertainty

No physical transition has been run. Ramoops retention across target → exact
fallback → bootloader → observation recovery remains unproven, and USB-NCM
loss still removes the primary live diagnostic transport. The two exact claim
records required for a future experiment are intentionally undefined, and the
central policy remains empty. This review therefore does not make the current
candidate eligible for admission: **HOLD**.
