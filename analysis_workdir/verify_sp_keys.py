#!/usr/bin/env python3
"""DEFINITIVE read-vs-write classification of test2's ad SP keys.
A key is READ iff some accessor calls an SP-bridge (0x904xxx/0x905xxx setter+getter / 0x4ea988 getAll).
Cross-validates + corrects test2's table."""
import json
db={int(k):v for k,v in json.load(open('analysis_workdir/xref_db.json')).items()}
pool=json.load(open('analysis_workdir/pool_deserialized.json'))
ref2off={int(k):v[1] for k,v in pool['by_ref'].items()}
strings={}
for line in open('unflutter_strings.txt'):
    if '[ref=' in line:
        try:
            r=int(line.split('[ref=')[1].split(']')[0]); q=line.split('"',1)[1].rsplit('"',1)[0]; strings[r]=q
        except: pass

def is_sp_bridge(c): return (0x904000<=c<0x906000) or (0x4ea000<=c<0x4eb000)

SP_KEYS=[(19035,'isNoAdLock'),(2855,'showSplashAd'),(18367,'noAdDisableSourceList'),
(5996,'noAdAllowSourceList'),(11283,'noAdSourceNumLimit'),(6278,'noAdRegex'),
(7606,'rewardTime'),(8067,'getRewardTime'),(11244,'readCount'),(10238,'preloadNum'),
(25454,'ComicPreloadNum'),(30590,'downThreadNum'),(11191,'checkDaily'),(7406,'expiresDate'),
(11366,'可以捐赠')]

print(f"{'SP key':<22} {'ref':>6} {'accessors calling SP-bridge':<45} verdict")
print('-'*100)
for ref,name in SP_KEYS:
    accs=[]
    for f,v in db.items():
        if name in v['strings']:
            sp_calles=[hex(c) for c in v['callees'] if is_sp_bridge(c)]
            if sp_calles:
                accs.append((f,sp_calles))
    if accs:
        det=' ; '.join(f'0x{f:x}->{c}' for f,c in accs[:3])
        verdict='READ (SP-set likely works)'
    else:
        # no accessor calls SP-bridge
        allaccs=[f for f,v in db.items() if name in v['strings']]
        det=f'{len(allaccs)} accessor(s), none call SP-bridge'
        verdict='WRITE-ONLY (SP-set ineffective)' if len(allaccs)<=2 else 'indirect (verify)'
    print(f"{name:<22} {ref:>6} {det:<45} {verdict}")
