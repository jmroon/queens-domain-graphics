from pathlib import Path

from lupa.lua54 import LuaRuntime

source = (Path(__file__).resolve().parents[1] / "src/QDGraphics/Scripts/menu.lua").read_text()
lua = LuaRuntime()
factory = lua.execute(source)
lua.execute("""
    hooks = {}
    messages = {}
    writes = 0
    loaded = false
    registrations = 0
    objects = {}
    prefs = { aa = "taa", af = 16, dither = 0, gradients = "smooth", vignette = 35 }
    function FText(v)
        return v
    end
    function FName(v)
        return {
            ToString = function()
                return v
            end,
        }
    end
    function LoadAsset(path)
        assert(path == "/Game/UI/Menus/OptionsMenu/OptionsMenu_OptionSelect")
        loaded = true
    end
    function StaticFindObject(path)
        if path:match("^/Runtime") then
            return objects[path]
        end
        return {
            IsValid = function()
                return loaded
            end,
        }
    end
    function RegisterHook(path, fn)
        local key = path:match(":([^:]+)$")
        if not path:match("OptionsMenu_OptionSelect") then
            key = path
        end
        hooks[key] = fn
        registrations = registrations + 1
    end
    api = {
        get = function(k)
            return prefs[k]
        end,
        log = function(v)
            table.insert(messages, v)
        end,
        change = function(k, v)
            writes = writes + 1
            prefs[k] = v
            menu.refresh()
        end,
    }
    function control(key, id)
        local o = { CurrentValue = 0, alive = true, SkipSavingOption = true, key = key, id = id }
        o.IsValid = function(self)
            return self.alive
        end
        o.GetFName = function(self)
            return FName("QDGraphicsControl_" .. self.key)
        end
        o.GetFullName = function(self)
            return "Widget /Runtime." .. self.id .. "." .. self.key
        end
        o.GetAddress = function(self)
            return self.id
        end
        o.Refreshtext = function(self)
            self.text = tostring(self.CurrentValue)
        end
        o.OptionText = {
            IsValid = function()
                return true
            end,
            SetText = function(self, t)
                o.text = t
            end,
        }
        objects[o:GetFullName():match("^%S+ (.+)$")] = o
        return o
    end
    function event(fn, o)
        hooks[fn]({
            get = function()
                return o
            end,
        })
    end
""")
lua.globals().menu = factory(lua.globals().api)
lua.execute("""
    menu.setup()
    menu.setup()
    assert(registrations == 4)
    aa = control("aa", 1)
    af = control("af", 2)
    vig = control("vignette", 3)
    other = control("resolution", 4)
    event("SaveProperty", aa)
    assert(writes == 0) -- not initialized
    event("Init", aa)
    event("Init", af)
    event("Init", vig)
    event("Init", other)
    assert(aa.CurrentValue == 2 and af.CurrentValue == 5 and vig.CurrentValue == 1)
    assert(vig.text == "35% (Custom)" and writes == 0)
    aa.CurrentValue = 1
    event("SaveProperty", aa)
    assert(writes == 1 and prefs.aa == "fxaa")
    vig.CurrentValue = 2
    event("SaveProperty", vig)
    assert(writes == 2 and prefs.vignette == 50)
    event("SaveProperty", other)
    assert(writes == 2)
    prefs.aa = "off"
    menu.refresh()
    assert(aa.CurrentValue == 0 and writes == 2)
    af.alive = false
    menu.refresh()
    assert(writes == 2)
    replacement = control("af", 2)
    event("SaveProperty", replacement)
    assert(writes == 2)
    event("Init", replacement)
    assert(replacement.CurrentValue == 5)
    replacement.CurrentValue = 99
    event("SaveProperty", replacement)
    assert(writes == 2 and replacement.CurrentValue == 5)
    aa.SkipSavingOption = false
    aa.CurrentValue = 2
    event("SaveProperty", aa)
    assert(writes == 2)
    for _, m in ipairs(messages) do
        assert(not m:match("callback:") and not m:match("refresh:"))
    end
    gradient = control("gradients", 5)
    event("Init", gradient)
    assert(gradient.CurrentValue == 1)
    gradient.CurrentValue = 2
    event("SaveProperty", gradient)
    assert(prefs.gradients == "biased" and writes == 3)
    gradient2 = control("gradients", 6)
    event("Init", gradient2)
    assert(gradient2.CurrentValue == 2 and writes == 3)
    prefs.gradients = "original"
    menu.refresh()
    assert(gradient.CurrentValue == 0 and gradient2.CurrentValue == 0)
""")
print(
    "PASS: native callbacks, repeated setup, no save on initialization, unrelated controls ignored, valid changes persist, console refresh, custom percentage, stale widgets discarded, invalid index rejected."
)
