commands = {}
hooks = {}
messages = {}
writes = 0
consolewrites = 0
queues = 0
objects = {}
available = true
failResolution = false
values = { EnableDither = 1, QD_SmoothColours = 0, QD_Vignette = 1, Damage = 0.33, InCutscene = 1 }
cvars = {
    ["r.DefaultFeature.AntiAliasing"] = 0,
    ["r.PostProcessAAQuality"] = 4,
    ["r.TemporalAA.Algorithm"] = 0,
    ["r.MaxAnisotropy"] = 8,
    ["sg.TextureQuality"] = 3,
}
function print(s)
    table.insert(messages, s)
end
function FName(n)
    return {
        ToString = function()
            return n
        end,
    }
end
function FText(n)
    return n
end
local yes = function()
    return true
end
pc = {
    IsValid = function()
        return available
    end,
}
save = {
    IsValid = yes,
    LockedResScale = true,
    ResScale = 80,
    FOV = 97,
    Vsync = true,
    Brightness = 0.9,
    FramerateCap = 2,
}
stock = { IsValid = yes, LockedResScale = true, ResScale = 80 }
gi = {
    IsValid = yes,
    ActiveSystemSave = save,
    GI_QueueSystemSave = function()
        queues = queues + 1
    end,
}
gi["UpdateScreen%"] = function(self, force)
    assert(self == gi and force)
    if failResolution then
        error("resolution failed")
    end
    cvars["r.ScreenPercentage"] = save.LockedResScale and 37.5 or save.ResScale
end
collection = {
    IsValid = yes,
    ScalarParameters = {
        ForEach = function(self, fn)
            for _, n in ipairs({
                "EnableDither",
                "QD_SmoothColours",
                "QD_Vignette",
                "Damage",
                "InCutscene",
            }) do
                fn(1, {
                    get = function()
                        return { ParameterName = FName(n) }
                    end,
                })
            end
        end,
    },
}
material = {
    IsValid = yes,
    SetScalarParameterValue = function(self, p, c, n, v)
        assert(p == pc)
        assert(n:ToString() ~= "Damage" and n:ToString() ~= "InCutscene")
        values[n:ToString()] = v
        writes = writes + 1
    end,
    GetScalarParameterValue = function(self, p, c, n)
        return values[n:ToString()]
    end,
}
system = {
    IsValid = yes,
    GetConsoleVariableIntValue = function(self, n)
        return cvars[n] or 0
    end,
    ExecuteConsoleCommand = function(self, p, cmd, specific)
        assert(p == pc and specific == pc)
        local k, v = cmd:match("([^ ]+) (.*)")
        cvars[k] = tonumber(v)
        consolewrites = consolewrites + 1
    end,
}
gameplay = {
    IsValid = yes,
    GetGameInstance = function(self, p)
        assert(p == pc)
        return gi
    end,
}
function FindFirstOf(n)
    assert(n == "PlayerController")
    return pc
end
function StaticFindObject(n)
    if n:match("^/Runtime") then
        return objects[n]
    end
    if n:match(":") then
        return { IsValid = yes }
    end
    if n:match("PixelFilter_MPC") then
        return collection
    end
    if n:match("KismetMaterialLibrary") then
        return material
    end
    if n:match("KismetSystemLibrary") then
        return system
    end
    if n:match("GameplayStatics") then
        return gameplay
    end
    if n:match("Default__FS_SystemSave_C") then
        return stock
    end
    error("unexpected object " .. n)
end
function LoadAsset()
    error("unexpected asset load")
end
function RegisterConsoleCommandHandler(n, f)
    commands[n] = f
end
function RegisterHook(n, pre, post)
    hooks[n] = post or pre
end
function RegisterInitGameStatePostHook(fn)
    hooks.world = fn
end
ar = {
    Log = function(self, s)
        table.insert(messages, s)
    end,
}
function run(n, ...)
    commands[n](n, { ... }, ar)
end
function ready()
    hooks["/Script/Engine.PlayerController:ClientRestart"]({
        get = function()
            return pc
        end,
    })
end
function native_changed()
    hooks["/Game/Blueprints/FS_GameInstance.FS_GameInstance_C:ApplyOptions"]()
end
function widget(key, id, kind)
    local o = {
        CurrentValue = 0,
        SkipSavingOption = true,
        IsValid = yes,
        GetAddress = function()
            return id
        end,
    }
    o.GetFName = function()
        return FName("QDGraphicsControl_" .. key)
    end
    o.GetFullName = function()
        return "Widget /Runtime." .. id .. "." .. key
    end
    o.Refreshtext = function(self)
        self.text = tostring(self.CurrentValue)
    end
    o.OptionText = {
        IsValid = yes,
        SetText = function(self, v)
            o.text = v
        end,
    }
    if kind then
        o.Property = FName(kind == "retro" and "LockedResScale" or "ResScale")
        o.PlayRelevantToggleAnim = function(self)
            self.visual = self.CurrentValue
        end
        o.Slider_99 = {
            SetValue = function(self, v)
                o.visual = v
            end,
        }
        o.UpdateReadout = function() end
        o.SetIsEnabled = function(self, v)
            self.enabled = v
        end
    end
    objects[o:GetFullName():match("^%S+ (.+)$")] = o
    local class = kind == "retro" and "OptionsMenu_ToggleControl"
        or (kind == "scale" and "OptionsMenu_SliderControl" or "OptionsMenu_OptionSelect")
    hooks["/Game/UI/Menus/OptionsMenu/" .. class .. "." .. class .. "_C:Init"]({
        get = function()
            return o
        end,
    })
    return o
end
function choose(o, index)
    o.CurrentValue = index
    hooks["/Game/UI/Menus/OptionsMenu/OptionsMenu_OptionSelect.OptionsMenu_OptionSelect_C:SaveProperty"]({
        get = function()
            return o
        end,
    })
end
