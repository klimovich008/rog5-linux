#!/usr/bin/env python3
"""Consume the exact Generation 156 local-image direct-stage claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-direct-v47-generation156-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-direct-v47-generation156-live-v1\n"
    b"candidate=local-image-direct-v47\n"
    b"manifest_sha256=d219de4fbfe7107c90c9fc2f8d92337f7cad916d4c3c767b55d2d4dd6a101a86\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(
    str(Path(__file__).with_name("consume-exact-boot-claim.py"))
)
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
