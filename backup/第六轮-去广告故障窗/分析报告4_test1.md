# 第四轮分析报告:去广告 + 故障窗 Patch 清单

> 分支: `test1`
>  
> 本轮遵守“纯静态分析”。交付物只包含报告、解密脚本、明文表与 patch 清单，不修改原始二进制、不分发 APK。

## 1. 结论摘要

- 本轮已经把 4 个核心广告插件的 **Flutter 绑定明文**、**Java 桥接入口**、**SDK 初始化锚点** 基本固定下来。
- 绑定阶段的加密字符串并不是只能靠 `0x549c84` 那个巨型 `sparse-switch` 分发表。至少在广告插件 `registerWith/binding` 阶段，实际明文来自各插件自己的 `[B, B] -> String` 包装器，按固定 XOR 规则可离线恢复。
- 最干净的去广告思路仍是: **只短路 4 个已确认广告插件的注册/绑定**，并配套 **Dart 侧故障窗补丁**。
- 故障窗最稳的 Dart 补丁不是直接 NOP `0xbc1020`。更稳的是把 `0xbc1020` 改成仍在失败条件下跳到现成的 `return null` 尾声 `0xbc1060`。

## 2. 交叉验证

- 参考了 `origin/test2:分析报告4.md` 与 `origin/test2:analysis_workdir/fault_dialog_analysis.txt`。
- 一致结论:
  - 故障正文 builder = `0xbbc22c`
  - 上层候选编排器 = `0xbc0f40`
  - 条件分支 = `0xbc1020`
- 本分支补充并修正:
  - 绑定字符串已离线稳定解出，不再停留在“算法框架”层。
  - `0xbc1020` 不建议直接改 NOP。因为 `0xbc1024` 起始的 fall-through 路径会消费前面 `BL` 的返回对象，若返回 `null`，直接 NOP 存在状态机/空对象风险。
  - 更稳的是把 `0xbc1020` 改成 `B.EQ 0xbc1060`，直接走该函数现成的 `MOV X0, X22; RET` 尾声。

## 3. 加密字符串解密

### 3.1 本轮确认的两类解密器

- 中央大分发表:
  - `0x549c84` `Lสۦ۠ۦۨ/สۥ۟۟ۡ;->ۥ้้۟۟ۡ([B [B)Ljava/lang/String;`
  - 结构是多层 `String.hashCode() + xor + sparse-switch`，更像通用分发器/校验器。
- 绑定阶段小包装器:
  - `0x4be4e0` `Lสۥ۠ۦ/สۥ۟ۤۦ;->ۥ้้۟۟ۡ([B [B)Ljava/lang/String;` (AdMob)
  - `0x491068` `Lสۥ۠ۤۧ/สۥ۟۟ۤ;->ۥ้้۟۟ۡ([B [B)Ljava/lang/String;` (Kwad)
  - `0x4c8d00` / `0x4e9de8` 所属类内部也复用同类 `[B,B] -> String` 调用

### 3.2 已验证的离线规则

对绑定阶段的 payload，明文可按以下规则恢复:

```python
def decode(cipher: bytes, key: bytes) -> bytes:
    if key and key[-1] == 0:
        key = key[:-1]
    repeated = key[1:] if len(key) > 1 else key
    return bytes(c ^ repeated[i % len(repeated)] for i, c in enumerate(cipher))
```

说明:

- `key` 尾部常带一个 `0x00` 终止字节，应先裁掉。
- 重复时使用 `key[1:]`，不使用首字节。
- 对 `GDT` 第一组 payload，cipher 自身也要裁掉末尾 `0x00` 才与对象池明文完全对齐。

### 3.3 明文结果

离线脚本: [analysis_round4/decode_plugin_bindings.py](/root/ppcat_repo/analysis_round4/decode_plugin_bindings.py)

明文表: [analysis_round4/plugin_binding_plaintexts.tsv](/root/ppcat_repo/analysis_round4/plugin_binding_plaintexts.tsv)

关键结果:

