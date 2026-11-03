"""Rebuild into .build/paks and compare with the release assets. No installation."""

import argparse

from pak_io import contents
from paths import PAKS, REPO
from prepare import prepare

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", required=True)
    args = parser.parse_args()
    prepare(args.game_dir)
    import build
    import build_menu

    build.main()
    build_menu.main()
    for p in sorted(PAKS.glob("*.pak")):
        shipped = REPO / "assets" / p.name
        # repak's archive entry order may vary. Compare every extracted byte/path,
        # not archive ordering; the release ZIP itself is deterministic.
        equal = contents(shipped) == contents(p)
        print(
            p.name,
            "asset contents MATCH release" if equal else "asset contents DIFFER from release",
        )
        if not equal:
            raise RuntimeError(
                "Build differs from committed assets. Review before accepting new outputs."
            )
