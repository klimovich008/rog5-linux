#!/usr/bin/env python3
"""Consume the exact Generation 150 local-image write benchmark claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-write-benchmark-v41-generation150-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-write-benchmark-v41-generation150-live-v1\n"
    b"candidate=local-image-write-benchmark-v41\n"
    b"manifest_sha256=48022ec8595d57b4cb64445fd4802879e0c652a96db31937dc2bd6826a23361a\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(
    str(Path(__file__).with_name("consume-exact-boot-claim.py"))
)
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
