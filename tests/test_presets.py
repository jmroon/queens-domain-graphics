from pathlib import Path
import sys,tempfile,json

from lupa.lua54 import LuaRuntime
scripts=(Path(__file__).resolve().parents[1]/'src/QDGraphics/Scripts').resolve()
source=(scripts/'main.lua').read_text()
mock=r'''
commands={};hooks={};messages={};writes=0;consolewrites=0;queues=0;objects={}
available=true;failResolution=false
values={EnableDither=1,QD_SmoothColours=0,QD_Vignette=1,Damage=0.33,InCutscene=1}
cvars={['r.DefaultFeature.AntiAliasing']=0,['r.PostProcessAAQuality']=4,['r.TemporalAA.Algorithm']=0,['r.MaxAnisotropy']=8,['sg.TextureQuality']=3}
function print(s)table.insert(messages,s)end
function FName(n)return {ToString=function()return n end}end
function FText(n)return n end
local yes=function()return true end
pc={IsValid=function()return available end}
save={IsValid=yes,LockedResScale=true,ResScale=80,FOV=97,Vsync=true,Brightness=0.9,FramerateCap=2}
stock={IsValid=yes,LockedResScale=true,ResScale=80}
gi={IsValid=yes,ActiveSystemSave=save,GI_QueueSystemSave=function()queues=queues+1 end}
gi['UpdateScreen%']=function(self,force)
 assert(self==gi and force);if failResolution then error('resolution failed')end
 cvars['r.ScreenPercentage']=save.LockedResScale and 37.5 or save.ResScale
end
collection={IsValid=yes,ScalarParameters={ForEach=function(self,fn)
 for _,n in ipairs({'EnableDither','QD_SmoothColours','QD_Vignette','Damage','InCutscene'})do
 fn(1,{get=function()return {ParameterName=FName(n)}end})end
end}}
material={IsValid=yes,SetScalarParameterValue=function(self,p,c,n,v)
 assert(p==pc);assert(n:ToString()~='Damage' and n:ToString()~='InCutscene');values[n:ToString()]=v;writes=writes+1
end,GetScalarParameterValue=function(self,p,c,n)return values[n:ToString()]end}
system={IsValid=yes,GetConsoleVariableIntValue=function(self,n)return cvars[n] or 0 end,
ExecuteConsoleCommand=function(self,p,cmd,specific)
 assert(p==pc and specific==pc);local k,v=cmd:match('([^ ]+) (.*)');cvars[k]=tonumber(v);consolewrites=consolewrites+1
end}
gameplay={IsValid=yes,GetGameInstance=function(self,p)assert(p==pc);return gi end}
function FindFirstOf(n)assert(n=='PlayerController');return pc end
function StaticFindObject(n)
 if n:match('^/Runtime')then return objects[n]end
 if n:match(':')then return {IsValid=yes}end
 if n:match('PixelFilter_MPC')then return collection end
 if n:match('KismetMaterialLibrary')then return material end
 if n:match('KismetSystemLibrary')then return system end
 if n:match('GameplayStatics')then return gameplay end
 if n:match('Default__FS_SystemSave_C')then return stock end
 error('unexpected object '..n)
end
function LoadAsset()error('unexpected asset load')end
function RegisterConsoleCommandHandler(n,f)commands[n]=f end
function RegisterHook(n,pre,post)hooks[n]=post or pre end
function RegisterInitGameStatePostHook(fn)hooks.world=fn end
ar={Log=function(self,s)table.insert(messages,s)end}
function run(n,...)commands[n](n,{...},ar)end
function ready()hooks['/Script/Engine.PlayerController:ClientRestart']({get=function()return pc end})end
function native_changed()hooks['/Game/Blueprints/FS_GameInstance.FS_GameInstance_C:ApplyOptions']()end
function widget(key,id,kind)
 local o={CurrentValue=0,SkipSavingOption=true,IsValid=yes,GetAddress=function()return id end}
 o.GetFName=function()return FName('QDGraphicsControl_'..key)end
 o.GetFullName=function()return 'Widget /Runtime.'..id..'.'..key end
 o.Refreshtext=function(self)self.text=tostring(self.CurrentValue)end
 o.OptionText={IsValid=yes,SetText=function(self,v)o.text=v end}
 if kind then
  o.Property=FName(kind=='retro' and 'LockedResScale' or 'ResScale')
  o.PlayRelevantToggleAnim=function(self)self.visual=self.CurrentValue end
  o.Slider_99={SetValue=function(self,v)o.visual=v end}
  o.UpdateReadout=function()end;o.SetIsEnabled=function(self,v)self.enabled=v end
 end
 objects[o:GetFullName():match('^%S+ (.+)$')]=o
 local class=kind=='retro' and 'OptionsMenu_ToggleControl' or (kind=='scale' and 'OptionsMenu_SliderControl' or 'OptionsMenu_OptionSelect')
 hooks['/Game/UI/Menus/OptionsMenu/'..class..'.'..class..'_C:Init']({get=function()return o end})
 return o
end
function choose(o,index)
 o.CurrentValue=index
 hooks['/Game/UI/Menus/OptionsMenu/OptionsMenu_OptionSelect.OptionsMenu_OptionSelect_C:SaveProperty']({get=function()return o end})
end
'''
with tempfile.TemporaryDirectory() as td:
    settings=(Path(td)/'QDGraphics.ini').resolve()
    code=source.replace(source.splitlines()[1],'local SCRIPT_DIR = '+json.dumps(str(scripts).replace('\\','/')+'/'))
    code=code.replace(source.splitlines()[2],'local SETTINGS_PATH = '+json.dumps(str(settings).replace('\\','/')))
    def boot(before=''):
        l=LuaRuntime();l.execute(mock);l.execute(before);l.execute(code);return l
    l=boot();l.execute('ready();assert(writes==0 and consolewrites==0 and queues==0)')
    assert not settings.exists()
    l.execute("preset=widget('preset',1);retro=widget('retro',2,'retro');scale=widget('scale',3,'scale');assert(preset.CurrentValue==0)")
    l.execute("choose(preset,1);assert(save.LockedResScale==false and save.ResScale==100 and queues==1);assert(values.EnableDither==0 and values.QD_SmoothColours==2);assert(cvars['r.DefaultFeature.AntiAliasing']==2 and cvars['r.MaxAnisotropy']==16);assert(retro.visual==false and scale.visual==100 and scale.enabled)")
    assert 'preset=modern' in settings.read_text()
    l=boot('save.LockedResScale=false;save.ResScale=100');l.execute('ready();assert(values.QD_SmoothColours==2 and queues==0)')
    l.execute("preset=widget('preset',1);assert(preset.CurrentValue==1);run('qd_vignette','70');assert(preset.CurrentValue==2)")
    l.execute("run('qd_preset','modern');save.LockedResScale=true;native_changed();assert(preset.CurrentValue==2 and save.LockedResScale==true and values.EnableDither==0)")
    assert 'preset=custom' in settings.read_text()
    l.execute("run('qd_preset','modern');save.ResScale=75;native_changed();assert(save.ResScale==75 and preset.CurrentValue==2)")
    l.execute("run('qd_preset','original');assert(values.EnableDither==1 and values.QD_SmoothColours==0 and values.QD_Vignette==1);assert(cvars['r.DefaultFeature.AntiAliasing']==0 and cvars['r.MaxAnisotropy']==8);assert(save.LockedResScale and save.ResScale==80)")
    l.execute("local w=writes;local q=queues;run('qd_preset','custom');assert(writes==w and queues==q and preset.CurrentValue==2)")
    # Invalid values and failed native operations must not corrupt persisted state.
    saved=settings.read_bytes()
    l.execute("run('qd_preset','invalid');run('qd_gradients','invalid');run('qd_vignette','101');run('qd_af','17')")
    assert settings.read_bytes()==saved
    l.execute("failResolution=true;run('qd_preset','modern');assert(save.LockedResScale and save.ResScale==80);failResolution=false")
    assert settings.read_bytes()==saved
    l.execute("assert(save.FOV==97 and save.Vsync and save.Brightness==0.9 and save.FramerateCap==2);assert(values.Damage==0.33 and values.InCutscene==1)")
    # Renamed preset: existing Enhanced files and commands remain compatible.
    settings.write_text('version=2\nmanaged=1\npreset=enhanced\naa=taa\naf=16\ndither=0\ngradients=biased\nvignette=100\n')
    l=boot('save.LockedResScale=false;save.ResScale=100')
    l.execute("ready();preset=widget('preset',1);assert(preset.CurrentValue==1 and values.QD_SmoothColours==2 and queues==0);run('qd_preset','enhanced')")
    assert 'preset=modern' in settings.read_text()
    # Version 1 preferences migrate with their values intact and no native save write.
    settings.write_text('version=1\naa=off\naf=16\ndither=0\ngradients=biased\nvignette=35\n')
    l=boot('save.LockedResScale=false;save.ResScale=92');l.execute("ready();assert(values.QD_SmoothColours==2 and values.QD_Vignette==0.35 and queues==0);assert(cvars['r.PostProcessAAQuality']==0 and save.ResScale==92);run('qd_gradients','smooth')")
    assert 'version=2' in settings.read_text() and 'preset=custom' in settings.read_text()
    # A new user with non-stock settings must see no first-run rendering changes.
    settings.unlink()
    l=boot("save.LockedResScale=false;save.ResScale=85;cvars['r.DefaultFeature.AntiAliasing']=1;cvars['r.PostProcessAAQuality']=6;cvars['r.MaxAnisotropy']=2")
    l.execute("ready();assert(writes==0 and consolewrites==0 and queues==0);preset=widget('preset',1);assert(preset.CurrentValue==2);run('qd_dither','0');assert(cvars['r.PostProcessAAQuality']==6 and cvars['r.MaxAnisotropy']==2 and save.ResScale==85)")
print('PASS: opt-in first launch, native menu presets, modern/original values, native UI refresh, manual Custom detection, restart persistence, failed-change rollback, legacy migration, unrelated game settings preserved.')
