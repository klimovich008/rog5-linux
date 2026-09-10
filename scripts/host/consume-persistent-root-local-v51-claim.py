#!/usr/bin/env python3
"""Consume the exact Generation 160 local-root reboot-module claim."""

from pathlib import Path
import runpy

PROFILE = "persistent-root-local-v51-generation160-live-v1"
EXPECTED = (
    b"format=rog5-temporary-boot-consumption-v1\n"
    b"recovery_profile=persistent-root-local-v51-generation160-live-v1\n"
    b"candidate=persistent-root-local-v51\n"
    b"manifest_sha256=15c928ac9ba0856ad6320d9b7ff4d1b78a0ecc0f4bb62b5cfaeec64978915ca3\n"
    b"state=BOOT_CLAIMED\n"
)
consumer = runpy.run_path(str(Path(__file__).with_name("consume-exact-boot-claim.py")))
consumer["CLAIMS"][PROFILE] = EXPECTED
consumer["consume"](PROFILE)
