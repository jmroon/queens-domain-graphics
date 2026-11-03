-- QDGraphics: persistent, event-driven graphics controls. No timer or per-frame work.
local SCRIPT_DIR = debug.getinfo(1, "S").source:sub(2):match("^(.*[/\\])")
local SETTINGS_PATH = os.getenv("LOCALAPPDATA") .. "\\QueensDomain\\Saved\\QDGraphics.ini"
local COLLECTION = "/Game/BaseMaterials/Resources/PixelFilter_MPC.PixelFilter_MPC"
local defaults = {aa="off", af="game", dither=1, gradients="original", vignette=100}
local modern = {aa="taa", af=16, dither=0, gradients="biased", vignette=100}
local managed, initialized, preset = false, false, "custom"
local aaQuality, taaAlgorithm = 4, 0
local order = {"aa","af","dither","gradients","vignette"}
local settings = {}; for k,v in pairs(defaults) do settings[k]=v end
local function valid(o) return o ~= nil and o:IsValid() end
local function log(message, ar)
    local line="[QD Graphics] "..message
    print(line.."\n")
    if ar then ar:Log(line) end
end
local function parse(key, value)
    value=tostring(value):lower()
    if key=="aa" and (value=="off" or value=="fxaa" or value=="taa") then return value end
    if key=="gradients" and (value=="original" or value=="smooth" or value=="biased") then return value end
    if key=="af" and value=="game" then return value end
    local n=tonumber(value)
    if not n or n~=n or n==math.huge or n==-math.huge then return nil end
    if key=="af" and n>=0 and n<=16 and n==math.floor(n) then return n end
    if key=="dither" and (n==0 or n==1) then return n end
    if key=="vignette" and n>=0 and n<=100 then return n end
end
do
    local f=io.open(SETTINGS_PATH,"r")
    if f then
        local version=1;local explicitlyManaged=nil;local count=0
        for line in f:lines() do
            local k,v=line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
            if k and defaults[k]~=nil then
                local p=parse(k,v)
                if p~=nil then settings[k]=p;count=count+1 else log("Ignoring invalid saved value: "..k) end
            elseif k=="version" then version=tonumber(v) or 1
            elseif k=="managed" then explicitlyManaged=v=="1"
            elseif k=="preset" and (v=="original" or v=="modern" or v=="enhanced" or v=="custom") then preset=v=="enhanced" and "modern" or v
            elseif k=="aa_quality" and tonumber(v) then aaQuality=math.max(0,math.min(6,tonumber(v)))
            elseif k=="taa_algorithm" and tonumber(v) then taaAlgorithm=tonumber(v)==1 and 1 or 0 end
        end
        f:close()
        managed=(version==1 and count>0) or (version>=2 and explicitlyManaged==true)
        if version==1 then aaQuality=settings.aa=="off" and 0 or 4 end
        -- Legacy files own these five settings; keep their saved values intact.
    end
end
local function persist()
    local tmp=SETTINGS_PATH..".tmp";local backup=SETTINGS_PATH..".bak"
    local f,err=io.open(tmp,"w");assert(f,err)
    local ok,writeerr=f:write("; Queen's Domain graphics mod preferences\nversion=2\nmanaged="..(managed and "1" or "0").."\npreset="..preset.."\naa_quality="..aaQuality.."\ntaa_algorithm="..taaAlgorithm.."\n")
    for _,k in ipairs(order) do
        if ok then ok,writeerr=f:write(k.."="..tostring(settings[k]).."\n") end
    end
    local closed,closeerr=f:close();assert(ok and closed,writeerr or closeerr)
    local existing=io.open(SETTINGS_PATH,"r")
    if existing then existing:close();os.remove(backup);assert(os.rename(SETTINGS_PATH,backup)) end
    local moved,moveerr=os.rename(tmp,SETTINGS_PATH)
    if not moved then if existing then os.rename(backup,SETTINGS_PATH) end;error(moveerr) end
end
local function context(candidate)
    if valid(candidate) then return candidate end
    local pc=FindFirstOf("PlayerController")
    if valid(pc) then return pc end
    return nil
end
local function set_scalar(pc, collection, library, name, value)
    library:SetScalarParameterValue(pc,collection,FName(name),value)
    local after=library:GetScalarParameterValue(pc,collection,FName(name))
    assert(math.abs(after-value)<0.0001,name.." did not accept requested value")
end
local native=dofile(SCRIPT_DIR.."native.lua")(log)
local function game_af(system)
    return ({[0]=0,[1]=2,[2]=4,[3]=8,[4]=8})[system:GetConsoleVariableIntValue("sg.TextureQuality")] or 8
