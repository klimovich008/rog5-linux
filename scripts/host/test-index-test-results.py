#!/usr/bin/env python3
"""test-results/README.md lists every dated result (regenerate with scripts/host/index-test-results.py)."""
from pathlib import Path
import subprocess
import sys

tool = Path(__file__).with_name('index-test-results.py')
sys.exit(subprocess.run([sys.executable, str(tool), '--check']).returncode)
