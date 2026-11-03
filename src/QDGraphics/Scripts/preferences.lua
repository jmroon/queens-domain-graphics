-- Validated preferences and atomic file persistence. No Unreal objects belong here.
local Preferences = {}

Preferences.ORDER = { "aa", "af", "dither", "gradients", "vignette" }
local PRESETS = {
    original = { aa = "off", af = "game", dither = 1, gradients = "original", vignette = 100 },
    modern = { aa = "taa", af = 16, dither = 0, gradients = "biased", vignette = 100 },
}

function Preferences.copy(values)
    local result = {}
    for key, value in pairs(values) do
        result[key] = value
    end
    return result
end

function Preferences.preset_values(name)
    return Preferences.copy(PRESETS[name])
end

function Preferences.is_original(values)
    for key, value in pairs(PRESETS.original) do
        if values[key] ~= value then
            return false
        end
    end
    return true
end

function Preferences.normalize_preset(value)
    if value == "enhanced" then
        return "modern" -- Keep early saved files and console commands compatible.
    end
    if value == "original" or value == "modern" or value == "custom" then
        return value
    end
    return nil
end

function Preferences.parse(key, value)
    value = tostring(value):lower()
    if key == "aa" and (value == "off" or value == "fxaa" or value == "taa") then
        return value
    end
    if key == "gradients" and (value == "original" or value == "smooth" or value == "biased") then
        return value
    end
    if key == "af" and value == "game" then
        return value
    end

    local number = tonumber(value)
    if not number or number ~= number or number == math.huge or number == -math.huge then
        return nil
    end
    if key == "af" and number >= 0 and number <= 16 and number == math.floor(number) then
        return number
    end
    if key == "dither" and (number == 0 or number == 1) then
        return number
    end
    if key == "vignette" and number >= 0 and number <= 100 then
        return number
    end
    return nil
end

function Preferences.snapshot(state)
    local result = Preferences.copy(state)
    result.values = Preferences.copy(state.values)
    return result
end

local function read_metadata(state, metadata, key, value)
    if key == "version" then
        metadata.version = tonumber(value) or 1
    elseif key == "managed" then
        metadata.explicitly_managed = value == "1"
    elseif key == "preset" and Preferences.normalize_preset(value) then
        state.preset = Preferences.normalize_preset(value)
    elseif key == "aa_quality" and tonumber(value) then
        state.aa_quality = math.max(0, math.min(6, tonumber(value)))
    elseif key == "taa_algorithm" and tonumber(value) then
        state.taa_algorithm = tonumber(value) == 1 and 1 or 0
    end
end

function Preferences.load(path, log)
    local state = {
        values = Preferences.preset_values("original"),
        managed = false,
        preset = "custom",
        aa_quality = 4,
        taa_algorithm = 0,
    }
    local file = io.open(path, "r")
    if not file then
        return state
    end

    local metadata = { version = 1, valid_values = 0 }
    for line in file:lines() do
        local key, value = line:match("^%s*([%w_]+)%s*=%s*(.-)%s*$")
        if key and PRESETS.original[key] ~= nil then
            local parsed = Preferences.parse(key, value)
            if parsed ~= nil then
                state.values[key] = parsed
                metadata.valid_values = metadata.valid_values + 1
            else
                log("Ignoring invalid saved value: " .. key)
            end
        else
            read_metadata(state, metadata, key, value)
        end
    end
    file:close()

    -- Version 1 files already own these settings. Version 2 makes ownership explicit.
    state.managed = (metadata.version == 1 and metadata.valid_values > 0)
        or (metadata.version >= 2 and metadata.explicitly_managed == true)
    if metadata.version == 1 then
        state.aa_quality = state.values.aa == "off" and 0 or 4
    end
    return state
end

local function write_preferences(path, state)
    local file, open_error = io.open(path, "w")
    assert(file, open_error)
    local header = "; Queen's Domain graphics mod preferences\nversion=2\nmanaged="
        .. (state.managed and "1" or "0")
        .. "\npreset="
        .. state.preset
        .. "\naa_quality="
        .. state.aa_quality
        .. "\ntaa_algorithm="
        .. state.taa_algorithm
        .. "\n"
    local written, write_error = file:write(header)
    for _, key in ipairs(Preferences.ORDER) do
        if written then
            written, write_error = file:write(key .. "=" .. tostring(state.values[key]) .. "\n")
        end
    end
    local closed, close_error = file:close()
    assert(written and closed, write_error or close_error)
end

function Preferences.save(path, state)
    local temporary_path = path .. ".tmp"
    local backup_path = path .. ".bak"
    write_preferences(temporary_path, state)

    local existing = io.open(path, "r")
    if existing then
        existing:close()
        os.remove(backup_path)
        assert(os.rename(path, backup_path))
    end
    local moved, move_error = os.rename(temporary_path, path)
    if not moved then
        if existing then
            os.rename(backup_path, path)
        end
        error(move_error)
    end
end

return Preferences