end
local function apply(candidate)
    local pc=context(candidate)
    if not pc then return false,"waiting for a player/world" end
    local collection=StaticFindObject(COLLECTION)
    if not valid(collection) then
        LoadAsset("/Game/BaseMaterials/Resources/PixelFilter_MPC")
        collection=StaticFindObject(COLLECTION)
    end
    assert(valid(collection),"PixelFilter_MPC unavailable")
    local names={}
    collection.ScalarParameters:ForEach(function(_,v) names[v:get().ParameterName:ToString()]=true end)
    assert(names.QD_SmoothColours and names.QD_Vignette,"Configurable Graphics PAK is not loaded; restart with the new PAK installed")
    local material=StaticFindObject("/Script/Engine.Default__KismetMaterialLibrary")
    local system=StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    assert(valid(material) and valid(system),"Engine libraries unavailable")
    if not managed then
        local method=system:GetConsoleVariableIntValue("r.DefaultFeature.AntiAliasing")
        settings.aa=({[0]="off",[1]="fxaa",[2]="taa"})[method] or "off"
        aaQuality=system:GetConsoleVariableIntValue("r.PostProcessAAQuality")
        taaAlgorithm=system:GetConsoleVariableIntValue("r.TemporalAA.Algorithm")
        local af=system:GetConsoleVariableIntValue("r.MaxAnisotropy")
        settings.af=af==game_af(system) and "game" or af
        settings.dither=material:GetScalarParameterValue(pc,collection,FName("EnableDither"))>=0.5 and 1 or 0
        local gradient=material:GetScalarParameterValue(pc,collection,FName("QD_SmoothColours"))
        settings.gradients=gradient>=1.5 and "biased" or (gradient>=0.5 and "smooth" or "original")
        settings.vignette=material:GetScalarParameterValue(pc,collection,FName("QD_Vignette"))*100
        if not initialized then
            local same=true;for k,v in pairs(defaults)do if settings[k]~=v then same=false end end
            local n=native.read(pc);local stock=native.stock()
            preset=same and n.retro==stock.retro and n.scale==stock.scale and "original" or "custom"
        end
        initialized=true
        return true,"existing settings preserved (no overrides selected)"
    end
    initialized=true
    set_scalar(pc,collection,material,"EnableDither",settings.dither)
    set_scalar(pc,collection,material,"QD_SmoothColours",({original=0,smooth=1,biased=2})[settings.gradients])
    set_scalar(pc,collection,material,"QD_Vignette",settings.vignette/100)
    local method=({off=0,fxaa=1,taa=2})[settings.aa]
    system:ExecuteConsoleCommand(pc,"r.DefaultFeature.AntiAliasing "..method,pc)
    system:ExecuteConsoleCommand(pc,"r.PostProcessAAQuality "..aaQuality,pc)
    if settings.aa=="taa" then system:ExecuteConsoleCommand(pc,"r.TemporalAA.Algorithm "..taaAlgorithm,pc) end
    system:ExecuteConsoleCommand(pc,"r.MaxAnisotropy "..(settings.af=="game" and game_af(system) or settings.af),pc)
    return true,"applied"
end
local menu
local function clone(t)local r={};for k,v in pairs(t)do r[k]=v end;return r end
local function native_values()
    local pc=context();if not pc then return nil end
    local ok,result=pcall(native.read,pc);return ok and result or nil
end
local function reconcile()
    if preset=="custom" then return end
    local n=native_values();if not n then return end
    local expected=preset=="modern" and {retro=false,scale=100} or native.stock()
    if n.retro~=expected.retro or math.abs(n.scale-expected.scale)>0.01 then
        preset="custom";persist()
    end
end
local function change(key,value,ar)
    if not initialized then local ready=apply();assert(ready,"Load a game world first") end
    local old={settings=clone(settings),managed=managed,preset=preset,quality=aaQuality,algorithm=taaAlgorithm}
    local nativeTarget,oldNative
    if key=="preset" then
        if value=="enhanced" then value="modern" end -- Compatibility with earlier console commands.
        assert(value=="original" or value=="modern" or value=="custom","Expected original, modern, or custom")
        if value~="custom" then
            assert(context(),"Player/world not ready")
            oldNative=native.read(context())
            nativeTarget=value=="modern" and {retro=false,scale=100} or native.stock()
            settings=clone(value=="modern" and modern or defaults)
            managed=true;aaQuality=settings.aa=="off" and 0 or 4;taaAlgorithm=0
        end
        preset=value
    else
        local parsed=parse(key,value);assert(parsed~=nil,"Invalid "..key.." value")
        settings[key]=parsed;managed=true;preset="custom"
        if key=="aa" then aaQuality=parsed=="off" and 0 or 4;taaAlgorithm=0 end
    end
    local ok,err=pcall(function()
        persist()
        if nativeTarget then native.set(context(),nativeTarget) end
        if key~="preset" or value~="custom" then apply() end
    end)
    if not ok then
        settings=old.settings;managed=old.managed;preset=old.preset;aaQuality=old.quality;taaAlgorithm=old.algorithm
        if nativeTarget and oldNative then pcall(native.set,context(),oldNative)end
        pcall(apply)
        pcall(persist)
        error("Setting change failed: "..tostring(err))
    end
    log(key.."="..tostring(value).." saved; applied",ar)
    if menu and menu.refresh then menu.refresh() end
