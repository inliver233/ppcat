#!/usr/bin/env python3
"""Generate AdNoOpPluginV3.smali: no-op MethodChannels + EventChannel reward simulation.
ROBUST against combining-mark obfuscation: read authoritative class descriptors directly
from the .smali files' own .class declarations (not hand-assembled strings).

Finds each needed class by its DISTINCTIVE method/field, reads its real 'L...;' descriptor.
Codec blocker RESOLVED: EventChannel codec = StandardMethodCodec concrete class
(byte-exact clone of VideoPlayerApi construction, verified assignable).
"""
import os, re
APK='/root/tools/ppcat_apktool'
SM='smali_classes2'
def rd(p): return open(os.path.join(APK,p),encoding='utf-8').read()

# --- find each needed class by a unique signature, return its full descriptor + key methods ---
def find_class(predicate):
    for root,_,files in os.walk(SM):
        for fn in files:
            if not fn.endswith('.smali'): continue
            p=os.path.join(root,fn)
            try: c=open(p,encoding='utf-8').read()
            except: continue
            cls=re.search(r'\.class[^\n]*?(L[^;]+;)', c)
            if not cls: continue
            desc=cls.group(1)
            if predicate(desc,c): return desc,c
    return None,None

# FlutterPlugin: interface with 2 methods taking L...$binding;V  (the $สۥ۟۠ۢ binding)
fp_iface,_ = find_class(lambda d,c: d.startswith('Lสۦۣ۟ۡ/') and 'abstract' in c[:120] and d.count('/')==1 and '$' not in d and '.method public abstract' in c and c.count('.method public abstract')==2)
assert fp_iface, 'FlutterPlugin not found'
# binding = FlutterPlugin's method param type
def get_abstract_methods(c): return re.findall(r'\.method public abstract (\S+)\(([^)]*)\)V', c)
fp_methods,_=find_class(lambda d,c: d==fp_iface)
# we need the actual file content again
fp_file=None
for root,_,files in os.walk(SM):
    for fn in files:
        p=os.path.join(root,fn)
        try: c=open(p,encoding='utf-8').read()
        except: continue
        m=re.search(r'\.class[^\n]*?(L[^;]+;)',c)
        if m and m.group(1)==fp_iface:
            fp_file=c; break
fpm=re.findall(r'\.method public abstract (\S+)\((L[^;]+;\$[^;]+;)\)V', fp_file)
attach=max(fpm,key=lambda x:len(x[0]))[0]; detach=min(fpm,key=lambda x:len(x[0]))[0]
binding=fpm[0][1]  # Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;
print('FlutterPlugin',fp_iface,'attach len',len(attach),'binding',binding.count('/'))

# binding.getBinaryMessenger(): need the method on binding that returns a BinaryMessenger-like type
# BinaryMessenger = the param type of MethodChannel ctor. Find MethodChannel first.
mchan,mc_file = find_class(lambda d,c: 'constructor <init>(L' in c and 'MethodChannel' not in c and c.count('invoke-virtual')==0 and d.count('/')==1 and d.count('$')==0 and '.method public abstract' not in c and 'setMethodCallHandler' if False else False)
# MethodChannel: has a public method taking a MethodCallHandler; let's find by ctor signature (bmess, String[, codec])
# Better: find the class whose ctor is (X, Ljava/lang/String;)V AND has an abstract MethodCallHandler-taking method absent (it's concrete)
mchan=None
for root,_,files in os.walk(SM):
    for fn in files:
        if '$' in fn or not fn.endswith('.smali'): continue
        p=os.path.join(root,fn);
        try: c=open(p,encoding='utf-8').read()
        except: continue
        m=re.search(r'\.class[^\n]*?(L[^;]+;)',c)
        if not m: continue
        d=m.group(1)
        if '.method public constructor <init>(L' not in c: continue
        # ctor takes (X, String)  -> capture X type
        mc=re.search(r'\.method public constructor <init>\((L[^;]+;)Ljava/lang/String;\)V', c)
        if not mc: continue
        # MethodChannel is the one with a setMethodCallHandler-like: a public method taking an interface (single L...$...; param) - the MCH iface
        # heur: has invoke-virtual and NOT abstract, and a method taking single L...$...;
        if re.search(r'\.method public \S+\(L[^;]+;\$[^;]+;\)V', c):
            mchan=d; mc_file=c; bmess=mc.group(1); break
    if mchan: break
print('MethodChannel',mchan,'bmess',bmess.count('/'))
# setMethodCallHandler = the method taking the MCH interface (single param L...$...;)
setmch=re.search(r'\.method public (\S+)\((L[^;]+;\$[^;]+;)\)V', mc_file).group(1)
mch_iface=re.search(r'\.method public \S+\((L[^;]+;\$[^;]+;)\)V', mc_file).group(1)
# MethodCall.method field + Result.success + onMethodCall from MCH iface file
mch_iface_file=None
for root,_,files in os.walk(SM):
    for fn in files:
        if not fn.endswith('.smali'): continue
        try: c=open(p:=os.path.join(root,fn),encoding='utf-8').read()
        except: continue
        m=re.search(r'\.class[^\n]*?(L[^;]+;)',c)
        if m and m.group(1)==mch_iface: mch_iface_file=c; break
    if mch_iface_file: break
