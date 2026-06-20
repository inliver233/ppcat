# smali deliverable

这目录把 `test3` 已验证可编译的 reward stub 协作产物同步到 `test1`，避免后续继续跨分支手抄。

包含：

- `AdNoOpPluginV3.smali`
  - `FlutterPlugin + MethodCallHandler + EventChannel.StreamHandler + Runnable`
  - 4 个广告 `MethodChannel` 全 `success(null)`
  - `flutter_pangle_ads_event` 走 `EventSink`
  - reward 方法额外延时 30s 推 `onRewardArrived` + `onAdClose`

- `gen_stub_v3_final.py`
  - 从既有 smali 符号自动提取混淆 API 描述符并生成 `AdNoOpPluginV3`

限制：

- 这个 V3 主要补齐的是 `Pangle` 的 `EventChannel` 路线
- `GDT` 的动态 reward 子 channel 仍未被这份 stub 全覆盖
- 因此它适合作为协作基线，但不应被表述为“reward 全平台已闭环”
