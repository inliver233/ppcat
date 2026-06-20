# stub_v2_lab 本地实验记录

目标：

- 在 `test1` 本地复建并验证 `test3` 的 `AdNoOpPluginV2` 思路
- 不只引用“另一分支说可编译”，而是在当前仓库里完成：
  - `smali` 生成
  - `GeneratedPluginRegistrant` 注入
  - `apktool b` 编译通过

## 输入

- 基础 APK：
  - [analysis_round10/ppcat_round7.apk](/root/ppcat_repo/analysis_round10/ppcat_round7.apk)
- 工具：
  - `/root/ppcat_tools/bin/apktool` = `3.0.2`
  - `/usr/bin/java`

## 过程

1. 解包到：
   - `analysis_round12/stub_v2_lab/`
2. 运行：
   - [build_stub_v2_lab.py](/root/ppcat_repo/analysis_round12/build_stub_v2_lab.py)
3. 生成：
   - [stub_v2_lab/smali_classes2/com/gentle/ppcat/AdNoOpPluginV2.smali](/root/ppcat_repo/analysis_round12/stub_v2_lab/smali_classes2/com/gentle/ppcat/AdNoOpPluginV2.smali)
4. 注入：
   - [stub_v2_lab/smali_classes2/สۥ۠ۦۢ/สۥ۟۟ۡ.smali](/root/ppcat_repo/analysis_round12/stub_v2_lab/smali_classes2/สۥ۠ۦۢ/สۥ۟۟ۡ.smali)
   - 插入 `:try_start_ad_v2` 注册块，注册 `AdNoOpPluginV2`
5. 编译：
   - `/root/ppcat_tools/bin/apktool b analysis_round12/stub_v2_lab -o analysis_round12/stub_v2_lab_unsigned.apk`

## 本地验证结果

### 1. smali 生成成功

- `AdNoOpPluginV2.smali` 已生成
- 关键通道：
  - `flutter_pangle_ads`
  - `ksad`
  - `plugins.flutter.io/google_mobile_ads`
  - `plugins.hetian.me/gdt_plugins`

### 2. registrant 注入成功

- `GeneratedPluginRegistrant` 中已存在：
  - `:try_start_ad_v2`
  - `new-instance v1, Lcom/gentle/ppcat/AdNoOpPluginV2;`

### 3. apktool 编译通过

- 输出 APK：
  - [stub_v2_lab_unsigned.apk](/root/ppcat_repo/analysis_round12/stub_v2_lab_unsigned.apk)
- 编译成功说明：
  - `smali` 语法有效
  - 混淆接口符号解析正确
  - `registerWith` 注入块不会破坏 dex 构建

## V2 当前语义

- 所有广告 method：
  - 立即 `result.success(null)`
- 若方法名包含 `Reward`：
  - 启动后台线程
  - `sleep(30000)`
  - 通过 `flutter_pangle_ads` channel 依次 `invokeMethod`：
    - `onRewardArrived`
    - `onAdClose`

## 现阶段边界

- 这是**编译级本地验证**，不是装机运行级验证
- 当前只对 `Pangle` 通道显式模拟了 reward 事件
- 还没有补：
  - `flutter_pangle_ads_event` 的 `EventChannel` 形态
  - `GDT` 独立 reward 子 channel 的事件模拟
  - `Kwad` reward 回调的模拟

## 结论

`test1` 现在已经可以独立说：

- `AdNoOpPluginV2` 不是只存在于 `test3` 的报告或静态草案
- 它已经在 `test1` 本地被成功复建并通过 `apktool b`
- 因此这条 `reward/no-op` 升级路径已经成为 `test1` 自己可继续深化的实验基础
