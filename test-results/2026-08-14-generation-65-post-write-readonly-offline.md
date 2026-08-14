# Generation 65 post-write read-only checkpoint

Date: 2026-08-14

Status: **unbooted; no claim created; RAM-only candidate only.**

Generation 64 successfully persisted the exact local-image probe and proved a
clean read-only remount, then deliberately rolled back at the aggregate
UFS-health gate. Generation 65 is the smallest follow-up: it reuses the exact
read-only kernel and DTB accepted by Generation 58, performs no write-window
operation, mounts both ext4 layers `ro,noload`, and verifies the persisted
marker against its pinned Generation 64 producer boot. The marker producer
must differ from the current target boot in both initramfs and runtime
attestation. Local-write mode retains its current-boot contract.

## Reproducible outputs

- target: `persistent-root-local-image-post-write-v43`;
- release: `7.1.4-gae717d919f87`;
- reused read-only `Image`: `f9fbf172630187877451133bf3634df345703dd5610a01c328d1a50408381aad`;
- unchanged DTB: `40fb477a02844c54624ffdb1b98e2cacecc679f432086b83364f0ce1523319d2`;
- twin initramfs: `fe73cd92cc834f8be20e0250d88c96123e7df96d4656ab461a74bb1e4ea755fa`;
- signed runtime manifest: `9a57ef7dab71d782bce1893525129e24bd350ee74f24aeabe4ed033af6500d07`;
- Generation 65 recovery AVB image: `80a4c775d973a2fc9d2159e48e87c21501339ce27a0226b35bbd7cd723e66fa1`;
- unchanged raw recovery: `5ad4a42c97c01ecae711cb6051b1ae320f7b189c022aa0668552efe4f00d602b`;
- AVB salt: `0497e7a871cc43efff41494dc7591ee28e4dfec440beda78224232804591129c`;
- AVB digest: `8c93bfbd4089873a6a1f4a2de71c125f9bf6c6f31c4aff1889b192c6f9421c5e`;
- generation record: `3f94c8b014d3aca25c29494fe8f55d7b256ff7ccf2a58e6d53bb743268001794`.

The two initramfs builds completed in 0.999 and 0.982 seconds and matched
byte-for-byte. The storage regression suite passed in 0.92 seconds; read-only
and local-write initramfs checks passed in 2.31 and 2.30 seconds. The active
profile, exact-claim, admission, live-runner, and stable-gate focused checks
all pass. Full `scripts/host/test-repository-linux.sh ci` passed in 464.453
seconds. No phone contact, claim creation, installation, or boot occurred at
this checkpoint.
