-- Read/write Unreal rendering controls. Do not cache world-owned UObject handles.
local Renderer = {}
local COLLECTION_ASSET = "/Game/BaseMaterials/Resources/PixelFilter_MPC"
local COLLECTION_OBJECT = COLLECTION_ASSET .. ".PixelFilter_MPC"
local MATERIAL_LIBRARY = "/Script/Engine.Default__KismetMaterialLibrary"
local SYSTEM_LIBRARY = "/Script/Engine.Default__KismetSystemLibrary"
local AA_METHODS = { off = 0, fxaa = 1, taa = 2 }
local AA_NAMES = { [0] = "off", [1] = "fxaa", [2] = "taa" }
local GRADIENT_MODES = { original = 0, smooth = 1, biased = 2 }
local AF_BY_TEXTURE_QUALITY = { [0] = 0, [1] = 2, [2] = 4, [3] = 8, [4] = 8 }

local function is_valid(object)
    return object ~= nil and object:IsValid()
end

function Renderer.player(candidate)
    if is_valid(candidate) then
        return candidate
    end
    local player = FindFirstOf("PlayerController")
    return is_valid(player) and player or nil
end

function Renderer.resolve(player)
    local collection = StaticFindObject(COLLECTION_OBJECT)
    if not is_valid(collection) then
        LoadAsset(COLLECTION_ASSET)
        collection = StaticFindObject(COLLECTION_OBJECT)
    end
    assert(is_valid(collection), "PixelFilter_MPC unavailable")
    local parameter_names = {}
    collection.ScalarParameters:ForEach(function(_, parameter)
        parameter_names[parameter:get().ParameterName:ToString()] = true
    end)
    assert(
        parameter_names.QD_SmoothColours and parameter_names.QD_Vignette,
        "Configurable Graphics PAK is not loaded; restart with the new PAK installed"
    )

    local material = StaticFindObject(MATERIAL_LIBRARY)
    local system = StaticFindObject(SYSTEM_LIBRARY)
    assert(is_valid(material) and is_valid(system), "Engine libraries unavailable")
    return { player = player, collection = collection, material = material, system = system }
end

local function game_anisotropy(system)
    local quality = system:GetConsoleVariableIntValue("sg.TextureQuality")
    return AF_BY_TEXTURE_QUALITY[quality] or 8
end

local function read_scalar(context, name)
    return context.material:GetScalarParameterValue(context.player, context.collection, FName(name))
end

function Renderer.read(context)
    local system = context.system
    local method = system:GetConsoleVariableIntValue("r.DefaultFeature.AntiAliasing")
    local anisotropy = system:GetConsoleVariableIntValue("r.MaxAnisotropy")
    local gradient = read_scalar(context, "QD_SmoothColours")
    local values = {
        aa = AA_NAMES[method] or "off",
        af = anisotropy == game_anisotropy(system) and "game" or anisotropy,
        dither = read_scalar(context, "EnableDither") >= 0.5 and 1 or 0,
        gradients = gradient >= 1.5 and "biased" or (gradient >= 0.5 and "smooth" or "original"),
        vignette = read_scalar(context, "QD_Vignette") * 100,
    }
    return values,
        system:GetConsoleVariableIntValue("r.PostProcessAAQuality"),
        system:GetConsoleVariableIntValue("r.TemporalAA.Algorithm")
end

local function set_scalar(context, name, value)
    context.material:SetScalarParameterValue(context.player, context.collection, FName(name), value)
    assert(
        math.abs(read_scalar(context, name) - value) < 0.0001,
        name .. " did not accept requested value"
    )
end

local function set_console_variable(context, name, value)
    context.system:ExecuteConsoleCommand(context.player, name .. " " .. value, context.player)
end

function Renderer.apply(context, state)
    local values = state.values
    -- Damage and InCutscene belong to the game; only our three scalars are written.
    set_scalar(context, "EnableDither", values.dither)
    set_scalar(context, "QD_SmoothColours", GRADIENT_MODES[values.gradients])
    set_scalar(context, "QD_Vignette", values.vignette / 100)
    set_console_variable(context, "r.DefaultFeature.AntiAliasing", AA_METHODS[values.aa])
    set_console_variable(context, "r.PostProcessAAQuality", state.aa_quality)
    if values.aa == "taa" then
        set_console_variable(context, "r.TemporalAA.Algorithm", state.taa_algorithm)
    end
    local anisotropy = values.af == "game" and game_anisotropy(context.system) or values.af
    set_console_variable(context, "r.MaxAnisotropy", anisotropy)
end

function Renderer.report(player, log)
    local collection = StaticFindObject(COLLECTION_OBJECT)
    local material = StaticFindObject(MATERIAL_LIBRARY)
    if is_valid(collection) and is_valid(material) then
        collection.ScalarParameters:ForEach(function(_, parameter)
            local name = parameter:get().ParameterName
            if name:ToString() == "EnableDither" or name:ToString():match("^QD_") then
                local value = material:GetScalarParameterValue(player, collection, name)
                log(name:ToString() .. "=" .. value .. " (runtime)")
            end
        end)
    end
    local system = StaticFindObject(SYSTEM_LIBRARY)
    if is_valid(system) then
        for _, name in ipairs({
            "r.DefaultFeature.AntiAliasing",
            "r.PostProcessAAQuality",
            "r.MaxAnisotropy",
            "r.PostProcessing.DisableMaterials",
        }) do
            log(name .. "=" .. system:GetConsoleVariableIntValue(name))
        end
    end
end

return Renderer
