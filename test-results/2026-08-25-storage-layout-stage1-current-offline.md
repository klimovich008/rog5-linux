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
- Status remains HOLD awaiting the exact final destructive confirmation. No
  policy admission, claim, boot authority, phone contact, partition operation,
  or storage write exists for Generation 165.
