-- Use the game's settings object and resolution-update function, not a timer.
return function(log)
    local hook_installed = false
    local function is_valid(o)
        return o ~= nil and o:IsValid()
    end
    local function get_game_options(player)
        local library = StaticFindObject("/Script/Engine.Default__GameplayStatics")
        assert(is_valid(library) and is_valid(player), "Player/world not ready")
        local game_instance = library:GetGameInstance(player)
        assert(
            is_valid(game_instance) and is_valid(game_instance.ActiveSystemSave),
            "Game options not ready"
        )
        return game_instance, game_instance.ActiveSystemSave
    end
    local function read(player)
        local _, system_save = get_game_options(player)
        return { retro = system_save.LockedResScale, scale = system_save.ResScale }
    end
    local function stock()
        local system_save =
            StaticFindObject("/Game/Blueprints/SaveSystem/FS_SystemSave.Default__FS_SystemSave_C")
        assert(is_valid(system_save), "Stock game settings not loaded")
        return { retro = system_save.LockedResScale, scale = system_save.ResScale }
    end
    local function set(player, values)
        local game_instance, system_save = get_game_options(player)
        local previous = { retro = system_save.LockedResScale, scale = system_save.ResScale }
        local success, update_error = pcall(function()
            system_save.LockedResScale = values.retro
            system_save.ResScale = values.scale
            game_instance["UpdateScreen%"](game_instance, true)
            game_instance:GI_QueueSystemSave()
        end)
        if not success then
            system_save.LockedResScale = previous.retro
            system_save.ResScale = previous.scale
            pcall(function()
                game_instance["UpdateScreen%"](game_instance, true)
            end)
            error(update_error)
        end
    end
    local function setup(callback)
        if hook_installed then
            return
        end
        local path = "/Game/Blueprints/FS_GameInstance.FS_GameInstance_C:ApplyOptions"
        if is_valid(StaticFindObject(path)) then
            RegisterHook(path, function()
                local success, update_error = pcall(callback)
                if not success then
                    log("Game-options callback: " .. tostring(update_error))
                end
            end)
            hook_installed = true
        end
    end
    return { read = read, stock = stock, set = set, setup = setup }
end
