#!/usr/bin/env python3
"""
Ad-config SharedPreferences key scanner for ppcat.
Scans the ObjectPool for all ad/VIP/reward-related camelCase strings
that likely serve as SharedPreferences keys.

Independent discovery by test2 - not present in test1/test3 deliverables.

Output: complete list of 20+ SP keys with slot/ref/accessor function mapping.
"""
import json, sys

def load_pool(pool_json='pool_deserialized.json'):
    with open(pool_json) as f:
        return json.load(f)

def load_strings(strings_txt='unflutter_strings.txt'):
    strings = {}
    for line in open(strings_txt):
        if '[ref=' in line:
            try:
                r = int(line.split('[ref=')[1].split(']')[0])
                s = line.split('"')[1].rsplit('"', 1)[0]
                strings[r] = s
            except: pass
    return strings

def load_pool_accesses(pa_txt='pool_accesses.txt'):
    acc = {}
    for line in open(pa_txt):
        parts = line.strip().split()
        if len(parts) >= 2:
            try: acc[int(parts[0], 16)] = int(parts[1], 16)
            except: pass
    return acc

def find_func_start(pc, data):
    for a in range(pc, max(0, pc-0x6000), -4):
        if data[a:a+4] == bytes.fromhex('fd79bfa9') and data[a+4:a+8] == bytes.fromhex('fd030faa'):
            return a
    return pc

def main():
    pool = load_pool()
    strings = load_strings()
    acc = load_pool_accesses()

    with open('libapp.so', 'rb') as f:
        d = f.read()

    # Build off->ref mapping
    off2ref = {}
    for e in pool['entries']:
        if e['type'] == 0:
            off2ref[e['idx'] * 8] = e['val']

    # Categories of ad-config SP keys
    categories = {
        'ad_display': ['showSplashAd', 'isNoAdLock', 'noAdAllowSourceList', 'noAdDisableSourceList',
                       'noAdSourceNumLimit', 'noAdRegex'],
        'ad_stats': ['adNum', 'adNum:', 'totalNum', 'totalTime', 'today', 'leaveTime:', 'readCount'],
        'reward': ['rewardTime', 'getRewardTime', 'checkDaily', 'isDaily:', 'rewardName', 'rewardAmount',
                   'rewardType', 'rewardVerify', 'hasReward'],
        'other': ['preloadNum', 'ComicPreloadNum', 'downThreadNum', 'expiresDate', 'expires',
                  'remoteConfigSign', 'forceVersion', 'showSplashAd'],
    }

    all_kw = set()
    for v in categories.values():
        all_kw.update(v)

    # Find matching pool strings
    results = {}
    for ref, s in strings.items():
        if s in all_kw or (len(s) >= 3 and len(s) <= 30 and
                           any(c.isupper() for c in s) and s[0].islower()):
            for e in pool['entries']:
                if e['type'] == 0 and e['val'] == ref:
                    off = e['idx'] * 8
                    pcs = [pc for pc, o in acc.items() if o == off]
                    funcs = sorted(set(find_func_start(pc, d) for pc in pcs))
                    if pcs:
                        results[s] = {'ref': ref, 'slot': e['idx'], 'off': off,
                                      'funcs': funcs, 'pcs': pcs[:5]}
                    break

    # Print report
    print(f"# Ad-config SP key scan results ({len(results)} keys)")
    print(f"# {'='*60}")

    for cat, keywords in categories.items():
        print(f"\n## {cat}")
        for kw in keywords:
            if kw in results:
                r = results[kw]
                print(f"  {kw:30s} ref={r['ref']:6d} slot=0x{r['slot']:04x} off=0x{r['off']:05x}")
                print(f"    funcs: {[hex(f) for f in r['funcs'][:4]]}")

    # Bonus: show all camelCase strings with accessors (potential SP keys)
    print(f"\n## All camelCase strings with .text accessors")
    for s, r in sorted(results.items()):
        if any(c.isupper() for c in s) and s[0].islower():
            print(f"  {s:35s} ref={r['ref']:6d} funcs={[hex(f) for f in r['funcs'][:3]]}")

if __name__ == '__main__':
    main()
