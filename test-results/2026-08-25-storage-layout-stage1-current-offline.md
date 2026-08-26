# Current dedicated-layout Stage 1 offline

- Public geometry remains unchanged: partitions 1–22 preserved, userdata tail
  shrunk to LBA 53,477,375, and aligned 32-GiB `arch_root_a` at entry 24.
- The private config now binds current userdata UUID
  `0892bacf-3e02-41b0-84a4-5f05c2df7ce5`, a fresh operation ID, existing GPT
  identities, and the unused proposed root GUID.
- The public checkpoint binds source image
  `533973be0e0ca76c5db8645fdef9aeb64d20b8c9c98b70124a2561700f119153`,
  tree `4701c23b93624bf894bb76331c165b650c9a2aecb99273a4e6d37c20ac3ef167`,
  slot-A rescue, and accepted Generation 163.
- Clean Stage-1 twins completed in 1.804 and 1.781 seconds and matched at
  SHA-256 `b9851f3e1d901fb32f2ea32dab8042a8bdc109dd30b1d1e06a10664befae294f`.
- Generation 164 then passed the current physical read-only gate with exact
  UFS/GPT/ext4 geometry, all block nodes read-only, zero mounts, and a fresh
  minimum of only 1,219,496 blocks.
- The current Stage-1 twins were repacked with the unchanged ASUS wrapper
  kernel and exact 900-second cmdline. Raw twins match at SHA-256
  `780dcfc2da571e76375f3e60eddf90e2b1a6881c5d13b5076aeec8a167ade98a`;
  authority-free AVB Generation 165 twins match at
  `1a00e9061c027c804458732cfc93ba7175ee6821d821f9d86ffa079383fd5fc2`.
- A private machine-readable execution record binds the old/new geometry,
  retained backup hashes, current preflight, exact commands, abort conditions,
  and rollback limitations at SHA-256
  `4e7f9e88bb53d69d16c546980eb36ec14a23a525c896e0602d2c75928134bac2`.
- The user supplied the exact final destructive confirmation. Generation 165
  entered its one-use claim and booted once, but host preflight caught that its
  private collector template still used short USB path `1-1.2` while the
  collector requires the canonical full sysfs path. The collector never
  started: no readiness record, fresh backup ACK, writable block device,
  resize, GPT command, partition operation, or storage write occurred. Exact
  slot-A unauthorized-ADB fallback passed. Generation 165 is consumed and
  revoked with R1 classification.
- The first full-CI attempt exposed a host-only stale identity tuple in the
  dormant retention process contract after prior claim/live-gate edits. The
  exact three current program size/hash tuples and their dependent profile
  bindings were refreshed; 59 focused executor/boundary/runtime/admission tests
  then passed. The frozen repository `ci` tier passed in 7m26.974s. This fix
  changes no wrapper, Stage-1 executor, initramfs, phone command, or candidate
  byte.
- The collector-compatible canonical execution template is separately retained
  at SHA-256
  `080aea76796bd3f0fad230796086adb14d45ca55557d6a40af2aa77b2a00b955`.
  The candidate manifest intentionally no longer pins the claim-consumer source
  that embeds the manifest hash, eliminating that recursive identity cycle.
- Generation 166 reuses byte-identical raw wrapper SHA-256 `780dcfc2...` under
  fresh AVB SHA-256 `4843d18e...` and changes only the private host template to
  canonical location
  `pci0000:00/0000:00:08.1/0000:04:00.3/usb1/1-1/1-1.2`. Its manifest is
  `cc348a62...`; focused Stage-1, collector, generic-claim, runtime-closure and
  admission tests pass. One narrow admission exists and its claim is
  unconsumed.

## Generation 166 live result and Generation 167 correction

- Generation 166 consumed its sole cycle. The canonical collector path passed,
  fresh GPT/raw backups were durably written and ACKed as set
  `1a6295725cb63ab27f90022e5061be6552eec7d6a4297cc4f5ff088543948679`,
  watchdog disarm passed, and ext4 shrank to exactly 51,124,000 blocks.
- The target then returned exact
  `S60_GPT_TRANSACTION/gpt_transaction_failed/gpt_restored=yes`. The original
  GPT was restored from the fresh in-RAM backup and exact slot-A recovery
  returned. The recoverable intermediate is the smaller filesystem inside the
  original larger partition; partition 24 is absent.
- Replaying the exact multi-option transaction against that fresh backup on a
  disposable 4-KiB-sector host loop succeeded with exact proposed geometry.
  Target `sgdisk --load-backup` is independently proven by the successful live
  restoration, isolating the failure to target-side multi-option editing rather
  than UFS write or backup-load support.
- The successor removes target-side GPT option reconstruction. It seals the
  exact verified 5,632-byte desired GPT backup at SHA-256
  `6774a2e5aa7defcb8197910a2b56ddc61be44f2681038c400f9a5ee0eb057a0e`
  and performs one already-proven `sgdisk --load-backup` transaction. Source
  tests require that operation and reject all prior `--delete`, `--new`, GUID,
  attribute, and alignment options after S60.
- Clean successor initramfs twins match at `f30d412c...`; authority-free AVB
  Generation 167 is prepared at `3f16f069...`. Full storage/trust CI passed on
  frozen implementation commit `827af45` in 6m55.105s. The separate generated
  manifest and one narrow admission now bind the exact candidate; its one-use
  claim remains unconsumed.

## Generation 168 observation loss / Generation 169 discriminator

