#!/usr/bin/env python3
"""Consume the exact Generation 155 local-image direct-stage claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-direct-v46-generation155-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-direct-v46-generation155-live-v1\n"
    b"candidate=local-image-direct-v46\n"
    b"manifest_sha256=4872ce3609a87449ab309af201e5b06d8791306eb3240f27fbc0ef2e0fe4ce9b\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(
    str(Path(__file__).with_name("consume-exact-boot-claim.py"))
)
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
