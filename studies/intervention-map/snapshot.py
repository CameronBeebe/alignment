"""Return the frozen archive, restoring it from its two tracked parts if needed."""

import hashlib
import json
from pathlib import Path
from tempfile import NamedTemporaryFile


def archive_path(data):
    target = data / "candidates.jsonl.gz"
    if target.exists():
        return target
    parts = [data / (target.name + suffix) for suffix in (".part1", ".part2")]
    raw = b"".join(part.read_bytes() for part in parts)
    expected = json.loads((data / "audit_design.json").read_text())["frame_sha256"]
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("Archive parts differ from the audited snapshot")
    with NamedTemporaryFile(dir=data, delete=False) as tmp:
        temp_path = Path(tmp.name)
    try:
        temp_path.write_bytes(raw)
        temp_path.replace(target)
    finally:
        temp_path.unlink(missing_ok=True)
    return target


if __name__ == "__main__":
    print(archive_path(Path(__file__).resolve().parent / "data"))
