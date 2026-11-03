-- Native Video options rows are supplied by QueensDomain_GraphicsMenu_P.pak.
-- All callbacks are event driven. Existing game options are ignored.
return function(api)
    local path = "/Game/UI/Menus/OptionsMenu/OptionsMenu_OptionSelect"
    local class = path .. ".OptionsMenu_OptionSelect_C:"
    local choices = {
        preset = { "original", "modern", "custom" },
        aa = { "off", "fxaa", "taa" },
        af = { "game", 1, 2, 4, 8, 16 },
        dither = { 0, 1 },
        gradients = { "original", "smooth", "biased" },
        vignette = { 0, 25, 50, 75, 100 },
    }
    local tracked_controls = {}
    local installed_hooks = {}
    local refreshing = false
    local function is_valid(control)
        return control ~= nil and control:IsValid()
    end
    local function setting_key(control)
        if not is_valid(control) then
            return nil
        end
        local key = control:GetFName():ToString():match("^QDGraphicsControl_(%a+)$")
        if choices[key] and control.SkipSavingOption then
            return key
        end
        return nil
    end
    local function refresh_mod_control(control, key)
        local value = api.get(key)
        local selected = 1
        local exact = false
        for i, v in ipairs(choices[key]) do
            if v == value then
                selected = i
                exact = true
                break
            end
            if key == "vignette" and v < value then
                selected = i
            end
        end
        control.CurrentValue = selected - 1
        control:Refreshtext()
        -- A precise console percentage need not be one of the menu presets.
        if key == "vignette" and not exact and is_valid(control.OptionText) then
            control.OptionText:SetText(FText(tostring(value) .. "% (Custom)"))
        elseif not exact and is_valid(control.OptionText) then
            control.OptionText:SetText(FText(tostring(value) .. " (Custom)"))
        end
    end
    local function refresh_native_control(control, kind)
        local resolution = api.native()
        if not resolution then
            return
        end
        if kind == "retro" then
            if control.CurrentValue ~= resolution.retro then
                control.CurrentValue = resolution.retro
                control:PlayRelevantToggleAnim()
            end
        else
            if control.CurrentValue ~= resolution.scale then
                control.CurrentValue = resolution.scale
                control.Slider_99:SetValue(resolution.scale)
                control:UpdateReadout()
            end
            control:SetIsEnabled(not resolution.retro)
        end
    end
    local function refresh()
        if refreshing then
            return
        end
        refreshing = true
        for address, entry in pairs(tracked_controls) do
            local success, callback_error = pcall(function()
                -- Resolve the widget afresh: never keep a raw UObject across
                -- menu destruction, garbage collection, or a level transition.
                local control = StaticFindObject(entry.path)
                if entry.kind then
                    if
                        not is_valid(control)
                        or control:GetAddress() ~= address
                        or control:GetFullName() ~= entry.name
                    then
                        tracked_controls[address] = nil
                        return
                    end
                    refresh_native_control(control, entry.kind)
                    return
                end
                if setting_key(control) ~= entry.key or control:GetAddress() ~= address then
                    tracked_controls[address] = nil
                    return
                end
                refresh_mod_control(control, entry.key)
            end)
            if not success then
                tracked_controls[address] = nil
                api.log("Menu refresh: " .. tostring(callback_error))
            end
        end
        refreshing = false
    end
    local function on_mod_control_initialized(context)
        local control = context:get()
        local key = setting_key(control)
        if not key then
            return
        end
        local name = control:GetFullName()
        tracked_controls[control:GetAddress()] =
            { key = key, name = name, path = name:match("^%S+ (.+)$") }
        refresh_mod_control(control, key)
        api.log("Menu ready: " .. key .. "=" .. tostring(api.get(key)))
    end
    local function on_mod_control_changed(context)
        if refreshing then
            return
        end
        local control = context:get()
        local key = setting_key(control)
        if not key then
            return
        end
        local entry = tracked_controls[control:GetAddress()]
        -- Construction/reversion must not overwrite saved values.
        if not entry or entry.name ~= control:GetFullName() then
            return
        end
        local value = choices[key][control.CurrentValue + 1]
        if value == nil then
            refresh_mod_control(control, key)
            return
        end
        if value ~= api.get(key) then
            local success, callback_error = pcall(api.change, key, value)
            if not success then
                api.log("Could not save menu selection: " .. tostring(callback_error))
                refresh_mod_control(control, key)
            end
        end
    end
    local function on_native_control_initialized(context)
        local control = context:get()
        if not is_valid(control) then
            return
        end
        local property = control.Property:ToString()
        local kind = property == "LockedResScale" and "retro"
            or (property == "ResScale" and "scale" or nil)
        if not kind then
            return
        end
        local name = control:GetFullName()
        tracked_controls[control:GetAddress()] =
            { kind = kind, name = name, path = name:match("^%S+ (.+)$") }
    end
    local function guard_callback(callback)
        return function(...)
            local success, callback_error = pcall(callback, ...)
            if not success then
                api.log("Menu callback: " .. tostring(callback_error))
            end
        end
    end
    local function setup()
        if
            installed_hooks.Init
            and installed_hooks.SaveProperty
            and installed_hooks.NativeToggle
            and installed_hooks.NativeSlider
        then
            return
        end
        if not is_valid(StaticFindObject(class .. "Init")) then
            LoadAsset(path)
        end
        for name, callback in pairs({
            Init = on_mod_control_initialized,
            SaveProperty = on_mod_control_changed,
        }) do
            if not installed_hooks[name] then
                assert(
                    is_valid(StaticFindObject(class .. name)),
                    "Menu function not loaded: " .. name
                )
                -- Blueprint functions use the second argument as a post-hook.
                RegisterHook(class .. name, guard_callback(callback))
                installed_hooks[name] = true
            end
        end
        for _, entry in ipairs({
            { "NativeToggle", "OptionsMenu_ToggleControl" },
            { "NativeSlider", "OptionsMenu_SliderControl" },
        }) do
            if not installed_hooks[entry[1]] then
                local asset = "/Game/UI/Menus/OptionsMenu/" .. entry[2]
                local callback = asset .. "." .. entry[2] .. "_C:Init"
                if not is_valid(StaticFindObject(callback)) then
                    LoadAsset(asset)
                end
                assert(is_valid(StaticFindObject(callback)), "Native option function unavailable")
                RegisterHook(callback, guard_callback(on_native_control_initialized))
                installed_hooks[entry[1]] = true
            end
        end
        api.log("Native graphics-menu controls connected")
    end
    return { setup = setup, refresh = refresh }
end
