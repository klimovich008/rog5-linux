# Automatic accepted core-source and corrected-DTB revalidation

Result: **PASS; host-only, authority-free, and credential-free.**

This increment started at
`90f891bddd85f728200a7cf42b6ded542a4a46fb`. No phone command, phone
storage access, credential access, signing, candidate issuance, or boot
occurred.

## Concrete defect fixed

The canonical accepted Linux 7.1.4 source was present and clean at
`build/linux-stable-v7.1.4-source`, and the corrected accepted DTB was tracked,
but normal local repository CI still skipped their real-input positive test
unless a caller manually set `ROG5_ACCEPTED_KERNEL_SOURCE`. A green local
checkpoint could therefore cover all synthetic mutations without proving the
actual retained source/DTB oracle remained valid.

The focused suite now selects that one fixed ignored worktree automatically
when its pathname exists. An explicit environment path still takes
precedence. An absent default remains an intentional skip for clean GitHub
checkouts, while a link, broken link, wrong file type, dirty worktree, wrong
commit, or changed source identity reaches the existing fail-closed baseline
verifier instead of being mistaken for absence.

## Regression and exact evidence

Three new discovery regressions prove explicit override precedence, automatic
fixed-path selection versus clean-checkout absence, and refusal to silently
skip an unsafe retained pathname. The complete focused suite now runs 77
tests, including the actual source/DTB baseline positive case, with no skip.

- preceding local CI focused suite: 74 tests in 12,213 ms, one real-input
  skip;
- corrected focused suite: 77 tests in 12,911 ms, zero skips;
- direct real-input verifier: 513 ms.

The direct verifier proved:

```text
active_capabilities=6
source_checks=43
dt_checks=23
thermal_cpu_zones=12
thermal_pmic_alarms=5
source_commit=7a5cef0db4795d9d453a12e0f61b5b7634fc4d40
dtb_sha256=86e5cb81191e3de39c9527b838fa03d78744cd9b0d862336f0c1f36a9f534f46
hardware_acceptance=unproven
authority=none
status=baseline-verified
```

The final repository CI timing and ending commit are reported in the handoff
for the commit containing this record.