- Generation 168 consumed its sole cycle. Recovery USB appeared but departed
  before the anchor-first lifecycle started the collector. No terminal record,
  backup directory, readiness, ACK, writable device, or storage write exists;
  exact slot-A fallback passed.
- After two pre-S30 observation losses, the explicit systematic-debugging skill
  and a bounded read-only Claude Opus review were used. Opus ranked a fast
  target S00/S10/S20 failure plus host observation loss highest and recommended
  collector-before-boot as the smallest safe discriminator. Independent review
  confirmed all config lines, every filesystem call site, embedded root:root
  0400 config/GPT metadata, hashes, and BusyBox sha256sum closure.
- A new receive-only observer waits for the exact recovery ACM before boot,
  parses ordered S00/S10/S20/FAIL or S30, and sends zero bytes. At S30 it exits
  without readiness or ACK, so the cycle cannot cross the storage write gate.
  Four focused hostile tests pass. The active tier was blocked by an unrelated
  stale local-image direct extent map before reaching this test; the focused
  observer and repository-runner contract tests pass.
- Generation 169 reissues byte-identical Generation-168 raw target bytes under
  fresh AVB SHA-256 `95007839...`. Its sole question is the exact prewrite
  stage/reason; no mutation is authorized by the host observer.

## Generation 169 observer result

- Generation 169 consumed its sole receive-only cycle. The observer was running
  before boot, attached to exact recovery ACM, parsed a complete verdict in
  memory, and sent zero bytes. The target then departed as expected.
- The host discarded that validated verdict because post-capture USB
  revalidation ran before evidence publication and treated zero remaining
  products/interfaces as an error. No output file, readiness, backup, ACK,
  writable device, or storage write exists; exact slot-A fallback passed.
- The host-only correction classifies zero product/interface after capture as
  `DEPARTED`, writes and fsyncs validated evidence before treating a changed
  identity as terminal, and keeps changed identity distinct. Seven focused
  tests pass. Generation 170 reissues the same raw target bytes under fresh AVB
  SHA-256 `56f8a8b3...`; one receive-only admission exists and its claim is
  unconsumed. No target bytes change.

## Generation 170 exact root boundary

- Generation 170 consumed one receive-only cycle and durably captured exact
  `S00_CONFIG/invalid_private_config/gpt_restored=not_needed` with
  `post_capture_identity=DEPARTED`. The observer sent zero bytes; no readiness,
  backup, ACK, writable device, or storage write occurred. Exact slot-A
  fallback passed.
- This proves Generations 167-170 failed before topology/filesystem checks; the
  51,124,000-block predicate was not reached. Offline archive inspection proves
  canonical config/GPT content and metadata, but cannot identify which runtime
  predicate differs.
- The next diagnostic replaces the generic config failure with a finite,
  non-secret reason for every config path, owner/group/mode/link/count/value,
  GUID, sealed-GPT size, and hash predicate. Nineteen focused source tests pass.
  The receive-only host continues to stop at S30 and cannot authorize mutation.
  Generation 171 clean twins use AVB SHA-256 `65a672c4...`; one narrow
  receive-only admission exists and its claim is unconsumed.

## Generation 171 prewrite PASS and fastboot fallback correction

- Generation 171 consumed one receive-only cycle and durably captured ordered
  `S00_CONFIG`, `S10_TOPOLOGY`, `S20_PROTECTED_SEAL`, and
  `S30_FRESH_BACKUP`, with outcome `REACHED_S30_NO_HOST_BYTES_SENT` and exact
  anchored USB identity. This proves the rewritten config check, current GPT,
  51,124,000-block ext4 state, partition-24 absence, and protected seal.
- The observer sent zero bytes and intentionally stopped at S30; no readiness,
  backup, ACK, writable device, GPT load, or storage write occurred. Exact
  slot-A fallback passed.
- The repeated operator bottleneck was traced to recovery-init's generic
  `force_rollback()` using `reboot -f`, which enters slot-A recovery. Storage
  Stage-1/2 rollback now calls the existing sealed restart2 `bootloader` helper
  first for all early, watchdog, failure, and success paths. Generic reboot and
  SysRq remain fallback if restart2 unexpectedly returns. Twenty-one focused
  Stage-1 source tests pass.
- Production Generation 172 clean initramfs twins match at `97c71ef0...` and
  AVB twins at `fa8d5ca4...`. Full recovery/storage CI passed on `5aec551` in
  7m24.105s. The candidate binds Generation-171 S00-S30 evidence, the current
  filesystem, sealed GPT, normal fresh-backup collector, and restart2 fastboot
  fallback; one narrow admission exists and its claim is unconsumed.

## Generation 167 prewrite result

- Generation 167 consumed its sole cycle and exact slot-A fallback passed.
  Recovery USB appeared, but the target exited before ACM stabilization and no
  Stage-1 backup directory was created.
- Source inspection proved the exact stale predicate: S10 still called
  `verify_userdata_filesystem 59513299` even though Generation 166 had already
  shrunk ext4 to 51,124,000 blocks before restoring the original GPT. This is
  R2 and occurred before S30, collector readiness, fresh backup, ACK, writable
  block device, GPT load, or any new storage write.
- The successor changes only that prewrite expectation to the current verified
  51,124,000 blocks. A source regression test requires the new value before S30
  and forbids the old value. Clean target-initramfs twins match at
  `282d9360...`; full CI passed on `74ffd15` in 6m53.439s. Generation 168 AVB
  twins match at `e5d54cf3...`; one narrow generated admission exists and its
  claim remains unconsumed.
