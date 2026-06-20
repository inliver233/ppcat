#!/usr/bin/env python3
"""Generate AdNoOpPluginV2.smali: no-op + reward-event simulation.
On showRewardVideoAd (or any *Reward* method): result.success(null), then on a
background thread sleep ~30s (bypass anti-cheat time threshold), then send
onRewardArrived + onAdClose events to the Pangle channel via invokeMethod.
All other methods: result.success(null).

EXPERIMENTAL upgrade over V1 (which only no-ops). V1 remains the safe baseline.
Symbols byte-exact from sqflite + interface smali (gen_stub.py verified)."""
import re, os
APK='/root/tools/ppcat_apktool'
def rd(p): return open(os.path.join(APK,p),encoding='utf-8').read()
flutter_plugin_iface='Lสۦۣ۟ۡ/สۥ۟۟ۡ;'
mch_iface          ='Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;'
binding_cls        ='Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;'
mchannel_cls       ='Lสۥ۠ۦۡ/สۥ۟۟۠;'
bmessenger_cls     ='Lสۥ۠ۦۡ/สۥ۟۠ۢ;'
mcall_cls          ='Lสۥ۠ۦۡ/สۥ۟۠۠;'
result_iface       ='Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;'
fp_src=rd('smali_classes2/สۦۣ۟ۡ/สۥ۟۟ۡ.smali')
fp_methods=re.findall(r'\.method public abstract (\S+)\(Lสۦۣ۟ۡ/สۥ۟۟ۡ\$สۥ۟۠ۢ;\)V',fp_src)
attach_name=max(fp_methods,key=len); detach_name=min(fp_methods,key=len)
mch_src=rd('smali_classes2/สۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ.smali')
onmethod_name=re.search(r'\.method public abstract (\S+)\(Lสۥ۠ۦۡ/สۥ۟۠۠;Lสۥ۠ۦۡ/สۥ۟۟۠\$สۥۣ۟۟;\)V',mch_src).group(1)
sq=rd('smali_classes2/สۥ۟ۥۥ/สۥ۟۟ۢ.smali')
getbm=re.search(r'invoke-virtual \{p1\}, Lสۦۣ۟ۡ/สۥ۟۟ۡ\$สۥ۟۠ۢ;->(\S+)\(\)Lสۥ۠ۦۡ/สۥ۟۠ۢ;',sq).group(1)
setmch=re.search(r'Lสۥ۠ۦۡ/สۥ۟۟۠;->(\S+)\(Lสۥ۠ۦۡ/สۥ۟۟۠\$สۥ۟۟ۢ;\)V',sq).group(1)
res_src=rd('smali_classes2/สۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟.smali')
success_name=re.search(r'\.method public abstract (\S+)\(Ljava/lang/Object;\)V',res_src).group(1)
# V2 new symbols
invoke_method_no_cb='ۥ้้้้้้۟۟ۡ'   # invokeMethod(String,Object)V  (verified above)
call_method_field='ۥ้้۟۟ۡ'         # MethodCall.method:String (verified)

CHANNELS=['flutter_pangle_ads','ksad','plugins.flutter.io/google_mobile_ads','plugins.hetian.me/gdt_plugins']
# build onAttachedToEngine: store pangle channel field + register all handlers
attach=[]
attach.append('    .locals 3')
attach.append(f'    invoke-virtual {{p1}}, {binding_cls}->{getbm}(){bmessenger_cls}')
attach.append('    move-result-object v0')
for i,ch in enumerate(CHANNELS):
    attach.append(f'    new-instance v1, {mchannel_cls}')
    attach.append(f'    const-string v2, "{ch}"')
    attach.append(f'    invoke-direct {{v1, v0, v2}}, {mchannel_cls}-><init>({bmessenger_cls}Ljava/lang/String;)V')
    if ch=='flutter_pangle_ads':
        attach.append(f'    iput-object v1, p0, Lcom/gentle/ppcat/AdNoOpPluginV2;->pangleChannel:{mchannel_cls}')
    attach.append(f'    invoke-virtual {{v1, p0}}, {mchannel_cls}->{setmch}({mch_iface})V')