end
local function status(ar)
    log("preset="..preset.."; managed="..tostring(managed),ar)
    local n=native_values();if n then log("Retro Resolution="..tostring(n.retro).."; resolution scale="..n.scale,ar)end
    for _,key in ipairs(order) do log(key.."="..tostring(settings[key]).." (saved preference)",ar) end
    log("Settings file: "..SETTINGS_PATH,ar)
    local pc=context()
    if not pc then log("No player/world yet",ar);return end
    local c=StaticFindObject(COLLECTION);local m=StaticFindObject("/Script/Engine.Default__KismetMaterialLibrary")
    if valid(c) and valid(m) then
        c.ScalarParameters:ForEach(function(_,v)
            local name=v:get().ParameterName
            if name:ToString()=="EnableDither" or name:ToString():match("^QD_") then
                log(name:ToString().."="..m:GetScalarParameterValue(pc,c,name).." (runtime)",ar)
            end
        end)
    end
    local sys=StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    if valid(sys) then
        for _,name in ipairs({"r.DefaultFeature.AntiAliasing","r.PostProcessAAQuality","r.MaxAnisotropy","r.PostProcessing.DisableMaterials"}) do
            log(name.."="..sys:GetConsoleVariableIntValue(name),ar)
        end
    end
end
local function register(name,fn)
    RegisterConsoleCommandHandler(name,function(_,params,ar)
        local ok,err=pcall(fn,params,ar)
        if not ok then log("Error: "..tostring(err),ar) end
        return true
    end)
end
register("qd_help",function(_,ar)
    log("Persistent: qd_preset original|modern|custom; qd_aa off|fxaa|taa; qd_af game|1|2|4|8|16; qd_dither 0|1",ar)
    log("qd_gradients original|smooth|biased; qd_vignette 0..100 (100 = original)",ar)
    log("qd_status; qd_apply; qd_defaults. Changes save immediately.",ar)
end)
register("qd_status",function(_,ar) status(ar) end)
for _,key in ipairs(order) do
    register("qd_"..key,function(params,ar)
        assert(#params==1,"Expected one value; use qd_help")
        change(key,params[1],ar)
    end)
end
register("qd_apply",function(_,ar) local _,why=apply();log(why,ar) end)
register("qd_preset",function(params,ar)
    assert(#params==1,"Expected original, modern, or custom");change("preset",params[1]:lower(),ar)
end)
register("qd_defaults",function(_,ar)change("preset","original",ar)end)
local function event_apply(candidate,label)
    native.setup(function()reconcile();apply();if menu and menu.refresh then menu.refresh()end end)
    local ok,result,why=pcall(apply,candidate)
    if not ok then log(label..": "..tostring(result))
    elseif result then log(label..": "..tostring(why)) end
    if ok and result then local success,err=pcall(reconcile);if not success then log("Preset check: "..tostring(err))end end
    if menu and menu.setup then
        local success,err=pcall(menu.setup)
        if not success then log("Menu setup: "..tostring(err)) end
    end
end
RegisterHook("/Script/Engine.PlayerController:ClientRestart",function() end,function(ctx)
    event_apply(ctx:get(),"Player ready")
end)
RegisterInitGameStatePostHook(function(_)
    event_apply(nil,"World initialized")
end)
local menuFile=SCRIPT_DIR and io.open(SCRIPT_DIR.."menu.lua","r")
if menuFile then
    menuFile:close()
    local ok,factory=pcall(dofile,SCRIPT_DIR.."menu.lua")
    if ok then menu=factory({get=function(k)if k=="preset" then return preset end;return settings[k]end,change=change,log=log,apply=apply,native=native_values})
    else log("Menu extension unavailable: "..tostring(factory)) end
end
log("Persistent controls registered. Type qd_help. No timers or per-frame callbacks.")
