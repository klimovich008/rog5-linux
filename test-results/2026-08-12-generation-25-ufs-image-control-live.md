# Generation 25 UFS-only Image control: live result

Date: 2026-08-12

Generation 25 was consumed by one RAM-only temporary-boot lifecycle and must
never be retried or flashed. The recovery accepted the exact signed
`persistent-root-storage-read-v4` bundle, recorded all five preparation
phases through `PREPARED_PERSISTED`, and accepted `COMMIT_EXEC`. Recovery USB
then disconnected. No target USB identity or target diagnostic frame appeared.
The exact Alpine fallback USB identity returned 25.038 seconds later, its
NetworkManager profile was restored, and strict key-only SSH identity proof
passed. The maximum reported fallback temperature was 41.5 C.

No UFS inventory was obtained, and the cycle performed no authorized phone
storage write. The result therefore does not distinguish a failure before
target init from an early target failure before USB gadget setup.

The cycle also exposed a separate host observation race after fallback: a
newly enumerated NCM interface can exist briefly before NetworkManager exposes
its `GENERAL.MANAGED` property. The lifecycle treated that transient as a
terminal failure after the successful fallback proof. The successor changes
this exact classification gap to a retryable host-identity observation and
adds a hardware-free regression test.

Retained private evidence includes the exact claim record, recovery transfer
and control logs, USB/udev/kernel monitor logs, fallback identity record, and
resolved durable intent. It contains no proof that UFS itself was reached.

Result: `FALLBACK_RETURNED`; Generation 25 consumed; hardware admission moves
only to a newly built generation.
