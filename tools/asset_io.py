"""Shared UAssetGUI serialization and original-asset roundtrip checks."""

import json
import subprocess
from pathlib import Path

from paths import UASSET


def asset_write(data: dict, path: Path) -> None:
    """Write cooked uasset/uexp files, removing only our temporary JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    j = path.with_suffix(".json")
    j.write_text(json.dumps(data, indent=2))
    subprocess.run([str(UASSET), "fromjson", str(j), str(path)], check=True)
    assert path.exists() and path.with_suffix(".uexp").exists()
    j.unlink()  # only the generated staging JSON, never game data


def verify_original_roundtrip(data: dict, original_path: Path, roundtrip_path: Path) -> None:
    """Require byte-identical serialization before editing any cooked asset."""
    asset_write(data, roundtrip_path)
    for extension in (".uasset", ".uexp"):
        assert (
            roundtrip_path.with_suffix(extension).read_bytes()
            == original_path.with_suffix(extension).read_bytes()
        ), f"Original roundtrip failed: {original_path.name}{extension}"
