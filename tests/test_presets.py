import json
import tempfile
from pathlib import Path

from lupa.lua54 import LuaRuntime

scripts = (Path(__file__).resolve().parents[1] / "src/QDGraphics/Scripts").resolve()
source = (scripts / "main.lua").read_text()
mock = (Path(__file__).parent / "fixtures/unreal.lua").read_text()
with tempfile.TemporaryDirectory() as td:
    settings = (Path(td) / "QDGraphics.ini").resolve()
    code = source.replace(
        next(line for line in source.splitlines() if line.startswith("local SCRIPT_DIR =")),
        "local SCRIPT_DIR = " + json.dumps(str(scripts).replace("\\", "/") + "/"),
    )
    code = code.replace(
        next(line for line in source.splitlines() if line.startswith("local SETTINGS_PATH =")),
        "local SETTINGS_PATH = " + json.dumps(str(settings).replace("\\", "/")),
    )

    def boot(before=""):
        lua = LuaRuntime()
        lua.execute(mock)
        lua.execute(before)
        lua.execute(code)
        return lua

    lua = boot()
    lua.execute("""
        ready()
        assert(writes == 0 and consolewrites == 0 and queues == 0)
    """)
    assert not settings.exists()
    lua.execute(
        """
        preset = widget("preset", 1)
        retro = widget("retro", 2, "retro")
        scale = widget("scale", 3, "scale")
        assert(preset.CurrentValue == 0)
    """
    )
    lua.execute(
        """
        choose(preset, 1)
        assert(save.LockedResScale == false and save.ResScale == 100 and queues == 1)
        assert(values.EnableDither == 0 and values.QD_SmoothColours == 2)
        assert(cvars["r.DefaultFeature.AntiAliasing"] == 2 and cvars["r.MaxAnisotropy"] == 16)
        assert(retro.visual == false and scale.visual == 100 and scale.enabled)
    """
    )
    assert "preset=modern" in settings.read_text()
    lua = boot("save.LockedResScale=false;save.ResScale=100")
    lua.execute("""
        ready()
        assert(values.QD_SmoothColours == 2 and queues == 0)
    """)
    lua.execute(
        """
        preset = widget("preset", 1)
        assert(preset.CurrentValue == 1)
        run("qd_vignette", "70")
        assert(preset.CurrentValue == 2)
    """
    )
    lua.execute(
        """
        run("qd_preset", "modern")
        save.LockedResScale = true
        native_changed()
        assert(preset.CurrentValue == 2 and save.LockedResScale == true and values.EnableDither == 0)
    """
    )
    assert "preset=custom" in settings.read_text()
    lua.execute(
        """
        run("qd_preset", "modern")
        save.ResScale = 75
        native_changed()
        assert(save.ResScale == 75 and preset.CurrentValue == 2)
    """
    )
    lua.execute(
        """
        run("qd_preset", "original")
        assert(values.EnableDither == 1 and values.QD_SmoothColours == 0 and values.QD_Vignette == 1)
        assert(cvars["r.DefaultFeature.AntiAliasing"] == 0 and cvars["r.MaxAnisotropy"] == 8)
        assert(save.LockedResScale and save.ResScale == 80)
    """
    )
    lua.execute(
        """
        local w = writes
        local q = queues
        run("qd_preset", "custom")
        assert(writes == w and queues == q and preset.CurrentValue == 2)
    """
    )
    # Invalid values and failed native operations must not corrupt persisted state.
    saved = settings.read_bytes()
    lua.execute(
        """
        run("qd_preset", "invalid")
        run("qd_gradients", "invalid")
        run("qd_vignette", "101")
        run("qd_af", "17")
    """
    )
    assert settings.read_bytes() == saved
    lua.execute(
        """
        failResolution = true
        run("qd_preset", "modern")
        assert(save.LockedResScale and save.ResScale == 80)
        failResolution = false
    """
    )
    assert settings.read_bytes() == saved
    lua.execute(
        """
        assert(save.FOV == 97 and save.Vsync and save.Brightness == 0.9 and save.FramerateCap == 2)
        assert(values.Damage == 0.33 and values.InCutscene == 1)
    """
    )
    # Renamed preset: existing Enhanced files and commands remain compatible.
    settings.write_text(
        "version=2\nmanaged=1\npreset=enhanced\naa=taa\naf=16\ndither=0\ngradients=biased\nvignette=100\n"
    )
    lua = boot("save.LockedResScale=false;save.ResScale=100")
    lua.execute(
        """
        ready()
        preset = widget("preset", 1)
        assert(preset.CurrentValue == 1 and values.QD_SmoothColours == 2 and queues == 0)
        run("qd_preset", "enhanced")
    """
    )
    assert "preset=modern" in settings.read_text()
    # Version 1 preferences migrate with their values intact and no native save write.
    settings.write_text("version=1\naa=off\naf=16\ndither=0\ngradients=biased\nvignette=35\n")
    lua = boot("save.LockedResScale=false;save.ResScale=92")
    lua.execute(
        """
        ready()
        assert(values.QD_SmoothColours == 2 and values.QD_Vignette == 0.35 and queues == 0)
        assert(cvars["r.PostProcessAAQuality"] == 0 and save.ResScale == 92)
        run("qd_gradients", "smooth")
    """
    )
    assert "version=2" in settings.read_text() and "preset=custom" in settings.read_text()
    # A new user with non-stock settings must see no first-run rendering changes.
    settings.unlink()
    lua = boot(
        "save.LockedResScale=false;save.ResScale=85;cvars['r.DefaultFeature.AntiAliasing']=1;cvars['r.PostProcessAAQuality']=6;cvars['r.MaxAnisotropy']=2"
    )
    lua.execute(
        """
        ready()
        assert(writes == 0 and consolewrites == 0 and queues == 0)
        preset = widget("preset", 1)
        assert(preset.CurrentValue == 2)
        run("qd_dither", "0")
        assert(
            cvars["r.PostProcessAAQuality"] == 6 and cvars["r.MaxAnisotropy"] == 2 and save.ResScale == 85
        )
    """
    )
print(
    "PASS: opt-in first launch, native menu presets, modern/original values, native UI refresh, manual Custom detection, restart persistence, failed-change rollback, legacy migration, unrelated game settings preserved."
)
