-- Native Video options rows are supplied by QueensDomain_GraphicsMenu_P.pak.
-- All callbacks are event driven. Existing game options are ignored.
return function(api)
    local path="/Game/UI/Menus/OptionsMenu/OptionsMenu_OptionSelect"
    local class=path..".OptionsMenu_OptionSelect_C:"
    local choices={preset={"original","modern","custom"},aa={"off","fxaa","taa"},af={"game",1,2,4,8,16},dither={0,1},
                   gradients={"original","smooth","biased"},vignette={0,25,50,75,100}}
    local controls={};local installed={};local refreshing=false
    local function valid(o)return o~=nil and o:IsValid() end
    local function key_of(o)
        if not valid(o) then return nil end
        local key=o:GetFName():ToString():match("^QDGraphicsControl_(%a+)$")
        if choices[key] and o.SkipSavingOption then return key end
        return nil
    end
    local function update(o,key)
        local value=api.get(key);local selected=1;local exact=false
        for i,v in ipairs(choices[key]) do
            if v==value then selected=i;exact=true;break end
            if key=="vignette" and v<value then selected=i end
        end
        o.CurrentValue=selected-1
        o:Refreshtext()
        -- A precise console percentage need not be one of the menu presets.
        if key=="vignette" and not exact and valid(o.OptionText) then
            o.OptionText:SetText(FText(tostring(value).."% (Custom)"))
        elseif not exact and valid(o.OptionText) then
            o.OptionText:SetText(FText(tostring(value).." (Custom)"))
        end
    end
    local function update_native(o,kind)
        local n=api.native();if not n then return end
        if kind=="retro" then
            if o.CurrentValue~=n.retro then o.CurrentValue=n.retro;o:PlayRelevantToggleAnim()end
        else
            if o.CurrentValue~=n.scale then o.CurrentValue=n.scale;o.Slider_99:SetValue(n.scale);o:UpdateReadout()end
            o:SetIsEnabled(not n.retro)
        end
    end
    local function refresh()
        if refreshing then return end
        refreshing=true
        for id,entry in pairs(controls) do
            local ok,err=pcall(function()
                -- Resolve the widget afresh: never keep a raw UObject across
                -- menu destruction, garbage collection, or a level transition.
                local o=StaticFindObject(entry.path)
                if entry.kind then
                    if not valid(o) or o:GetAddress()~=id or o:GetFullName()~=entry.name then controls[id]=nil;return end
                    update_native(o,entry.kind);return
                end
                if key_of(o)~=entry.key or o:GetAddress()~=id then controls[id]=nil;return end
                update(o,entry.key)
            end)
            if not ok then controls[id]=nil;api.log("Menu refresh: "..tostring(err)) end
        end
        refreshing=false
    end
    local function init(ctx)
        local o=ctx:get();local key=key_of(o);if not key then return end
        local name=o:GetFullName()
        controls[o:GetAddress()]={key=key,name=name,path=name:match("^%S+ (.+)$")}
        update(o,key)
        api.log("Menu ready: "..key.."="..tostring(api.get(key)))
    end
    local function save(ctx)
        if refreshing then return end
        local o=ctx:get();local key=key_of(o);if not key then return end
        local entry=controls[o:GetAddress()]
        -- Construction/reversion must not overwrite saved values.
        if not entry or entry.name~=o:GetFullName() then return end
        local value=choices[key][o.CurrentValue+1]
        if value==nil then update(o,key);return end
        if value~=api.get(key) then
            local ok,err=pcall(api.change,key,value)
            if not ok then api.log("Could not save menu selection: "..tostring(err));update(o,key) end
        end
    end
    local function native_init(ctx)
        local o=ctx:get();if not valid(o) then return end
        local property=o.Property:ToString()
        local kind=property=="LockedResScale" and "retro" or (property=="ResScale" and "scale" or nil)
        if not kind then return end
        local name=o:GetFullName()
        controls[o:GetAddress()]={kind=kind,name=name,path=name:match("^%S+ (.+)$")}
    end
    local function guarded(fn)
        return function(...)
            local ok,err=pcall(fn,...)
            if not ok then api.log("Menu callback: "..tostring(err)) end
        end
    end
    local function setup()
        if installed.Init and installed.SaveProperty and installed.NativeToggle and installed.NativeSlider then return end
        if not valid(StaticFindObject(class.."Init")) then LoadAsset(path) end
        for name,fn in pairs({Init=init,SaveProperty=save}) do
            if not installed[name] then
                assert(valid(StaticFindObject(class..name)),"Menu function not loaded: "..name)
                -- Blueprint functions use the second argument as a post-hook.
                RegisterHook(class..name,guarded(fn));installed[name]=true
            end
        end
        for _,entry in ipairs({{"NativeToggle","OptionsMenu_ToggleControl"},{"NativeSlider","OptionsMenu_SliderControl"}})do
            if not installed[entry[1]]then
                local asset="/Game/UI/Menus/OptionsMenu/"..entry[2]
                local fn=asset.."."..entry[2].."_C:Init"
                if not valid(StaticFindObject(fn))then LoadAsset(asset)end
                assert(valid(StaticFindObject(fn)),"Native option function unavailable")
                RegisterHook(fn,guarded(native_init));installed[entry[1]]=true
            end
        end
        api.log("Native graphics-menu controls connected")
    end
    return {setup=setup,refresh=refresh}
end
