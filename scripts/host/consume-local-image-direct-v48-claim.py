#!/usr/bin/env python3
"""Consume the exact Generation 157 local-image direct-stage claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-direct-v48-generation157-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-direct-v48-generation157-live-v1\n"
    b"candidate=local-image-direct-v48\n"
    b"manifest_sha256=b20c4ae492aecbf000c258456031c30f74847f816af347f40084d6c7569bbba2\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(str(Path(__file__).with_name("consume-exact-boot-claim.py")))
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