| code_off | 插件 | 明文 |
|---|---|---|
| `0x4bcfe8` | AdMob binding | `plugins.flutter.io/google_mobile_ads` |
| `0x4bcfe8` | AdMob platform view | `plugins.flutter.io/google_mobile_ads/ad_widget` |
| `0x4c8d00` | Pangle binding | `flutter_pangle_ads` |
| `0x4c8d00` | Pangle event | `flutter_pangle_ads_event` |
| `0x492e3c` | Kwad binding helper | `flutterPluginBinding` |
| `0x492e3c` | Kwad channel | `ksad` |
| `0x4e9de8` | GDT binding | `plugins.hetian.me/gdt_plugins` |
| `0x4e9de8` | GDT banner view | `plugins.hetian.me/gdtview_banner` |
| `0x4e9de8` | GDT native view | `plugins.hetian.me/gdtview_native` |

注:

- `GDT` 第一组 payload 直接按规则解得 `plugins.hetian.me/gdt_plugins8`，但裁掉 payload 尾 `0x00` 后得到 `plugins.hetian.me/gdt_plugins`，且该字符串已在对象池 `ref=31299` 明确出现，因此最终以对象池锚点为准。

## 4. 广告插件剖析

### 4.1 确认要动 / 不要动的插件

不要动:

- `Lสۦ۠ۦ/สۥ۟۠ۢ;` = file picker
- `Lสۥۡۨۥ/สۥ۟۠ۢ;` = picture-in-picture wrapper
- `Lสۦ۟ۡۥ/สۥ۟۠ۢ;` = install helper / VIEW intent 辅助类

应纳入去广告 patch:

- `Lสۥ۠ۦ/สۥ۟ۢ;` = AdMob
- `Lสۥ۠ۦۧ/สۥ۟۟ۡ;` = Pangle
- `Lสۥ۠ۤۧ/สۥ۟۠ۢ;` = Kwad
- `Lสۥۡۨ/สۥ۟۠ۢ;` = GDT

### 4.2 插件分析表

| SDK | 插件类 | 绑定入口 | Channel / View | 初始化锚点 | 展示 / 回调锚点 |
|---|---|---|---|---|---|
| AdMob | `Lสۥ۠ۦ/สۥ۟ۢ;` | `0x4bcfe8` | `plugins.flutter.io/google_mobile_ads`, `.../ad_widget` | `0x4b5c18` 调 `MobileAds.*` | `0x4a9274` 命中 `setOnPaidEventListener`; `0x4c49f8` / `0x4c3e20` 命中 `NativeAdView` |
| Pangle | `Lสۥ۠ۦۧ/สۥ۟۟ۡ;` | `0x4c8d00` | `flutter_pangle_ads`, `flutter_pangle_ads_event` | `0x4c9c48` 调 `TTAdSdk.init(..., TTAdSdk$InitCallback)` | `0x50ec0c` `showFullScreenVideoAd`; `0x50b834` `showRewardVideoAd`; `0x50cc28` `setExpressInteractionListener` |
| Kwad | `Lสۥ۠ۤۧ/สۥ۟۠ۢ;` | `0x492e3c` | `ksad` | `0x491700` 调 `SdkConfig$Builder.appId/build`, `KsAdSDK.init/start/getSDKVersion` | `0x5520bc` `setAdInteractionListener` + `showInterstitialAd`; `0x551e28` `loadInterstitialAd` |
| GDT | `Lสۥۡۨ/สۥ۟۠ۢ;` | `0x4e9de8` | `plugins.hetian.me/gdt_plugins`, `.../gdtview_banner`, `.../gdtview_native` | `0x4e8430` 调 `MultiProcessFlag.setMultiProcess`, `GDTAdSdk.initWithoutStart`, `GDTAdSdk.start(OnStartListener)` | `0x3a0fa0` / `0x3a1394` 命中 `GDTAdSdk$OnStartListener.onStartSuccess/onStartFailed`; SDK 侧 `SplashAD` / `UnifiedInterstitialAD` / `NativeExpressAD` 类均在 dex 中可见 |

补充:

- Pangle 更深层桥接类还包含:
  - `0x4cb0e0` `TTAdSdk.getAdManager`
  - `0x4cb1a0` `TTAdSdk.updateAdConfig`
  - `0x4cb368` / `0x4cb5a8` / `0x4cb7e8` `TTAdSdk.isInitSuccess`
