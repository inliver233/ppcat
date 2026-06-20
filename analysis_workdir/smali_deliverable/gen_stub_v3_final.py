#!/usr/bin/env python3
"""Generate AdNoOpPluginV3.smali (EventChannel reward stub). All symbols extracted robustly
from V1 (verified-compiling) + EventChannel interface files. Codec blocker RESOLVED."""
import os, re
APK='/root/tools/ppcat_apktool'
PKG=chr(0xe2a)+chr(0x6e5)+chr(0x6e0)+chr(0x6e6)+chr(0x6e1)
BASE=os.path.join(APK,'smali_classes2',PKG)
def f(bn): return open(os.path.join(BASE,bn),encoding='utf-8').read()
def clsdesc(c): return re.search(r'\.class[^\n]*?(L[^;]+;)',c).group(1)
v1=open(os.path.join(APK,'smali_classes2/com/gentle/ppcat/AdNoOpPlugin.smali'),encoding='utf-8').read()

impls=re.findall(r'\.implements (L[^;]+;)', v1)
fp_iface,mch_iface = impls[0],impls[1]
am=re.findall(r'\.method public (\S+)\((L[^)]+)\)V', v1)
onep=[(n,p) for n,p in am if '$' in p and p.count('L')==1]   # attach/detach
attach,detach=max(onep,key=lambda x:len(x[0]))[0], min(onep,key=lambda x:len(x[0]))[0]
binding=onep[0][1]
twop=[(n,p) for n,p in am if p.count('L')==2]                 # onMethodCall
onmethod=twop[0][0]; a,b=twop[0][1].split(';L',1); mcall=a+';'; result='L'+b
_gbm=re.search(r'invoke-virtual \{p1\}, (L[^)]+?;)->(\S+)\(\)(L[^;]+;)', v1)
binding=_gbm.group(1); getbm=_gbm.group(2); bmess=_gbm.group(3)
mchan=re.search(r'new-instance v1, (L[^;]+;)', v1).group(1)
setmch=re.search(r'invoke-virtual \{v1, p0\}, (L[^)]+?;)->(\S+)\((L[^)]+?;)\)V', v1).group(2)
result_success=re.search(r'invoke-interface \{p2, v0\}, (L[^)]+?;)->(\S+)\(Ljava/lang/Object;\)V', v1).group(2)

ev=f('สۥ۟۟ۡ.smali'); evchan=clsdesc(ev)
ev_ctor=re.search(r'\.method public constructor <init>\((L[^)]+?;)Ljava/lang/String;(L[^)]+?;)\)V', ev)
codec_base=ev_ctor.group(2); bmess2=ev_ctor.group(1)  # codec_base = ctor codec param type
# setStreamHandler = the public method whose param is the StreamHandler iface ($สۥۣ۟۟;)
setsh_m=re.search(r'\.method public (\S+)\((L[^)]+?\$สۥۣ۟۟;)\)V', ev)
setsh=setsh_m.group(1); sh_iface=setsh_m.group(2)
codec=clsdesc(f('สۥ۟۟.smali'))
sh=f('สۥ۟۟ۡ$สۥۣ۟۟.smali')
onlisten=re.search(r'\.method public abstract (\S+)\(Ljava/lang/Object;(L[^)]+?;)\)V', sh).group(1)
esink=re.search(r'\.method public abstract \S+\(Ljava/lang/Object;(L[^)]+?;)\)V', sh).group(1)
sink_success=re.search(r'\.method public abstract (\S+)\(Ljava/lang/Object;\)V', f('สۥ۟۟ۡ$สۥ۟۟ۤ.smali')).group(1)
assert '.method public constructor <init>()V' in f('สۥ۟۟.smali'), 'codec no <init>()V'

print('fp',fp_iface,'\nbinding',binding,'getbm',repr(getbm),'bmess',bmess)
print('mchan',mchan,'setmch',repr(setmch),'mch_iface',mch_iface)
print('onmethod',repr(onmethod),'mcall',mcall,'result',result,'result_success',repr(result_success))
print('evchan',evchan,'codec',codec,'codec_base',codec_base,'setsh',repr(setsh),'sh_iface',sh_iface)
print('onlisten',repr(onlisten),'esink',esink,'sink_success',repr(sink_success))

