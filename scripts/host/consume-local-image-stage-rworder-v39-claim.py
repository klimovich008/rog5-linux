#!/usr/bin/env python3
"""Consume the exact Generation 148 local-image staging boot claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-stage-rworder-v39-generation148-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-stage-rworder-v39-generation148-live-v1\n"
    b"candidate=local-image-stage-rworder-v39\n"
    b"manifest_sha256=59a2ebc8798354545159cf24a836cc23fe9e9a031eea7c7fe181f8674ee8dab3\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(
    str(Path(__file__).with_name("consume-exact-boot-claim.py"))
)
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
