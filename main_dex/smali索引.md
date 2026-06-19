# smali 类索引：广告/导入/反射相关（app 自有 ส/了 混淆类）
# 来源：apktool 反编译（部分 ส 类可用，了 类未解出）

## 广告 SDK 初始化调用者（ส 类）
- AdMob MobileAds.initialize: smali_classes2/สۥ۠ۦ/สۥ۟ۡ۟.smali, สۥ۠ۦ/สۥ۟ۢ.smali
- Kwad SdkConfig: smali_classes2/สۥ۠ۤۧ/สۥ۟۠ۢ.smali
- Pangle/CSJ TTAdSdk: smali_classes2/สۥ۠ۦۧ/สۥ۟۠ۢ.smali

## Flutter 平台通道（P10 反篡改 + 功能通道）
- 通道主类: smali_classes2/สۥ۟ۥۥ/ (含 onMethodCall, sanitize chokepoint)
- 自定义 Application: com/gentle/ppcat/App.smali (装 PMS 代理)
- 探针 spoof: com/gentle/ppcat/hook/Dbg.smali

## 导入源相关 Dart 通道方法名（对象池已确认）
- bookSource, import, importall, importonline, subscribe

## classes2.dex 含 类 L了/了; 字段 了（apktool 未解出，需 jadx/dexdump 直接分析）
