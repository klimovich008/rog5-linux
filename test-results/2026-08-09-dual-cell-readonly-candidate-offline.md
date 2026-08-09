# Read-only dual-cell candidate — hardware-free result

Date: 2026-08-09

Branch: `agent/linux-recovery-host`

Starting repository HEAD: `5200fa93dc4dac1d8e033b7990a3b5e18d5ea7df`

Phone access: none

Boot/flash/storage/credential authority used: none
Result: **passed as an offline compile-only candidate; live and release
status remain HOLD**.

## Defects closed

1. Mainline qcom_battmgr exposed only aggregate pack voltage, so the accepted
   8.255 V snapshot could not be checked against the ROG Phone 5's two cells.
   The bounded patch adds the vendor-evidenced owner-32782/opcode-0x3005 read
   without importing the vendor driver's control surfaces.
2. There was no exact DT opt-in separating this ASUS-only read from generic
   SM8350 systems. The candidate adds and verifies one empty property on the
   already isolated battery-only PMIC GLINK node.
3. There was no hostile runtime fixture for the new read-only ABI. The new
   snapshot collector fails closed on malformed values, changed inventory,
   writable/linked attributes, charging controls, and aggregate inconsistency.

## Pinned inputs

- Linux source commit:
  `7a5cef0db4795d9d453a12e0f61b5b7634fc4d40` (`v7.1.4`).
- Qualified builder image:
  `bdb4bbda79ab38a55c72d23b269f5c3f5cb14d153e373ce50932c17538e9ccaf`.
- Vendor protocol oracle:
  `drivers/power/supply/asus_battery_charger.c`, SHA-256
  `22aa2cd9d4259ac396c7dd52ebafbced1c4dcbe84565b4f0c3b74f95f0ce5ab7`.
- Current telemetry DTB base: 102,938 bytes, SHA-256
  `3f4305d7fbbd2c74d15c1011bb8a2e8e24b3a5228f31ed86281917d16cf18f11`.
- Driver patch SHA-256:
  `12b84505ce30374482683e477e438c0c68ce41cdf7241e23c202be6625f8cbf0`.
- DT overlay SHA-256:
  `a80e538d587fce7ed445624c1cc5cd4a83740706624605d586d2195e0eef710c`.

## Fail-first and focused results

Before implementation, the new source and DT tests failed on their missing
patch/overlay in 9 ms each. The runtime fixture failed on its missing collector
in 81 ms. After implementation:

- hostile source patch contract: 521 ms;
- hostile exact-delta DT contract: 715 ms;
- hostile runtime snapshot fixtures: 347 ms, six test groups;
- patched AArch64 `qcom_battmgr.o`: 2,407 ms.

The successful object is a 64-bit AArch64 relocatable with SHA-256
`89bf737ed626158fcf2da2359742e499f1457114d56be59d936094c6e85fa9af`.
It contains `dev_attr_cell_voltages`, `qcom_battmgr_asus_callback`, and
`qcom_battmgr_asus_pdr_notify`.

A separate 133 ms fail-first mutation exposed the service-loss/response-timeout
race before its guard existed. The final implementation revalidates a service
generation around each request and poisons the request path after timeout
until PMIC service transitions, so an untagged late response cannot satisfy a
retry.

The first 44,353 ms repository-CI run then failed before unrelated source/DT
mutation assertions because `rog5-core-source-dtb-v1.json` still pinned the
previous compatibility-profile hash. The exact pin was updated to the reviewed
profile SHA-256
`cd5d42b2f6ee681bd9f792d971383176cec8daf50a4792b1fd05f1b48d8a676a`;
the focused 77-test source/DT contract then passed in 13,087 ms. No semantic
source or accepted-DTB policy was relaxed.

An earlier 26,334 ms partial-directory command compiled the driver but stopped
at modpost because no complete-kernel `Module.symvers` existed. That expected
partial-build limitation is not reported as a linked module result. Clean
twin complete builds remain mandatory before candidate issuance.

## Safety outcome

No phone was detected, queried, booted, or written. No credential was read.
The patch adds no setter, writable attribute, Type-C/UCSI path, debugfs/proc
interface, firmware loader, GPIO, nvmem access, or charging policy. The
collector's `OBSERVED_NOT_HEALTH_ASSESSMENT` result cannot promote charging
or battery-health acceptance.

See the [contract](../docs/dual-cell-readonly-telemetry.md). The next eligible
step is a clean twin full-kernel build and candidate assembly; any phone run
remains a separate lifecycle decision.
