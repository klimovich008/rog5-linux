#!/usr/bin/env python3
"""Count a direct-image stream without storing it."""

from pathlib import Path
import sys


state = Path(sys.argv[1])
extent_map = Path(sys.argv[2])
action = sys.argv[3]
records = {
    int(fields[0]): int(fields[2])
    for line in extent_map.read_text(encoding="ascii").splitlines()[8:]
    if (fields := line.split("\t"))
}
if action == "prepare":
    assert len(sys.argv) == 4
    state.write_text("1\n", encoding="ascii")
    print("format=rog5-local-image-direct-stage-v1\nstate=READY\nextents=37")
elif action == "write":
    index = int(sys.argv[4])
    assert int(state.read_text(encoding="ascii")) == index
    expected = records[index] * 4096
    received = 0
    while chunk := sys.stdin.buffer.read(1_048_576):
        received += len(chunk)
    assert received == expected
    state.write_text(f"{index + 1}\n", encoding="ascii")
    print(
        "format=rog5-local-image-direct-extent-v1\n"
        f"index={index}\nblocks={records[index]}\nresult=PASS"
    )
elif action == "finalize":
    assert len(sys.argv) == 4 and int(state.read_text(encoding="ascii")) == 38
    print(
        "format=rog5-local-image-direct-final-v1\n"
        "image_size=17179869184\nextents=37\nresult=PASS"
    )
else:
    raise AssertionError(action)
