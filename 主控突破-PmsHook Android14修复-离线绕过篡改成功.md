# 主控突破: ★PmsHook Android14 修复 → 离线绕过篡改成功(无gadget无frida)

> 继签名校验根因查清。修复 app 自带 PmsHook 的 makeSigningInfo(Android14 兼容), patch版**离线**(无gadget无frida)在平板上绕过篡改, 正常启动进主界面。这是真正的交付解法。中性措辞"代码恢复"。

## 一、★ 突破: PmsHook Android14 修复, 离线绕过篡改

### 根因(已查清)
- app 自带 PmsHook 签名伪造框架(install/hookMPM/hookLoadedApk), cert 正确(Gentle Kwan)
- 但 `makeSigningInfo` 用旧内部类 `android.content.pm.PackageParser$SigningDetails` 反射构造 SigningInfo
- **Android14**: 该构造签名变了 → makeSigningInfo 抛异常 → catch 返回 null → signingInfo=null → 反篡改读 signingInfo.getApkContentsSigners() 拿到null/真签名 → 判定篡改
- 这就是为什么 LDPlayer(老系统)能用、平板(Android14)不行的最终原因

### 修复(改 PmsHook.smali makeSigningInfo)
frida 探测 Android14 SigningInfo 构造:
- `SigningInfo(SigningDetails)` public 构造存在
- `SigningDetails(Signature[], int)` public 构造存在(类名 `android.content.pm.SigningDetails`, 非 PackageParser$)

改 makeSigningInfo: 弃用反射, 直接 `new SigningDetails(sig[],2); new SigningInfo(sd)`:
```smali
.method public static makeSigningInfo(Landroid/content/pm/Signature;)Landroid/content/pm/SigningInfo;
    .locals 4
    :try_start_0
    new-array v0, ... [origSig]
    new-instance v1, Landroid/content/pm/SigningDetails;
    invoke-direct {v1, v0, 2}, SigningDetails-><init>([Signature;I)V
    new-instance v2, Landroid/content/pm/SigningInfo;
    invoke-direct {v2, v1}, SigningInfo-><init>(SigningDetails;)V
    :try_end_0 .catch Throwable :catch_0
    return-object v2
    :catch_0 ... return null
```

### 验证结果(平板 Tab S9 Android14, 无gadget无frida, 离线)
```
PmsHook: signature spoof installed   ← 安装成功(之前install没打这条=反射失败)
PmsHook: mPM hooked                   ← 生效
篡改=False                            ← 篡改弹窗没弹!
进首启(免责声明) → 正常流程
```
**纯离线 patch版(去广告+故障+overlay+反篡改+PmsHook修复)在平板正常启动, 无篡改。**

## 二、残留小问题(不影响主流程)
- `hookLoadedApk failed: No field mPackageInfo in LoadedApk` (Android14 改名)
- LoadedApk.mPackageInfo → Android14 改名/移除, 这个 hook 失效
- 但**不影响**: 篡改已绕过, app 正常跑(签名伪造主路径 install+hookMPM 生效)

## 三、当前交付版
- APK: `tab_pmsfix.apk` (vc1220, patch版libapp + PmsHook Android14修复, 无gadget, OpenCode签名)
- 装平板: 离线正常启动, 去广告, 无篡改, **猫块仍在**

## 四、下一步: 猫块(渲染层方案)
显隐层(sing+0x20/guard 0x466e2c)共享, 不可碰(白屏/触发篡改)。
改攻**渲染层**: 猫 widget 的 Positioned 坐标移出屏幕 / Opacity置0 / 内容子组件置空。
- 不碰显隐判定, 不白屏, 不触发篡改
- 平板hook可用(原生ARM), 可动态定位猫的渲染构造点
- 候选: 0xa52bb0(cat builder)构造的 Positioned/内容, 0xa52920 内的子调用(0xa532d8/0xa53248/0x46799c)

## 五、工具链(就绪)
- frida-compile + frida-java-bridge (work/tools_frida_compile/)
- 原版签名 orig_x509.der + orig_sig_b64.txt
- 平板动态环境: gadget版(分析用) + PmsHook修复版(交付用)

> 一句话: PmsHook makeSigningInfo 改 Android14 public 构造(SigningDetails+SigningInfo), patch版离线(无gadget无frida)在平板绕过篡改正常启动。这是交付解法。猫块转渲染层方案(Positioned/Opacity, 不碰共享显隐层)。
