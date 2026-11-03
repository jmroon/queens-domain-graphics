"""Run Lua behavior checks, package both variants, then validate their contents."""

import subprocess
import sys

from package_release import package
from paths import REPO


def main():
    for name in ("test_presets.py", "test_menu.py", "test_behavior_parity.py"):
        subprocess.run([sys.executable, str(REPO / "tests" / name)], check=True)
    package()
    subprocess.run([sys.executable, str(REPO / "tests/test_package.py")], check=True)


if __name__ == "__main__":
    main()
