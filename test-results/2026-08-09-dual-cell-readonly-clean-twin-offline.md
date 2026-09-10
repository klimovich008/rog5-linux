# Dual-cell read-only clean-twin candidate — offline result

Date: 2026-08-09

Branch: `agent/linux-recovery-host`

Starting repository HEAD: `0adffcd8d49a0cd81b02f44afa9a4cada14e922b`

Phone, credential, signing, publication, and storage-device access: none

Result: **passed as an unbooted, authority-free clean-twin candidate;
hardware acceptance remains unproven**.

## Concrete defects fixed

1. The source/ABI proof stopped at a partial AArch64 object, so it did not
   prove a linked module or complete-kernel reproducibility. The new release
   path prepares one deterministic patched source identity, performs two clean
   complete builds with cache and incremental reuse disabled, semantically
   verifies each, and compares all release-relevant outputs.
2. Twin comparison omitted `Module.symvers`. It is now a mandatory
   byte-identity gate alongside `.config`, both Images, module archive, and
   build metadata.
3. The historical telemetry DT helper requires a power-key state that is not
   part of the current accepted battery-only telemetry base. The release path
   now reconstructs that exact pinned base directly, twice, without changing
   the historical helper or its evidence contract.
4. The candidate path lacked fail-closed output ownership. It now uses an
   atomic output lock, refuses replacement or mismatched source identities,
   compares twin manifests, and publishes locally without replacement. A
   follow-up review also removed the temporary resume/finalize path: candidate
   issuance can now occur only in the same invocation that prepares two fresh
   sources and executes both clean builds.
5. The generic network-root verifier accepted one fixed source identity only.
   A closed `dual-cell-readonly` profile now pins the exact candidate commit
   and release; arbitrary caller-supplied identities remain forbidden.

## Fail-first and regression evidence

The new release-contract test initially failed because the deterministic
source preparer did not exist. After implementation, focused results were:

- source-patch hostile contract: 405 ms;
- exact-delta DT hostile contract: 941 ms;
- runtime snapshot hostile fixtures: 443 ms;
- release integration/locking/fresh-only contract: 332 ms;
- network-root rebuild contract: 173 ms;
- incremental invalidation and locking contract: 1,736 ms;
- optional real twin source materialization: 141,374 ms.

The first complete orchestration reached two verified and byte-identical clean
builds, then failed before candidate publication because it called the
historical telemetry helper with the obsolete power-key expectation. No
candidate existed and the output lock was released. The corrected direct
telemetry reconstruction passed the focused regression, then the bounded exact
twin finalizer rechecked source identities, full-build log markers, both
semantic verifiers, and every twin comparison before publication.

The one-time finalizer was removed after review because copied valid evidence
could not cryptographically establish two independent invocations. The
retained candidate came from the two clean executions recorded above, remains
authority-free, and is not a reusable input to the now fresh-only issuance
script.

The fresh-only regression fails against the pre-review implementation on its
`RESUME_EXACT_TWINS` publication surface. It also dynamically acquires the
candidate output lock with a deliberately missing source, so clean CI proves
concurrent-output refusal before the optional retained kernel source check.

## Exact source and build identities

- accepted parent commit:
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40`;
- deterministic candidate commit:
  `7ee91d34b5458efa0ac45d979bab82bbd2cb7ea5`;
- candidate source tree:
  `ef7703ecc0aad3d625cfbbef296e586d861deefe`;
- kernel release: `7.1.4-00001-g7ee91d34b545`;
- qualified builder image ID:
  `bdb4bbda79ab38a55c72d23b269f5c3f5cb14d153e373ce50932c17538e9ccaf`;
- jobs: 8; `INCREMENTAL_BUILD=0`; `KBUILD_CCACHE=0`.

Source preparation took 21,338 ms for twin A and 22,907 ms for twin B. Clean
build A took 2,287,082 ms (38m07.082s); clean build B took 2,206,791 ms
(36m46.791s). The guarded post-failure revalidation and finalization took
58,937 ms.

## Byte-identical outputs

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `.config` | 239,677 | `68fb3025f3677a7dc8607396af9fcb17c75398b3285d624f1588d564e03c513f` |
| `Image` | 40,049,152 | `0a16cbee15464a1689dbb5f492518600d79823e56cc32c9bec4b1a9a5a4c752f` |
| `Image.gz` | 14,751,421 | `eb84e0edf6017c5d1be68a65c92df1e14c8b68003f34ae9cfedaab75b1a7a0a8` |
| `Module.symvers` | 1,140,345 | `008919805fa413eefe4bb42675bcf6467a0a5bcef87158af05deec5e4cf75365` |
| `modules.tar.gz` | 300,435,627 | `8e8a2e70a36e5a01df110517a86e6c3e26a4f50033841780042dfa652877b331` |
| `build-meta.txt` | 629 | `1cbf82658a3fee5d0ce6b21a59b54d280b5d5232d51145a1bae548b4ca792dc6` |
| `qcom_battmgr.ko` | 351,824 | `5a338fb5454e7ab8e3ec60ad09dd0aea877e5493db51bc0cb5a35841926442ca` |
| candidate DTB | 102,977 | `ffd8204c671c27ce413951c4f31b23486ade7f5755f36a534b902dd76d2b90a7` |

The 1,864-byte candidate manifest has SHA-256
`3f887f9f9f56e5b547458d721fc42b942c3f1b89807fe82cd2f97f120e523e24`
and records `status=compile-only-clean-twins`, `execution_state=unbooted`,
`authority=none`, `boot_authority=none`, and
`hardware_acceptance=unproven`.

## Safety outcome

No phone was queried or booted. No flash, wipe, erase, slot, persistent
installation, or phone-storage operation occurred. No credential or signing
key was read, and nothing was pushed or externally published. The retained
ignored candidate is compile-only evidence; a phone observation requires a
separate reviewed lifecycle decision.
