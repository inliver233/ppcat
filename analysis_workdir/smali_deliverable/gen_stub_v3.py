#!/usr/bin/env python3
"""Extract byte-exact EventChannel/StreamHandler/EventSink/Codec symbols from smali,
so the V3 reward stub can be generated without combining-mark transcription errors."""
import re, os
APK='/root/tools/ppcat_apktool'
def rd(p): return open(os.path.join(APK,p),encoding='utf-8').read()

# EventChannel class = Lสۥ笔墨ۦۡ/สۥ۟۟ۡ;  (confirmed: has setStreamHandler(StreamHandler))
ev = rd('smali_classes2/สۥ۠ۦۡ/สۥ۟۟ۡ.smali')
# ctor: (BinaryMessenger, String, Codec)
ctor = re.search(r'\.method public constructor <init>\(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;(L[^;]+;)\)V', ev)
codec_param = ctor.group(1) if ctor else None
# setStreamHandler(StreamHandler): the public method taking the StreamHandler inner class
setsh = re.search(r'\.method public (\S+)\((Lสۥ۠ۦۡ/สۥ۟۟ۡ\$[^;]+;)\)V', ev)
setsh_name = setsh.group(1) if setsh else None
streamhandler_iface = setsh.group(2) if setsh else None
print('EventChannel class       : Lสۥ۠ۦۡ/สۥ۟۟ۡ;')
print('EventChannel ctor codec  :', codec_param)
print('setStreamHandler(name)   :', repr(setsh_name))
print('StreamHandler iface      :', streamhandler_iface)

# StreamHandler interface methods (onListen/onCancel)
sh = rd('smali_classes2/สۥ۠ۦۡ/สۥ۟۟ۡ$สۥۣ۟۟.smali')
sh_methods = re.findall(r'\.method public abstract (\S+)\(([^)]*)\)V', sh)
print('StreamHandler methods    :', sh_methods)
# EventSink interface methods (success/error/endOfStream)
es = rd('smali_classes2/สۥ۠ۦۡ/สۥ۟۟ۡ$สۥ۟۟ۤ.smali')
es_methods = re.findall(r'\.method public abstract (\S+)\(([^)]*)\)V', es)
print('EventSink methods        :', es_methods)

# codec class: from the real construction, codec = new Lสۥ笔墨ۦۡ/สۥ۟۟;(). Verify codec_param matches a constructible class.
# find the codec class file (strip L ; )
codec_cls = codec_param
codec_fname = codec_cls[1:-1].replace('/', os.sep)+'.smali'
codec_path = os.path.join('smali_classes2', codec_cls[1:-1].split('/',1)[1].replace('/','/')+'.smali')
# try to locate
import glob
cands = glob.glob(os.path.join(APK,'smali_classes2','สۥ۠ۦۡ','*.smali'))
codec_found=None
for c in cands:
    name=os.path.basename(c)[:-6]
    if ('Lสۥ۠ۦۡ/'+name+';')==codec_param:
        codec_found=c; break
print('codec class file found   :', codec_found)
if codec_found:
    has_init = '.method public constructor <init>()V' in open(codec_found,encoding='utf-8').read()
    print('codec has no-arg <init>  :', has_init)
