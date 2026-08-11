# Generation 20 temporary Arch + SSH MVP

Status: **PASS, consumed, never retry**.

The sole RAM-only use of recovery AVB
`cacd0164d7d1d581f6fa4cb8926d7fea655be92e333c84635de953dd7d816b39`
completed the minimal headless path on the ASUS ROG Phone 5. No image was
flashed and no phone storage was mounted or modified.

The exact stage timeline from the private receive-only reporter was:

| Stage | Target boot time |
| --- | ---: |
| reporter up | 2.680 s |
| address configured | 2.930 s |
| NCM carrier up | 3.680 s |
| NFSv4.2 mount verified read-only | 4.930 s |
| sealed root verified | 350.038 s |
| switch-root executed | 350.288 s |
| systemd new init up | 359.043 s |
| sshd active | 372.046 s |
| strict key-only SSH accepted | 379.548 s |
| rollback watchdog pretimeout | 597.104 s |
| final frame before expected disconnect | 602.606 s |

Runtime acceptance verified Linux `7.1.4-g7a5cef0db479`, six active
capabilities, 10,884,800 KiB available memory, 33 thermal zones, the exact
read-only NFS lower plus OverlayFS topology, zero phone-storage exposure, the
diagnostic USB gadget, and the still-armed rollback watchdog. The prior broad
fatal-signature false positive did not recur.

The reporter captured 2,400 valid frames and 383 transport snapshots with no
dropped snapshots or USB events. Every frame remained `fault=none`; the last
good stage at watchdog pretimeout was `ssh-key-accepted`.

The intentional watchdog rollback returned the exact Alpine fallback. Strict
pinned SSH, fallback NetworkManager profile restoration, NFS/server cleanup,
Steam TCP/8081 socket restoration, and durable `FALLBACK_RETURNED` resolution
all passed. The fallback reported exact PMIC `PS_HOLD` / `HARD_RESET` state
without a PMIC watchdog signal. Pstore was unavailable, so the absence of a
retained crash record is inconclusive and is not evidence that no crash
occurred.

Private host keys, boot IDs, signatures, nonce material, and raw live logs
remain outside Git. Generation 20 is removed from temporary-boot policy and
its exact private one-use claim remains retained.

## Publication verification

The live cycle began from clean, pushed commit
`09cd5a41d0b6ec2b2cccdb4fd0d70e05032a80b2` and completed in 727 seconds.
Post-cycle focused checks passed: current-profile refusal in 12 seconds,
recovery policy in 1 second, stable live-gate policy in 4 seconds, the
39-test compatibility oracle in 1 second, and the 77-test source/DTB contract
in 12 seconds. Complete local `scripts/host/test-repository-linux.sh ci`
passed in 355 seconds after correcting stale tests that still assumed the
consumed execution image remained an active policy row.
