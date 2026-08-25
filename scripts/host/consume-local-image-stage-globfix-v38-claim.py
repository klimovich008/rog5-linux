#!/usr/bin/env python3
"""Consume the exact Generation 147 local-image staging boot claim."""

from pathlib import Path
import runpy

PROFILE = "local-image-stage-globfix-v38-generation147-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=local-image-stage-globfix-v38-generation147-live-v1\n"
    b"candidate=local-image-stage-globfix-v38\n"
    b"manifest_sha256=1930e049f1f180e90cfcb8e877cb1108e1f1b9a15f3beaf421f4aeac3901a1e6\n"
    b"state=BOOT_CLAIMED\n"
)

consumer = runpy.run_path(
    str(Path(__file__).with_name("consume-exact-boot-claim.py"))
)
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