- AdMob 初始化桥接还可见于:
  - `0x4b19e0` `Lสۥ۠ۦ/สۥ۟ۡ۟;->...` 调 `MobileAds.initialize(Context)`

## 5. 推荐去广告方案

### 5.1 推荐方案

推荐组合:

1. Java 层只短路 4 个已确认广告插件的注册/绑定
2. Dart 层同时 patch 故障窗

原因:

- 这是最小误伤面。
- 不碰 file picker / PIP / install helper。
- 不需要深改各 SDK 内部回调状态机。

### 5.2 可实施 patch 点

#### 方案 A: 直接短路 4 个广告 binding 方法

最干净、最容易回滚。

建议改动:

- `0x4bcfe8` AdMob binding 入口改 `return-void`
- `0x4c8d00` Pangle binding 入口改 `return-void`
- `0x492e3c` Kwad binding 入口改 `return-void`
- `0x4e9de8` GDT binding 入口改 `return-void`

理由:

- 这 4 个方法就是桥接层真正创建 `MethodChannel` / `PlatformView` 的入口。
- 比在总 `registerWith` 里按 try 块删更直观，也更不容易误伤相邻功能插件。

smali 级实施原则:

- 在对应方法体起始直接替换为:

```smali
.locals 0
return-void
```

#### 方案 B: 在总 registerWith 里只清空 4 个广告 try 块

仍可用，但不如方案 A 直观。

总注册函数:

- `Lสۥ۠ۦۢ/สۥ۟۟ۡ;->registerWith(...)V`
- `code_off = 0x4c7858`

本轮采用的精确注册映射:

- `+0x0098` = GDT
- `+0x00f8` = Pangle
- `+0x0158` = AdMob
- `+0x01b8` = Kwad

不建议碰:

- `+0x0038` file picker
- `+0x0050` PIP wrapper
- `+0x0188` install helper

## 6. 故障窗触发逻辑

### 6.1 已确认链路

- 故障正文 builder:
  - `0x00bbc22c`
  - 关键取串:
    - `0x00bbc31c  LDR X16, [X16,#3176]` -> slot `0x13c68` -> `ref=27673`
- 上层候选编排器:
  - `0x00bc0f40`
- 判定分支:
  - `0x00bc101c  1f 00 16 6b  CMP W0, W22`
  - `0x00bc1020  a0 12 00 54  B.EQ 0x00bc1274`
- 弹窗构造支路:
  - `0x00bc1274..0x00bc1394`
- 关键副作用调用:
  - `0x00bc133c  e4 c4 e2 97  BL 0x008b1390`

### 6.2 为什么不推荐直接 NOP `0xbc1020`

`0xbc1020` 前面的 `BL 0xf82494` 返回 `null` 时，fall-through 会进入:

- `0xbc1024 STR X0, [X15,#-8]!`
- `0xbc1028 BL 0x62d2ec`
- `0xbc1034 LDUR X0, [X29,#-112]`
- `0xbc1038 LDUR W2, [X0,#31]`

这条路径会继续消费前面的返回对象和状态字段。若只是把 `B.EQ` NOP 掉，`null` 情况会直接跌进“正常路径”，存在状态机/空对象风险。

### 6.3 推荐故障窗 patch

#### 首选: 重定向失败条件到现成 `return null` 尾声

- 地址: `0x00bc1020`
- 原始:
  - `a0 12 00 54`
  - 语义: `B.EQ 0x00bc1274`
- 推荐改为:
  - `00 02 00 54`
  - 语义: `B.EQ 0x00bc1060`

校验:

- `0x00bc1060` 起始就是现成尾声:
  - `0x00bc1060  e0 03 16 aa  MOV X0, X22`
  - `0x00bc1064  ef 03 1d aa  MOV X15, X29`
  - `0x00bc1068  fd 79 c1 a8  LDP X29, X30, [X15],#16`
  - `0x00bc106c  c0 03 5f d6  RET`

效果:

- 仅在 `W0 == null` 的“失败判定”分支里提前返回 `null`
- 避免进入 `0xbc1274..0xbc1394` 的故障窗构造链
- 风险低于整函数 return 或直接 NOP 分支

#### 次选: NOP showDialog 侧效调用

- 地址: `0x00bc133c`
- 原始:
  - `e4 c4 e2 97`
  - `BL 0x008b1390`