attach.append('    return-void')

smali=f'''.class public Lcom/gentle/ppcat/AdNoOpPluginV2;
.super Ljava/lang/Object;
.source "AdNoOpPluginV2.java"
.implements {flutter_plugin_iface}
.implements Ljava/lang/Runnable;
.implements {mch_iface}

# V2: no-op + reward simulation (delayed onRewardArrived/onAdClose on Pangle).
# Field: the Pangle MethodChannel, used to push events Java->Dart.
.field private pangleChannel:{mchannel_cls}

.method public constructor <init>()V
    .locals 0
    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V
    return-void
.end method

# onAttachedToEngine
.method public {attach_name}({binding_cls})V
{chr(10).join(attach)}
.end method

# onDetachedFromEngine
.method public {detach_name}({binding_cls})V
    .locals 0
    return-void
.end method

# onMethodCall(call, result)
.method public {onmethod_name}({mcall_cls}{result_iface})V
    .locals 3
    # read method name = call.method
    iget-object v0, p1, {mcall_cls}->{call_method_field}:Ljava/lang/String;
    # success immediately for ALL methods (baseline no-op)
    const/4 v1, 0x0
    invoke-interface {{p2, v1}}, {result_iface}->{success_name}(Ljava/lang/Object;)V
    # if method contains "Reward" -> arm reward simulation
    const-string v2, "Reward"
    invoke-virtual {{v0, v2}}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v2
    if-eqz v2, :cond_no_reward
    # ensure pangleChannel != null
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV2;->pangleChannel:{mchannel_cls}
    if-eqz v2, :cond_no_reward
    # spawn a Thread(this) to sleep then send events (bypass anti-cheat time threshold)
    new-instance v2, Ljava/lang/Thread;
    invoke-direct {{v2, p0}}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V
    invoke-virtual {{v2}}, Ljava/lang/Thread;->start()V
    :cond_no_reward
    return-void
.end method

# Runnable.run: sleep ~30s then push onRewardArrived + onAdClose to Pangle channel.
.method public run()V
    .locals 5
    :try_start_0
    const-wide/32 v0, 0x7530          # 30000 ms = 30s (simulate reward ad watch)
    invoke-static {{v0, v1}}, Ljava/lang/Thread;->sleep(J)V
    :try_end_0
    .catch Ljava/lang/InterruptedException; {{:try_start_0 .. :try_end_0}} :catch_0
    goto :send
    :catch_0
    # send reward-arrived event (arg = null; Dart side onRewardArrived)
    :send
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV2;->pangleChannel:{mchannel_cls}
    if-eqz v2, :done
    const-string v3, "onRewardArrived"
    const/4 v4, 0x0
    invoke-virtual {{v2, v3, v4}}, {mchannel_cls}->{invoke_method_no_cb}(Ljava/lang/String;Ljava/lang/Object;)V
    const-wide/16 v0, 0x1f4           # 500 ms
    invoke-static {{v0, v1}}, Ljava/lang/Thread;->sleep(J)V
    const-string v3, "onAdClose"
    invoke-virtual {{v2, v3, v4}}, {mchannel_cls}->{invoke_method_no_cb}(Ljava/lang/String;Ljava/lang/Object;)V
    :done
    return-void
    .catch Ljava/lang/InterruptedException; {{:send .. :done}} :catch_1
    :catch_1
    return-void
.end method
'''
out='/root/tools/ppcat_apktool/smali_classes2/com/gentle/ppcat/AdNoOpPluginV2.smali'
open(out,'w',encoding='utf-8').write(smali)
print('wrote',out)
print('symbols: attach=%d detach=%d onMethod=%d invoke=%s'%(len(attach_name),len(detach_name),len(onmethod_name),invoke_method_no_cb))