CH=['flutter_pangle_ads','ksad','plugins.flutter.io/google_mobile_ads','plugins.hetian.me/gdt_plugins']
L=[f'''.class public Lcom/gentle/ppcat/AdNoOpPluginV3;
.super Ljava/lang/Object;
.source "AdNoOpPluginV3.java"
.implements {fp_iface}
.implements {mch_iface}
.implements {sh_iface}
.implements Ljava/lang/Runnable;

# V3: 4 no-op MethodChannels + EventChannel "flutter_pangle_ads_event" reward simulation.
# StreamHandler.onListen stores EventSink; "Reward" method -> Thread sleep 30s ->
# push onRewardArrived/onAdClose maps via EventSink.success (correct EventChannel path).
.field private eventSink:{esink}

.method public constructor <init>()V
    .locals 0
    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public {attach}({binding})V
    .locals 4
    invoke-virtual {{p1}}, {binding}->{getbm}(){bmess}
    move-result-object v0
''']
for ch in CH:
    L.append(f'''    new-instance v1, {mchan}
    const-string v2, "{ch}"
    invoke-direct {{v1, v0, v2}}, {mchan}-><init>({bmess}Ljava/lang/String;)V
    invoke-virtual {{v1, p0}}, {mchan}->{setmch}({mch_iface})V
''')
L.append(f'''    new-instance v1, {codec}
    invoke-direct {{v1}}, {codec}-><init>()V
    new-instance v3, {evchan}
    const-string v2, "flutter_pangle_ads_event"
    invoke-direct {{v3, v0, v2, v1}}, {evchan}-><init>({bmess}Ljava/lang/String;{codec_base})V
    invoke-virtual {{v3, p0}}, {evchan}->{setsh}({sh_iface})V
    return-void
.end method

.method public {detach}({binding})V
    .locals 0
    return-void
.end method

.method public {onlisten}(Ljava/lang/Object;{esink})V
    .locals 0
    iput-object p2, p0, Lcom/gentle/ppcat/AdNoOpPluginV3;->eventSink:{esink}
    return-void
.end method

.method public {onmethod}({mcall}{result})V
    .locals 3
    iget-object v0, p1, {mcall}->ۥ้้۟۟ۡ:Ljava/lang/String;
    const/4 v1, 0x0
    invoke-interface {{p2, v1}}, {result}->{result_success}(Ljava/lang/Object;)V
    const-string v2, "Reward"
    invoke-virtual {{v0, v2}}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v2
    if-eqz v2, :cond_nr
    new-instance v2, Ljava/lang/Thread;
    invoke-direct {{v2, p0}}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V
    invoke-virtual {{v2}}, Ljava/lang/Thread;->start()V
    :cond_nr
    return-void
.end method

.method public run()V
    .locals 5
    :try_start_0
    const-wide/32 v0, 0x7530
    invoke-static {{v0, v1}}, Ljava/lang/Thread;->sleep(J)V
    :try_end_0
    .catch Ljava/lang/InterruptedException; {{:try_start_0 .. :try_end_0}} :catch_0
    goto :push0
    :catch_0
    :push0
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV3;->eventSink:{esink}
    if-eqz v2, :done
    new-instance v3, Ljava/util/HashMap;
    invoke-direct {{v3}}, Ljava/util/HashMap;-><init>()V
    const-string v4, "action"
    const-string v0, "onRewardArrived"
    invoke-virtual {{v3, v4, v0}}, Ljava/util/HashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
    invoke-interface {{v2, v3}}, {esink}->{sink_success}(Ljava/lang/Object;)V
    const-wide/16 v0, 0x1f4
    invoke-static {{v0, v1}}, Ljava/lang/Thread;->sleep(J)V
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV3;->eventSink:{esink}
    new-instance v3, Ljava/util/HashMap;
    invoke-direct {{v3}}, Ljava/util/HashMap;-><init>()V
    const-string v4, "action"
    const-string v0, "onAdClose"
    invoke-virtual {{v3, v4, v0}}, Ljava/util/HashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
    invoke-interface {{v2, v3}}, {esink}->{sink_success}(Ljava/lang/Object;)V
    :done
    return-void
    .catch Ljava/lang/InterruptedException; {{:push0 .. :done}} :catch_1
    :catch_1
    return-void
.end method
''')
out=os.path.join(APK,'smali_classes2/com/gentle/ppcat/AdNoOpPluginV3.smali')
open(out,'w',encoding='utf-8').write(''.join(L))
print('\nwrote',out)