- 备选 patch:
  - `1f 20 03 d5`
  - `NOP`

说明:

- 这是更“局部”的补丁，只砍掉故障窗构造支路里的关键副作用调用。
- 但它位于分支深处，仍需依赖前半段对象构造链稳定执行。
- 风险上仍高于“直接跳到现成 return null”。

#### 不推荐

- `0xbc1020 -> NOP`
- `0xbc0f40` 入口直接改 `return null`

原因:

- 前者会让 `null` 跌入正常路径。
- 后者虽然可能有效，但本轮没有把该状态机所有外部依赖完全证明为“入口直接 return 无副作用”。

## 7. 开屏广告

对象池已有明确锚点:

- `loadAppOpenAd`
- `showSplashAd`
- `loadSplashScreenAd`
- `AdMob_Splash`
- `AdPgl_Splash`
- `AdNet_Splash`
- `AdKs_Splash`
- `ksadsdk_splash_daily_show_count`

结合 Java 层:

- Pangle:
  - `0x50efb8` -> `TTAdNative.loadFullScreenVideoAd(...)`
  - `0x50ec0c` -> `showFullScreenVideoAd(...)`
  - `0x50d6b0` -> `loadBannerExpressAd(...)`
- Kwad:
  - `0x551e28` -> `KsLoadManager.loadInterstitialAd(...)`
  - `0x5520bc` -> `showInterstitialAd(...)`
- GDT dex 内可见 `SplashAD`

实操建议:

- 若已执行“短路 4 个 binding 方法 + Dart 故障窗补丁”，开屏广告大概率会一并失效。
- 本轮未继续强行给出单独 Dart 开屏函数入口地址，原因是当前组合 patch 已足够覆盖 Java 桥接层展示路径。

## 8. Umeng

本轮证据:

- 对象池:
  - `ref=27990` -> `5cecdbb14ca3575f39000861`
  - `ref=30406` -> `UMENG_APPKEY`
  - `ref=13228` -> `flutter_umeng_analytics`
- dex 侧:
  - `0x54ba38` `Lสۦۡۢ/สۥ۟۟ۡ;->...` 读取 manifest `UMENG_APPKEY`
  - `0x57a340` `Lส⁣⁤⁠⁠⁠⁣⁠⁠⁤⁠⁠⁤⁠⁤⁣/สۥ۟۟ۡ;->...` 命中 `flutter_umeng_analytics`
  - `0x4d20ac` 的 `<clinit>` 含 `UMConfigure.setLogEnabled(true)` 相关提示串

本轮没有静态抓到明确的 `invoke-static ... UMConfigure;->init(...)` 调用点，因此只能给保守结论:

- Umeng 插件桥接存在
- `UMENG_APPKEY` manifest 读取存在
- 若要禁用，应优先从:
  - `flutter_umeng_analytics` 对应插件 binding
  - 或 manifest / Application 初始化桥接
  入手继续静态确认

## 9. 最终 patch 清单

### 9.1 推荐执行顺序

1. 短路 4 个广告 binding 方法:
   - `0x4bcfe8` AdMob
   - `0x4c8d00` Pangle
   - `0x492e3c` Kwad
   - `0x4e9de8` GDT
2. Dart 层补丁:
   - `0x00bc1020: a0 12 00 54 -> 00 02 00 54`

### 9.2 备选

- 若首选仍有故障窗残留，再试:
  - `0x00bc133c: e4 c4 e2 97 -> 1f 20 03 d5`

### 9.3 明确不要动

- `0x00913bf8`
- `Lสۦ۠ۦ/สۥ۟۠ۢ;` file picker
- `Lสۥۡۨۥ/สۥ۟۠ۢ;` PIP wrapper
- `Lสۦ۟ۡۥ/สۥ۟۠ۢ;` install helper

## 10. 本轮新增产物

- [analysis_round4/decode_plugin_bindings.py](/root/ppcat_repo/analysis_round4/decode_plugin_bindings.py)
- [analysis_round4/plugin_binding_plaintexts.tsv](/root/ppcat_repo/analysis_round4/plugin_binding_plaintexts.tsv)
- [分析报告4.md](/root/ppcat_repo/分析报告4.md)
