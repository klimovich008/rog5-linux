#!/usr/bin/env python3
"""Consume the exact Generation 158 UFS high-speed direct-stage claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-direct-v49-generation158-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-direct-v49-generation158-live-v1\n"
    b"candidate=local-image-direct-v49\n"
    b"manifest_sha256=ac33ccf7cef86f43834f672d652537b7b5790c8949825f8449088a7721c30459\n"
    b"state=BOOT_CLAIMED\n"
)
consumer = runpy.run_path(str(Path(__file__).with_name("consume-exact-boot-claim.py")))
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
