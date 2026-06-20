#!/usr/bin/env python3
"""Insert AdNoOpPlugin registration into GeneratedPluginRegistrant (C10522 smali)."""
import re, os
APK='/root/tools/ppcat_apktool'
def rd(p): return open(os.path.join(APK,p),encoding='utf-8').read()

reg = rd('smali_classes2/สۥ۠ۦۢ/สۥ۟۟ۡ.smali')
# exact tokens
getreg = re.search(r'invoke-virtual \{p0\}, Lio/flutter/embedding/engine/สۥ۟۟ۡ;->(\S+)\(\)Lสۦۣ۟ۡ/สۥ۟۠ۢ;', reg).group(1)
add    = re.search(r'Lสۦۣ۟ۡ/สۥ۟۠ۢ;->(\S+)\(Lสۦۣ۟ۡ/สۥ۟۟ۡ;\)V', reg).group(1)
print('getRegistry=',repr(getreg))
print('add        =',repr(add))

block = f'''
    :try_start_ad
    invoke-virtual {{p0}}, Lio/flutter/embedding/engine/สۥ۟۟ۡ;->{getreg}()Lสۦۣ۟ۡ/สۥ۟۠ۢ;

    move-result-object v0

    new-instance v1, Lcom/gentle/ppcat/AdNoOpPlugin;

    invoke-direct {{v1}}, Lcom/gentle/ppcat/AdNoOpPlugin;-><init>()V

    invoke-interface {{v0, v1}}, Lสۦۣ۟ۡ/สۥ۟۠ۢ;->{add}(Lสۦۣ۟ۡ/สۥ۟۟ۡ;)V
    :try_end_ad
    .catch Ljava/lang/Exception; {{:try_start_ad .. :try_end_ad}} :catch_ad

    :catch_ad
'''

# insert right before the first :try_start_0
assert '    :try_start_0\n' in reg
new = reg.replace('    :try_start_0\n', block + '    :try_start_0\n', 1)
open(os.path.join(APK,'smali_classes2/สۥ۠ۦۢ/สۥ۟۟ۡ.smali'),'w',encoding='utf-8').write(new)
print('inserted registration block')
