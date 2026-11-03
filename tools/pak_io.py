"""Read PAK entries serially; avoid concurrent Windows extraction file races."""

import subprocess

from paths import REPAK


def read_entry(pak, name):
    return subprocess.run(
        [str(REPAK), "get", str(pak), name], check=True, capture_output=True
    ).stdout


def contents(pak):
    names = subprocess.run(
        [str(REPAK), "list", str(pak)], check=True, capture_output=True, text=True
    ).stdout.splitlines()
    if len(names) != len(set(names)):
        raise RuntimeError("Duplicate archive entry")
    return {name: read_entry(pak, name) for name in names}
