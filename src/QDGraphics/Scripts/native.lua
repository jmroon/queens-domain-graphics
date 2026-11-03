-- Use the game's settings object and resolution-update function, not a timer.
return function(log)
    local hooked=false
    local function valid(o)return o~=nil and o:IsValid()end
    local function objects(pc)
        local library=StaticFindObject('/Script/Engine.Default__GameplayStatics')
        assert(valid(library) and valid(pc),'Player/world not ready')
        local gi=library:GetGameInstance(pc)
        assert(valid(gi) and valid(gi.ActiveSystemSave),'Game options not ready')
        return gi,gi.ActiveSystemSave
    end
    local function read(pc)
        local _,save=objects(pc)
        return {retro=save.LockedResScale,scale=save.ResScale}
    end
    local function stock()
        local save=StaticFindObject('/Game/Blueprints/SaveSystem/FS_SystemSave.Default__FS_SystemSave_C')
        assert(valid(save),'Stock game settings not loaded')
        return {retro=save.LockedResScale,scale=save.ResScale}
    end
    local function set(pc,values)
        local gi,save=objects(pc)
        local old={retro=save.LockedResScale,scale=save.ResScale}
        local ok,err=pcall(function()
            save.LockedResScale=values.retro;save.ResScale=values.scale
            gi['UpdateScreen%'](gi,true)
            gi:GI_QueueSystemSave()
        end)
        if not ok then
            save.LockedResScale=old.retro;save.ResScale=old.scale
            pcall(function()gi['UpdateScreen%'](gi,true)end)
            error(err)
        end
    end
    local function setup(callback)
        if hooked then return end
        local path='/Game/Blueprints/FS_GameInstance.FS_GameInstance_C:ApplyOptions'
        if valid(StaticFindObject(path)) then
            RegisterHook(path,function()
                local ok,err=pcall(callback)
                if not ok then log('Game-options callback: '..tostring(err))end
            end)
            hooked=true
        end
    end
    return {read=read,stock=stock,set=set,setup=setup}
end
