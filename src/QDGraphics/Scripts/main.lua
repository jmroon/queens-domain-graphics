-- Entry point: coordinate preferences, rendering, native options, and menu events.
local SCRIPT_DIR = debug.getinfo(1, "S").source:sub(2):match("^(.*[/\\])")
local SETTINGS_PATH = os.getenv("LOCALAPPDATA") .. "\\QueensDomain\\Saved\\QDGraphics.ini"
local Preferences = dofile(SCRIPT_DIR .. "preferences.lua")
local Renderer = dofile(SCRIPT_DIR .. "renderer.lua")

local function log(message, console)
    local line = "[QD Graphics] " .. message
    print(line .. "\n")
    if console then
        console:Log(line)
    end
end

local state = Preferences.load(SETTINGS_PATH, log)
local native = dofile(SCRIPT_DIR .. "native.lua")(log)
local initialized = false
local menu

local function persist()
    Preferences.save(SETTINGS_PATH, state)
end

local function refresh_menu()
    if menu and menu.refresh then
        menu.refresh()
    end
end

local function native_values()
    local player = Renderer.player()
    if not player then
        return nil
    end
    local success, values = pcall(native.read, player)
    return success and values or nil
end

local function preset_resolution(preset)
    return preset == "modern" and { retro = false, scale = 100 } or native.stock()
end

local function adopt_existing_settings(context)
    state.values, state.aa_quality, state.taa_algorithm = Renderer.read(context)
    if not initialized then
        local resolution = native.read(context.player)
        local stock = native.stock()
        local matches_original = Preferences.is_original(state.values)
            and resolution.retro == stock.retro
            and resolution.scale == stock.scale
        state.preset = matches_original and "original" or "custom"
    end
end

local function apply(candidate)
    local player = Renderer.player(candidate)
    if not player then
        return false, "waiting for a player/world"
    end
    local context = Renderer.resolve(player)
    if not state.managed then
        -- Fresh installs observe existing values until the user chooses an override.
        adopt_existing_settings(context)
        initialized = true
        return true, "existing settings preserved (no overrides selected)"
    end
    initialized = true
    Renderer.apply(context, state)
    return true, "applied"
end

local function reconcile_resolution()
    if state.preset == "custom" then
        return
    end
    local current = native_values()
    if not current then
        return
    end
    local expected = preset_resolution(state.preset)
    if current.retro ~= expected.retro or math.abs(current.scale - expected.scale) > 0.01 then
        state.preset = "custom"
        persist()
    end
end

local function select_preset(value)
    local target_resolution, previous_resolution
    if value ~= "custom" then
        assert(Renderer.player(), "Player/world not ready")
        previous_resolution = native.read(Renderer.player())
        target_resolution = preset_resolution(value)
        state.values = Preferences.preset_values(value)
        state.managed = true
        state.aa_quality = state.values.aa == "off" and 0 or 4
        state.taa_algorithm = 0
    end
    state.preset = value
    return target_resolution, previous_resolution
end

local function select_individual_setting(key, value)
    local parsed = Preferences.parse(key, value)
    assert(parsed ~= nil, "Invalid " .. key .. " value")
    state.values[key] = parsed
    state.managed = true
    state.preset = "custom"
    if key == "aa" then
        state.aa_quality = parsed == "off" and 0 or 4
        state.taa_algorithm = 0
    end
end

local function restore_after_failed_change(previous_state, previous_resolution)
    state = previous_state
    if previous_resolution then
        pcall(native.set, Renderer.player(), previous_resolution)
    end
    -- Recovery is best effort: preserve the original error for the user.
    pcall(apply)
    pcall(persist)
end

local function change(key, value, console)
    if not initialized then
        local ready = apply()
        assert(ready, "Load a game world first")
    end
    local previous_state = Preferences.snapshot(state)
    local target_resolution, previous_resolution
    if key == "preset" then
        value = Preferences.normalize_preset(value)
        assert(value, "Expected original, modern, or custom")
        target_resolution, previous_resolution = select_preset(value)
    else
        select_individual_setting(key, value)
    end

    local success, change_error = pcall(function()
        persist()
        if target_resolution then
            native.set(Renderer.player(), target_resolution)
        end
        -- Choosing Custom labels the current picture; it does not apply a preset.
        if key ~= "preset" or value ~= "custom" then
            apply()
        end
    end)
    if not success then
        restore_after_failed_change(previous_state, previous_resolution)
        error("Setting change failed: " .. tostring(change_error))
    end
    log(key .. "=" .. tostring(value) .. " saved; applied", console)
    refresh_menu()
