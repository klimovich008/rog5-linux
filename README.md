# ROG Phone 5 native Linux

Native Arch Linux ARM server development for the ASUS ROG Phone 5 (SM8350).
The accepted installation boots from local storage through slot B, with Wi-Fi,
USB NCM, key-only SSH, Tailscale, charging and persistent service state.
ASUS WW33 slot A remains the rescue and charging route.

Start at [current state](docs/current-state.md). It is the authoritative handoff
for accepted artifacts, limitations, authorizations and next steps.
[Development](docs/development.md) lists the build, package, test and trial
commands. [Roadmap](ROADMAP.md) contains only outstanding priorities.

The repository contains source, configuration and redacted evidence. Private
keys, credentials, per-device backups, proprietary firmware and large outputs
remain outside Git. This is a device-specific experimental port; passing
offline checks does not prove a changed kernel works on hardware.

## Development entry points

```sh
scripts/host/rog5-dev test active
scripts/host/rog5-dev select BASE HEAD
scripts/host/rog5-dev package --config /private/recipe.json \
  --private-key /private/signing-key.pem --bundle-root /private/new-output
```

Packaging does not admit, stage or execute a candidate. Read the
[development workflow](docs/development.md) before a trial.

## Source layout

| Path | Purpose |
|---|---|
| `initramfs/`, `packaging/` | Boot/runtime sources and server services |
| `scripts/device/`, `tools/` | Target helpers and native verifiers |
| `scripts/host/` | Builders, orchestration, packaging and tests |
| `configs/`, `manifests/` | Build profiles, candidate records and policy |
| `dts/`, `patches/` | Device support and diagnostic kernel changes |
| `test-results/` | Dated, redacted evidence |
| `build/`, `artifacts/` | Mostly ignored outputs; some pinned CI fixtures |

Historical loaders and candidate records remain for regression and recovery.
They are not instructions for the next cycle. Superseded documentation is
indexed in [the archive](docs/archive/README.md).
