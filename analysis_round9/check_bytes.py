#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Verify key patch bytes in the device-installed APK's libapp.so.
import zipfile, sys
apk = sys.argv[1] if len(sys.argv) > 1 else r"E:/皮皮喵4/work/devchk.apk"
d = zipfile.ZipFile(apk).read("lib/arm64-v8a/libapp.so")
checks = [
    (0x8e1dd0, "e00316aac0035fd6", "tamper1 return-null"),
    (0x8ef2b8, "e00316aac0035fd6", "tamper2 return-null"),
    (0xbc1020, "00020054", "fault gate"),
    (0x920d90, "29000014", "fault body cured (MUST stay)"),
    (0xbd2e30, "e00316aa", "overlay 0xbd2e1c entry-null (NEW)"),
    (0xbd2e34, "ef031daa", "overlay mov x15,x29"),
    (0xbd2e38, "fd79c1a8", "overlay ldp"),
    (0xbd2e3c, "c0035fd6", "overlay ret"),
]
ok = True
for a, exp, name in checks:
    got = d[a:a+len(bytes.fromhex(exp))].hex()
    mark = "OK" if got == exp else "** MISMATCH **"
    if got != exp: ok = False
    print("0x%07x %-22s expect %s  got %s  %s" % (a, name, exp, got, mark))
print("RESULT:", "ALL OK" if ok else "MISMATCH DETECTED")
