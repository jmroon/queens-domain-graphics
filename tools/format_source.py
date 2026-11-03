"""Check formatting and lint by default; use --write to apply formatting fixes."""

import argparse
import subprocess
import sys

from bootstrap import bootstrap
from paths import REPO, TOOLS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Format source files and fix safe lint findings."
    )
    args = parser.parse_args()
    bootstrap(("stylua",))
    commands = [
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            *(["--fix"] if args.write else []),
            "tools",
            "tests",
        ],
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            *([] if args.write else ["--check"]),
            "tools",
            "tests",
        ],
        [
            str(TOOLS / "stylua.exe"),
            "--verify",
            *([] if args.write else ["--check"]),
            "src",
            "tests/fixtures",
        ],
    ]
    for command in commands:
        subprocess.run(command, cwd=REPO, check=True)


if __name__ == "__main__":
    main()
