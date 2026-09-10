#!/usr/bin/env python3
"""Consume the exact Generation 151 local-image write benchmark claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-write-benchmark-v42-generation151-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-write-benchmark-v42-generation151-live-v1\n"
    b"candidate=local-image-write-benchmark-v42\n"
    b"manifest_sha256=eda3bd6c644adb12254cf92d1c32dab1ace1982809227f0eb1917286c8cd36e9\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(
    str(Path(__file__).with_name("consume-exact-boot-claim.py"))
)
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
