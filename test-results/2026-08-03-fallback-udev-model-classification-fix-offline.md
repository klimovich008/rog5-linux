# Fallback udev-model classification correction — offline

Date: 2026-08-03

Result: **PASS offline**. The Generation-6 final-cleanup failure is reproduced
without phone contact and corrected at the exact host identity boundary. This
result does not relabel the failed live cleanup proof and grants no boot
authority.

## Root cause

Production fallback udev reports
`ID_MODEL=ROG_Phone_5_Linux_Server`. The lifecycle's shared NCM classifier
required the same vendor `1d6b`, product `0104`, and `cdc_ncm` driver, but then
accepted only models beginning `ROG5_`. The restored fallback interface was
therefore omitted from the exact interface set, so its canonical
`169.254.77.1/30` address appeared to have escaped the managed USB profile.

The old offline fixture hid this mismatch by continuing to emit
`ID_MODEL=ROG5_recovery` after simulated fallback proof.

## Correction

`rog5_ncm_interfaces()` now accepts only these exact normalized udev values:

- `ROG5_recovery`;
- `ROG5_network_root`;
- `ROG5_diagnostic_network_root`; and
- `ROG_Phone_5_Linux_Server`.

The existing exact vendor, product, driver, address, NetworkManager, firewall,
and cleanup checks remain unchanged. There is no prefix, trimming, or
case-folding fallback. Missing values and near matches remain unclassified.

The lifecycle fixture now emits the real Alpine model only after fallback
proof. Each exact allowed model passes behaviorally. The hostile matrix rejects
the old broad `ROG5_` prefix, arbitrary project-like models, leading/trailing
whitespace, case changes, empty or missing values, prefixes, suffixes, and
embedded combinations. A dedicated fallback regression proves the exact
Alpine model reaches clean intent resolution without a cleanup-proof error.

## Verification

- Python syntax compilation: pass;
- focused lifecycle suite: 52 tests pass;
- constrained credential-free Claude Opus diff review: completed; supported
  exact-match and hostile-coverage findings were applied, while trimming and
  case-folding were rejected to preserve byte-exact identity;
- complete repository Linux `ci` tier: pass;
- phone, fastboot, recovery, SSH, NFS export, and host-network mutation: none.

The independent Generation-6 complete-transfer/control-silence boundary is
not corrected here. No successor may be issued solely from this result.