onmethod=re.search(r'\.method public abstract (\S+)\((L[^;]+;)(L[^;]+;\$[^;]+;)\)V', mch_iface_file).group(1)
mcall=re.search(r'\.method public abstract (\S+)\((L[^;]+;)(L[^;]+;\$[^;]+;)\)V', mch_iface_file).group(2)
result=re.search(r'\.method public abstract (\S+)\((L[^;]+;)(L[^;]+;\$[^;]+;)\)V', mch_iface_file).group(3)
# MethodCall.method field name: read from mcall class
mcall_file=None
for root,_,files in os.walk(SM):
    for fn in files:
        try: c=open(p:=os.path.join(root,fn),encoding='utf-8').read()
        except: continue
        m=re.search(r'\.class[^\n]*?(L[^;]+;)',c)
        if m and m.group(1)==mcall: mcall_file=c; break
    if mcall_file: break
field_m=re.search(r'\.field public (\S+):Ljava/lang/String;', mcall_file)
method_field = field_m.group(1) if field_m else 'ۥ้้۟۟ۡ'
# Result.success
result_file=None
for root,_,files in os.walk(SM):
    for fn in files:
        try: c=open(p:=os.path.join(root,fn),encoding='utf-8').read()
        except: continue
        m=re.search(r'\.class[^\n]*?(L[^;]+;)',c)
        if m and m.group(1)==result: result_file=c; break
    if result_file: break
result_success=re.search(r'\.method public abstract (\S+)\(Ljava/lang/Object;\)V', result_file).group(1)

# EventChannel: has setStreamHandler(StreamHandler) public method + ctor (bmess, String, codec)
evchan,ev_file=find_class(lambda d,c: re.search(r'\.method public \S+\(L[^;]+;\$[^;]+;\)V',c) and re.search(r'\.method public constructor <init>\(L[^;]+;Ljava/lang/String;L[^;]+;\)V',c))
assert evchan, 'EventChannel not found'
setsh=re.search(r'\.method public (\S+)\(L[^;]+;\$[^;]+;\)V', ev_file).group(1)
# EventChannel ctor params
ev_ctor=re.search(r'\.method public constructor <init>\((L[^;]+;)Ljava/lang/String;(L[^;]+;)\)V', ev_file)
ev_bmess=ev_ctor.group(1); codec=ev_ctor.group(2)
sh_iface=re.search(r'\.method public (\S+)\((L[^;]+;\$[^;]+;)\)V', ev_file).group(1)  # placeholder
setsh_param=re.search(r'\.method public \S+\((L[^;]+;\$[^;]+;)\)V', ev_file).group(1)  # StreamHandler iface
# StreamHandler iface: has onListen(Object, EventSink)
sh_file=None
for root,_,files in os.walk(SM):
    for fn in files:
        try: c=open(p:=os.path.join(root,fn),encoding='utf-8').read()
        except: continue
        m=re.search(r'\.class[^\n]*?(L[^;]+;)',c)
        if m and m.group(1)==setsh_param: sh_file=c; break
    if sh_file: break
onlisten=re.search(r'\.method public abstract (\S+)\(Ljava/lang/Object;(L[^;]+;\$[^;]+;)\)V', sh_file).group(1)
esink=re.search(r'\.method public abstract (\S+)\(Ljava/lang/Object;(L[^;]+;\$[^;]+;)\)V', sh_file).group(2)
# EventSink.success
es_file=None
for root,_,files in os.walk(SM):
    for fn in files:
        try: c=open(p:=os.path.join(root,fn),encoding='utf-8').read()
        except: continue
        m=re.search(r'\.class[^\n]*?(L[^;]+;)',c)
        if m and m.group(1)==esink: es_file=c; break
    if es_file: break
sink_success=re.search(r'\.method public abstract (\S+)\(Ljava/lang/Object;\)V', es_file).group(1)
# binding.getBinaryMessenger: find method on binding returning ev_bmess
binding_file=None
for root,_,files in os.walk(SM):
    for fn in files:
        try: c=open(p:=os.path.join(root,fn),encoding='utf-8').read()
        except: continue
        m=re.search(r'\.class[^\n]*?(L[^;]+;)',c)
        if m and m.group(1)==binding: binding_file=c; break
    if binding_file: break
getbm=re.search(r'\.method public (\S+)\(\)'+re.escape(ev_bmess), binding_file).group(1)

print('ALL EXTRACTED:')
print(' fp',fp_iface,'attach',len(attach),'detach',len(detach))
print(' binding',binding,'getbm',len(getbm))
print(' mchan',mchan,'setmch',len(setmch),'mch_iface',mch_iface.count('/'))
print(' onmethod',len(onmethod),'mcall',mcall.count('/'),'result',result.count('/'),'result_success',len(result_success))
print(' method_field',repr(method_field))
print(' evchan',evchan,'codec',codec.count('/'),'setsh',len(setsh))
print(' sh_iface',setsh_param.count('/'),'onlisten',len(onlisten),'esink',esink.count('/'),'sink_success',len(sink_success))

import json
json.dump(dict(fp_iface=fp_iface,attach=attach,detach=detach,binding=binding,getbm=getbm,
  mchan=mchan,setmch=setmch,mch_iface=mch_iface,onmethod=onmethod,mcall=mcall,result=result,
  result_success=result_success,method_field=method_field,evchan=evchan,ev_bmess=ev_bmess,codec=codec,
  setsh=setsh,sh_iface=setsh_param,onlisten=onlisten,esink=esink,sink_success=sink_success),
  open('/tmp/v3_syms.json','w'),ensure_ascii=False)
print('symbols saved to /tmp/v3_syms.json')
