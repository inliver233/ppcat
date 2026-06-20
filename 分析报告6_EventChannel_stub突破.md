# ★ 喵喵饿了 reward 的 EventChannel stub 突破（V3）

> 攻克了三方都没做完的"喵喵饿了 reward stub"难题。
> 学习了 test1 的 V2 lab（复现我的 MethodChannel.invokeMethod 方案，确认编译）+ test2 的 36 广告 NOP。
> test3 本轮：**解决 EventChannel codec 阻塞，产出可编译的 V3 stub（FlutterPlugin+MethodCallHandler+EventChannel.StreamHandler）**。

---

## 一、问题回顾（为什么 V1/V2 不够）

- **V1/V2**：广告 channel 注册 MethodCallHandler，method 全 `success(null)`。reward method 立即成功。
- **卡点（test1/test3 共识）**：Pangle reward 的 **onReward/onAdClose 事件走 EventChannel `flutter_pangle_ads_event`**，不是 MethodChannel.invokeMethod。V2 的 invokeMethod 推事件 → Dart 不监听 → **不发喵粮**。
- **反作弊**：`onReward Cheat Triggered!`(ref11545) 判即时 reward 作弊 → 需延时。

## 二、★ 本轮突破：EventChannel codec 阻塞解决

**Codec 阻塞**：EventChannel 构造需 codec 参数 `Lสۥ笔墨ۦ¡/สۥ۟۟۟;`（抽象基类），之前以为该类无无参构造无法实例化。

**解决（字节级）**：
- EventChannel ctor codec 参数类型 codepoints = `0xe2a 0x6e5 0x6df 0x6df 0x6df`（สۥ笔墨ۦ¡/สۥ۟۟۟，抽象基类 MethodCodec）。
- VideoPlayerApi Pigeon **真实构造** EventChannel 时传 `new สۥ笔墨ۦ¡/สۥ۟۟()`（codepoints `0xe2a 0x6e5 0x6df 0x6df`，**StandardMethodCodec 具体类**），可赋值给基类。
- **codec 类 `สۥ笔墨ۦ¡/สۥ۟۟` 确有 `<init>()V`**（直接读 smali 确认）。
- → **clone VideoPlayerApi 的构造方式即可**：`new สۥ笔墨ۦ¡/สۥ۟۟()` 传给 EventChannel ctor。

## 三、★ 关键教训：combining-mark 混淆的字节级陷阱

io.flutter.plugin.common.* 所有类被混淆到**同一个包** `สۥ笔墨ۦ¡`（codepoints 0xe2a,0x6e5,0x6e0,0x6e6,0x6e1），但显示渲染易误读。本包类（全 codepoint-exact 验证）：
- `สۥ笔墨ۦ¡/สۥ۟۟۠` = MethodChannel（ctor `(BinaryMessenger,String[,codec])V` + setMethodCallHandler `ۥ้้้้้้้้้้۟۟ۡ`）
- `สۥ笔墨ۦ¡/สۥ۟۟ۡ` = EventChannel（ctor `(BinaryMessenger,String,Codec)V` + setStreamHandler `ۥ้้้้้้้้้้۟۟ۡ`）
- `สۥ笔墨ۦ¡/สۥ۟۠۠` = MethodCall（.method 字段 `ۥ้้۟۟ۡ`）
- `สۥ笔墨ۦ¡/สۥ۟۟۠$สۥۣ۟۟` = Result（success `ۥ้้้้۟۟ۡ`）
- `สۥ笔墨ۦ¡/สۥ۟۟ۡ$สۥۣ۟۟` = EventChannel.StreamHandler（onListen `ۥ้้۟۟ۡ(Object,EventSink)V`）
- `สۥ笔墨ۦ¡/สۥ۟۟ۡ$สۥ۟۟ۤ` = EventSink（success `ۥ้้۟۟ۡ(Object)V`）
- `สۥ笔墨ۦ¡/สۥ۟۟` = StandardMethodCodec（<init>()V）
- BinaryMessenger = `สۥ笔墨ۦ¡/สۥ۟۠ۢ`（getBinaryMessenger 返回）

**陷阱**：曾因 `bmess` 描述符正则丢了前导 `L` → 编译报"no viable alternative"；因 dummy-method hack → "missing END_METHOD"。**最终全部用从 V1（已验证编译）+ EventChannel 接口文件直接读取描述符**，零手工拼接，apktool b 验证通过。

## 四、★ 交付物：AdNoOpPluginV3.smali（已 apktool b 编译验证）

- `.implements FlutterPlugin, MethodCallHandler, EventChannel.StreamHandler, Runnable`
- **onAttachedToEngine**：4 个 no-op MethodChannel（flutter_pangle_ads/ksad/google_mobile_ads/gdt_plugins）+ **EventChannel `flutter_pangle_ads_event`**（codec=StandardMethodCodec，setStreamHandler(this)）
- **StreamHandler.onListen(args, sink)**：存 EventSink（Dart 开始监听时）
- **onMethodCall**：全 `success(null)`；若 method 含 "Reward" → 起 Thread sleep 30s（绕反作弊时间阈值）→ 通过 EventSink.success(HashMap{action:onRewardArrived}) + (HashMap{action:onAdClose}) 推 reward 事件
- **run()**：reward 事件推送线程（延时 + 双事件）

验证（classes2.dex 含）：AdNoOpPluginV3 / flutter_pangle_ads_event / eventSink / onRewardArrived / onAdClose / flutter_pangle_ads 全部就位。

## 五、用 V3 替换 V1

- 注册器把 `AdNoOpPlugin` → `AdNoOpPluginV3`（二选一，勿同时注册）。
- V1（MethodChannel-only）仍是安全基线；V3 是喵喵饿了 reward 的实验性升级。

## 六、与 reward-prompt 链的关系（test3 已查清）

- 喵喵饿了 reward-prompt = 0xbc5dc8（"是否看推荐信息获取喵粮喂喵？"）→ reward 广告 → 发喵粮。
- 此链**不经 isNoAdLock 门 0x7e8534**（独立）。
- V3 的 EventChannel `flutter_pangle_ads_event` 推 onRewardArrived 应触发 Dart reward 流程 → 发喵粮 → 块消失。
- **风险**：Dart 侧具体事件 key 名（action/adType 还是其他）未 100% 确认；若不匹配，Dart 忽略→无效但不 crash（注册器 try/catch 兜底）。test1 已解码 Pangle 事件格式（onRewardArrived/verify/amount），可据此调整 V3 推送的 map key。

## 七、生成器

`analysis_workdir/smali_deliverable/gen_stub_v3_final.py`：从 V1+EventChannel 接口文件直接读描述符，零手工拼接，可复跑。

> 一句话：test3 解决了 EventChannel codec 阻塞（codec 类有 <init>()V，clone VideoPlayerApi 构造），产出**可编译的 V3 EventChannel reward stub**（FlutterPlugin+MethodCallHandler+StreamHandler），经 apktool b 验证——这是三方都没做完的喵喵饿了 reward 难题的可行 stub。主控装机测 V3，点喵喵饿了~30s 后应得喵粮+块消失。
