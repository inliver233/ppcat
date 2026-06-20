#!/usr/bin/env python3
"""Resolve EventChannel codec: compare byte-exact class descriptors.
EventChannel ctor param type  vs  VideoPlayerApi's real new-codec class.
If identical codepoints -> clone VideoPlayerApi construction (it works)."""
import re, glob, os

PKG='smali_classes2/สۥ۠ۦۡ'
ev_file=os.path.join(PKG,'สۥ۟۟ۡ.smali')
ev=open(ev_file,encoding='utf-8').read()
# EventChannel ctor: <init>(BinaryMessenger, String, CODEC)V  — extract 3rd param
m=re.search(r'\.method public constructor <init>\(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;(L[^;]+;)\)V', ev)
ev_codec = m.group(1) if m else None
print('EventChannel ctor codec param type:', repr(ev_codec))
print('  codepoints:', [hex(ord(c)) for c in ev_codec] if ev_codec else None)

# VideoPlayerApi real EventChannel construction: find the codec it news
vp_files=glob.glob('smali_classes2/สۥ۠۟/*.smali')+glob.glob('smali_classes2/*/*.smali')
# find the file that has the EventChannel ctor call with a new codec
import subprocess
# search all smali for the EventChannel ctor call + preceding new-instance codec
for root,_,files in os.walk('smali_classes2'):
    for fn in files:
        if not fn.endswith('.smali'): continue
        p=os.path.join(root,fn)
        try: src=open(p,encoding='utf-8').read()
        except: continue
        # find: new-instance X, CODEC; invoke-direct X, CODEC-><init>()V ... new-instance Y, EventChannel; ... invoke-direct Y, ..., X, EventChannel-><init>(bm,str,codec)
        for mm in re.finditer(r'new-instance \w\d?, (L[^;]+;)\s+invoke-direct \{\w\d?\}, \1\-><init>\(\)V\s+const-string \w\d?, "([^"]+)"\s+invoke-direct \{\w\d?, \w\d?, \w\d?, \w\d?\}, (Lสۥ۠ۦۡ/สۥ۟۟ۡ;)-><init>\(', src):
            codec_cls=mm.group(1); chan=mm.group(2)
            print(f'\nREAL EventChannel construction in {p}:')
            print(f'  channel={chan!r}')
            print(f'  codec new-instance class={codec_cls!r}')
            print(f'  codepoints: {[hex(ord(c)) for c in codec_cls]}')
            print(f'  MATCHES EventChannel ctor param? {codec_cls==ev_codec}')
            break
    else: continue
    break
