#!/usr/bin/env python3
"""Consume the exact Generation 154 local-image write benchmark claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-write-benchmark-v45-generation154-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-write-benchmark-v45-generation154-live-v1\n"
    b"candidate=local-image-write-benchmark-v45\n"
    b"manifest_sha256=14741fb36498f039e1711719ad542fa88e5b3b990a147d0877dbd8b400b8f25e\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(
    str(Path(__file__).with_name("consume-exact-boot-claim.py"))
)
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
