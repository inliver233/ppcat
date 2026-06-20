#!/usr/bin/env python3
"""Build AdNoOpPluginV2 inside analysis_round12/stub_v2_lab.

Goal:
- reproduce test3's V2 reward/no-op stub idea inside test1's local apktool lab
- keep the process repo-local and repeatable
- avoid relying on /root/tools hardcoded paths from test3
"""

from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "analysis_round12" / "stub_v2_lab"


def rd(rel: str) -> str:
    return (LAB / rel).read_text(encoding="utf-8")


def wr(rel: str, text: str) -> None:
    path = LAB / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_v2_smali() -> Path:
    flutter_plugin_iface = "Lสۦۣ۟ۡ/สۥ۟۟ۡ;"
    mch_iface = "Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;"
    binding_cls = "Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;"
    mchannel_cls = "Lสۥ۠ۦۡ/สۥ۟۟۠;"
    bmessenger_cls = "Lสۥ۠ۦۡ/สۥ۟۠ۢ;"
    mcall_cls = "Lสۥ۠ۦۡ/สۥ۟۠۠;"
    result_iface = "Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;"

    fp_src = rd("smali_classes2/สۦۣ۟ۡ/สۥ۟۟ۡ.smali")
    fp_methods = re.findall(r"\.method public abstract (\S+)\(Lสۦۣ۟ۡ/สۥ۟۟ۡ\$สۥ۟۠ۢ;\)V", fp_src)
    attach_name = max(fp_methods, key=len)
    detach_name = min(fp_methods, key=len)

    mch_src = rd("smali_classes2/สۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ.smali")
    onmethod_name = re.search(
        r"\.method public abstract (\S+)\(Lสۥ۠ۦۡ/สۥ۟۠۠;Lสۥ۠ۦۡ/สۥ۟۟۠\$สۥۣ۟۟;\)V",
        mch_src,
    ).group(1)

    sq = rd("smali_classes2/สۥ۟ۥۥ/สۥ۟۟ۢ.smali")
    getbm = re.search(
        r"invoke-virtual \{p1\}, Lสۦۣ۟ۡ/สۥ۟۟ۡ\$สۥ۟۠ۢ;->(\S+)\(\)Lสۥ۠ۦۡ/สۥ۟۠ۢ;",
        sq,
    ).group(1)
    setmch = re.search(
        r"Lสۥ۠ۦۡ/สۥ۟۟۠;->(\S+)\(Lสۥ۠ۦۡ/สۥ۟۟۠\$สۥ۟۟ۢ;\)V",
        sq,
    ).group(1)

    res_src = rd("smali_classes2/สۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟.smali")
    success_name = re.search(r"\.method public abstract (\S+)\(Ljava/lang/Object;\)V", res_src).group(1)

    # Verified by earlier reverse-work on the plugin channel API.
    invoke_method_no_cb = "ۥ้้้้้้۟۟ۡ"
    call_method_field = "ۥ้้۟۟ۡ"

    channels = [
        "flutter_pangle_ads",
        "ksad",
        "plugins.flutter.io/google_mobile_ads",
        "plugins.hetian.me/gdt_plugins",
    ]

    attach_lines = []
    attach_lines.append("    .locals 3")
    attach_lines.append(f"    invoke-virtual {{p1}}, {binding_cls}->{getbm}(){bmessenger_cls}")
    attach_lines.append("    move-result-object v0")
    for channel in channels:
        attach_lines.append(f"    new-instance v1, {mchannel_cls}")
        attach_lines.append(f'    const-string v2, "{channel}"')
        attach_lines.append(
            f"    invoke-direct {{v1, v0, v2}}, {mchannel_cls}-><init>({bmessenger_cls}Ljava/lang/String;)V"
        )
        if channel == "flutter_pangle_ads":
            attach_lines.append(
                f"    iput-object v1, p0, Lcom/gentle/ppcat/AdNoOpPluginV2;->pangleChannel:{mchannel_cls}"
            )
        attach_lines.append(f"    invoke-virtual {{v1, p0}}, {mchannel_cls}->{setmch}({mch_iface})V")
    attach_lines.append("    return-void")

    smali = f""".class public Lcom/gentle/ppcat/AdNoOpPluginV2;
.super Ljava/lang/Object;
.source "AdNoOpPluginV2.java"
.implements {flutter_plugin_iface}
.implements Ljava/lang/Runnable;
.implements {mch_iface}

# V2: no-op + reward simulation (delayed onRewardArrived/onAdClose on Pangle).
.field private pangleChannel:{mchannel_cls}

.method public constructor <init>()V
    .locals 0
    invoke-direct {{p0}}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public {attach_name}({binding_cls})V
{chr(10).join(attach_lines)}
.end method

.method public {detach_name}({binding_cls})V
    .locals 0
    return-void
.end method

.method public {onmethod_name}({mcall_cls}{result_iface})V
    .locals 3
    iget-object v0, p1, {mcall_cls}->{call_method_field}:Ljava/lang/String;
    const/4 v1, 0x0
    invoke-interface {{p2, v1}}, {result_iface}->{success_name}(Ljava/lang/Object;)V
    const-string v2, "Reward"
    invoke-virtual {{v0, v2}}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v2
    if-eqz v2, :cond_no_reward
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV2;->pangleChannel:{mchannel_cls}
    if-eqz v2, :cond_no_reward
    new-instance v2, Ljava/lang/Thread;
    invoke-direct {{v2, p0}}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V
    invoke-virtual {{v2}}, Ljava/lang/Thread;->start()V
    :cond_no_reward
    return-void
.end method

.method public run()V
    .locals 5
    :try_start_0
    const-wide/32 v0, 0x7530
    invoke-static {{v0, v1}}, Ljava/lang/Thread;->sleep(J)V
    :try_end_0
    .catch Ljava/lang/InterruptedException; {{:try_start_0 .. :try_end_0}} :catch_0
    goto :send
    :catch_0
    :send
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV2;->pangleChannel:{mchannel_cls}
    if-eqz v2, :done
    const-string v3, "onRewardArrived"
    const/4 v4, 0x0
    invoke-virtual {{v2, v3, v4}}, {mchannel_cls}->{invoke_method_no_cb}(Ljava/lang/String;Ljava/lang/Object;)V
    const-wide/16 v0, 0x1f4
    invoke-static {{v0, v1}}, Ljava/lang/Thread;->sleep(J)V
    const-string v3, "onAdClose"
    invoke-virtual {{v2, v3, v4}}, {mchannel_cls}->{invoke_method_no_cb}(Ljava/lang/String;Ljava/lang/Object;)V
    :done
    return-void
    .catch Ljava/lang/InterruptedException; {{:send .. :done}} :catch_1
    :catch_1
    return-void
.end method
"""

    out = LAB / "smali_classes2/com/gentle/ppcat/AdNoOpPluginV2.smali"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(smali, encoding="utf-8")
    return out


