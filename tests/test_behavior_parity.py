"""Compare observable runtime behavior with a trace captured from release 1.0.1.

The fixture records material/CVar/native settings, widget selection, writes, and
exact preference/backup contents. It excludes source line numbers and log paths.
This guards the refactor at its public boundary rather than testing private helpers.
"""

import argparse
import json
import random
import tempfile
from pathlib import Path

from lupa.lua54 import LuaRuntime

REPO = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures"


def boot(scripts, settings_path, before=""):
    source = (scripts / "main.lua").read_text()
    for name, value in (
        ("SCRIPT_DIR", scripts.as_posix() + "/"),
        ("SETTINGS_PATH", settings_path.as_posix()),
    ):
        declaration = next(
            line for line in source.splitlines() if line.startswith(f"local {name} =")
        )
        source = source.replace(declaration, f"local {name} = " + json.dumps(value), 1)
    lua = LuaRuntime()
    lua.execute((FIXTURES / "unreal.lua").read_text())
    lua.execute(before)
    lua.execute(source)
    return lua


def snapshot(lua, settings_path):
    globals = lua.globals()

    def scalar_fields(table):
        return {
            key: value for key, value in table.items() if isinstance(value, (int, float, str, bool))
        }

    return {
        "material": scalar_fields(globals["values"]),
        "console_variables": scalar_fields(globals.cvars),
        "native_settings": scalar_fields(globals.save),
        "writes": [globals.writes, globals.consolewrites, globals.queues],
        "menu_preset": globals.preset.CurrentValue if globals.preset else None,
        "preferences": settings_path.read_text() if settings_path.exists() else None,
        "backup": Path(str(settings_path) + ".bak").read_text()
        if Path(str(settings_path) + ".bak").exists()
        else None,
    }


def capture(scripts):
    trace = []
    with tempfile.TemporaryDirectory() as folder:
        settings = Path(folder) / "QDGraphics.ini"
        lua = boot(scripts, settings)
        actions = [
            "available=false;ready()",
            "available=true;ready();preset=widget('preset',1)",
            "choose(preset,1)",
            "run('qd_vignette','33.5')",
            "run('qd_preset','enhanced')",
            "save.ResScale=87;native_changed()",
            "run('qd_preset','original')",
            "failResolution=true;run('qd_preset','modern');failResolution=false",
            "run('qd_gradients','invalid');run('qd_vignette','101')",
            "hooks.world()",
        ]
        choices = {
            "qd_preset": ["original", "modern", "custom", "enhanced"],
            "qd_aa": ["off", "fxaa", "taa"],
            "qd_af": ["game", "0", "2", "7", "16"],
            "qd_dither": ["0", "1"],
            "qd_gradients": ["original", "smooth", "biased"],
            "qd_vignette": ["0", "12.5", "75", "100"],
        }
        rng = random.Random(20261103)
        for _ in range(40):
            command = rng.choice(list(choices))
            actions.append(f"run('{command}','{rng.choice(choices[command])}')")
        for action in actions:
            lua.execute(action)
            trace.append({"action": action, "state": snapshot(lua, settings)})
        # A new Lua VM must restore the same persisted values without native save writes.
        lua = boot(scripts, settings, "save.LockedResScale=false;save.ResScale=100")
        lua.execute("ready();preset=widget('preset',1)")
        trace.append({"action": "restart", "state": snapshot(lua, settings)})
    return trace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--record-from",
        type=Path,
        help="Explicit baseline source directory; only use the original release to refresh the fixture.",
    )
    args = parser.parse_args()
    fixture = FIXTURES / "behavior-v1.0.1.json"
    if args.record_from:
        fixture.write_text(json.dumps(capture(args.record_from.resolve()), indent=2) + "\n")
        return
    expected = json.loads(fixture.read_text())
    actual = capture(REPO / "src/QDGraphics/Scripts")
    assert len(expected) == len(actual)
    for index, (before, after) in enumerate(zip(expected, actual)):
        assert before == after, (
            f"Behavior changed at action {index}: {before['action']}\nExpected: {before['state']}\nActual: {after['state']}"
        )
    print(
        f"PASS: {len(actual)} runtime transitions match release 1.0.1, including restart and failure rollback."
    )


if __name__ == "__main__":
    main()
