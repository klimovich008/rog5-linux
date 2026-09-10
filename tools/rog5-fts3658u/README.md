# ASUS ROG5 MP2 front-touch prototype

Minimal external input-driver source for the MP2 FTS3658U normal firmware.
It accepts normal ID `5652`, preserves the native fractional coordinates, and
contains no touch firmware-upgrade or register-value write path. The included
Makefile selects only this external module; it changes no kernel configuration.

This remains a prototype: physical behavior is unqualified, and system suspend
returns `-EBUSY`. Do not treat it as a production touchscreen driver.

Read the [protocol, dependencies and qualification status](../../docs/front-touch-prototype.md).
Run the focused host test from the repository root:

```sh
python3 scripts/device/test-rog5-front-touch.py
```

That command compiles the shared decoder test, not a kernel module. It also
checks the compiled disabled overlay. Use a copied source directory and a
matching, pinned kernel kit for any later external-module build.