end

local function status(console)
    log("preset=" .. state.preset .. "; managed=" .. tostring(state.managed), console)
    local resolution = native_values()
    if resolution then
        log(
            "Retro Resolution="
                .. tostring(resolution.retro)
                .. "; resolution scale="
                .. resolution.scale,
            console
        )
    end
    for _, key in ipairs(Preferences.ORDER) do
        log(key .. "=" .. tostring(state.values[key]) .. " (saved preference)", console)
    end
    log("Settings file: " .. SETTINGS_PATH, console)
    local player = Renderer.player()
    if not player then
        log("No player/world yet", console)
        return
    end
    Renderer.report(player, function(message)
        log(message, console)
    end)
end

local function register_command(name, callback)
    RegisterConsoleCommandHandler(name, function(_, parameters, console)
        local success, command_error = pcall(callback, parameters, console)
        if not success then
            log("Error: " .. tostring(command_error), console)
        end
        return true
    end)
end

local function register_commands()
    register_command("qd_help", function(_, console)
        log(
            "Persistent: qd_preset original|modern|custom; qd_aa off|fxaa|taa; qd_af game|1|2|4|8|16; qd_dither 0|1",
            console
        )
        log("qd_gradients original|smooth|biased; qd_vignette 0..100 (100 = original)", console)
        log("qd_status; qd_apply; qd_defaults. Changes save immediately.", console)
    end)
    register_command("qd_status", function(_, console)
        status(console)
    end)
    for _, key in ipairs(Preferences.ORDER) do
        register_command("qd_" .. key, function(parameters, console)
            assert(#parameters == 1, "Expected one value; use qd_help")
            change(key, parameters[1], console)
        end)
    end
    register_command("qd_apply", function(_, console)
        local _, reason = apply()
        log(reason, console)
    end)
    register_command("qd_preset", function(parameters, console)
        assert(#parameters == 1, "Expected original, modern, or custom")
        change("preset", parameters[1]:lower(), console)
    end)
    register_command("qd_defaults", function(_, console)
        change("preset", "original", console)
    end)
end

local function on_game_options_changed()
    reconcile_resolution()
    apply()
    refresh_menu()
end

local function on_world_ready(candidate, label)
    native.setup(on_game_options_changed)
    local success, applied, reason = pcall(apply, candidate)
    if not success then
        log(label .. ": " .. tostring(applied))
    elseif applied then
        log(label .. ": " .. tostring(reason))
    end
    if success and applied then
        local reconciled, reconcile_error = pcall(reconcile_resolution)
        if not reconciled then
            log("Preset check: " .. tostring(reconcile_error))
        end
    end
    if menu and menu.setup then
        local connected, setup_error = pcall(menu.setup)
        if not connected then
            log("Menu setup: " .. tostring(setup_error))
        end
    end
end

local function load_menu()
    local menu_file = SCRIPT_DIR and io.open(SCRIPT_DIR .. "menu.lua", "r")
    if not menu_file then
        return
    end
    menu_file:close()
    local loaded, factory = pcall(dofile, SCRIPT_DIR .. "menu.lua")
    if not loaded then
        log("Menu extension unavailable: " .. tostring(factory))
        return
    end
    menu = factory({
        get = function(key)
            return key == "preset" and state.preset or state.values[key]
        end,
        change = change,
        log = log,
        apply = apply,
        native = native_values,
    })
end

register_commands()
-- Native functions use an explicit post-hook; Blueprint hooks in menu.lua differ.
RegisterHook("/Script/Engine.PlayerController:ClientRestart", function() end, function(context)
    on_world_ready(context:get(), "Player ready")
end)
RegisterInitGameStatePostHook(function()
    on_world_ready(nil, "World initialized")
end)
load_menu()
log("Persistent controls registered. Type qd_help. No timers or per-frame callbacks.")