def patch_registrant() -> tuple[Path, str, str]:
    reg_path = LAB / "smali_classes2/สۥ۠ۦۢ/สۥ۟۟ۡ.smali"
    reg = reg_path.read_text(encoding="utf-8")

    getreg = re.search(
        r"invoke-virtual \{p0\}, Lio/flutter/embedding/engine/สۥ۟۟ۡ;->(\S+)\(\)Lสۦۣ۟ۡ/สۥ۟۠ۢ;",
        reg,
    ).group(1)
    add = re.search(r"Lสۦۣ۟ۡ/สۥ۟۠ۢ;->(\S+)\(Lสۦۣ۟ۡ/สۥ۟۟ۡ;\)V", reg).group(1)

    block = f"""
    :try_start_ad_v2
    invoke-virtual {{p0}}, Lio/flutter/embedding/engine/สۥ۟۟ۡ;->{getreg}()Lสۦۣ۟ۡ/สۥ۟۠ۢ;

    move-result-object v0

    new-instance v1, Lcom/gentle/ppcat/AdNoOpPluginV2;

    invoke-direct {{v1}}, Lcom/gentle/ppcat/AdNoOpPluginV2;-><init>()V

    invoke-interface {{v0, v1}}, Lสۦۣ۟ۡ/สۥ۟۠ۢ;->{add}(Lสۦۣ۟ۡ/สۥ۟۟ۡ;)V
    :try_end_ad_v2
    .catch Ljava/lang/Exception; {{:try_start_ad_v2 .. :try_end_ad_v2}} :catch_ad_v2

    :catch_ad_v2
"""

    if ":try_start_ad_v2" not in reg:
        reg = reg.replace("    :try_start_0\n", block + "    :try_start_0\n", 1)
        reg_path.write_text(reg, encoding="utf-8")
    return reg_path, getreg, add


def main() -> int:
    out = build_v2_smali()
    reg_path, getreg, add = patch_registrant()
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"patched {reg_path.relative_to(ROOT)}")
    print(f"symbols: getRegistry={getreg!r} add={add!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
