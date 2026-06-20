# 第八轮运行时验证硬事实 (2026-06-20)
# 设备 LDPlayer9 127.0.0.1:5555, work/build, versionCode递增法装机

## 关键方法论突破 (解决之前反复出现的"状态污染/装错"bug)
- **install -r 同签名同versionCode 不替换 libapp.so!** 必须每次递增 versionCode(apktool.yml)才能强制覆盖 native lib。
  - 验证:reward版libapp install -r(versionCode不变)→设备0xba0bbc仍e00f2036(没换);versionCode 1143→1144后→7f000014(换了)。
- **pm clear 清掉书架数据**, 测阅读页功能需 install -r(保留数据)+versionCode递增(强制换lib)。
- **首启弹窗序列**(清数据后): 免责声明(我已知晓@822,1752) → 有时跟提醒191227(取消@624,1445) → 主界面。
- **免责声明SP键名**: flutter.disclaimer 无效(实测仍弹). noticeId键名=flutter.noticeId=191227(读它判断提醒是否弹).

## 各 patch 运行时实测结果 (颠覆了test2/test3的静态乐观结论)
1. **isNoAdLock总闸 0x7e8540:69000014** — 运行时对【可见广告】基本无效:
   首页banner仍在、喵喵饿了块仍在、点喵喵饿了仍弹故障窗。它只门控部分阅读期广告,覆盖面远小于报告宣称的"41处全清"。→ 放弃。
2. **SP showSplashAd=false** — 不阻止WebView开屏(loadDataWithBaseURL仍28次)。→ 无效。
3. **0x8863e8 开屏4点NOP** — 不阻止WebView开屏。loadDataWithBaseURL是AdMob/Pangle SDK行为,不走0x8863e8(Dart showDialog)。→ 对WebView开屏无效。
4. **开屏广告本身**: Pangle开屏日志=0(没跑). loadDataWithBaseURL是AdMob内部(gms/internal/ads). 开屏广告网络偶发,不稳定复现。
5. **0xba0bbc reward跳过(7f000014)** — 点喵喵饿了仍卡"正在加载"(和基线一样)。0xba0bbc跳的是ref19128"饿了喵~"提示文案,不是reward广告加载本身。→ 对喵喵饿了点击无效。

## 喵喵饿了根因 (logcat铁证)
- 点喵喵饿了 → Dart调 **ksad channel register** → MissingPluginException(因Kwad插件注册被注释) → reward流程中断 → 卡"正在加载"。
- 这证实关键教训#5/#6 + 三分支判断:去广告(注释插件)→channel调用全MissingPluginException。

## AdNoOpPluginV3 stub 部分生效
- V3集成进classes2.dex + 注册器add(V3) ✓ (apktool b通过)
- **效果: ksad MissingPluginException 消失!** channel调用被V3接管。
- **但**: 新错误 `NoSuchMethodError: []("channel_name") called on null` — V3对reward返回null, Dart期望Map(带channel_name等key),对null索引崩溃。
- 含义: reward链路打通一半(从无响应→有响应但格式错). 完整模拟需正确Map结构(test3报告§六预警的风险).

## 当前最佳基线 = TestC (backup/第七轮)
- 篡改窗(0x8e1dd0/8ef2b8) + 故障门控(0xbc1020) + 7点dialog-show NOP(故障弹窗) + 去广告smali(4插件注释)
- 主界面干净(无banner), 能看书, 故障弹窗延迟到~4min(第三源0x920d7c)

## ★★★ 决定性发现:故障弹窗根因 (logcat铁证, 2026-06-20)
主界面挂机 T+261s(~4.4分钟) 故障弹窗(ref27673"无法正常联网…广告无法显示")自动触发, 不依赖点击.
触发时logcat:
- MissingPluginException: method showSplashAd on channel flutter_pangle_ads
- MissingPluginException: method register on channel ksad
→ 根因: 去广告(注释插件注册)后, 广告定时器/重试调用 showSplashAd(Pangle)/register(ksad) →
  channel无响应 → MissingPluginException 累积 → 触发故障弹窗.
→ 这同时解释: ①为何挂机4min才弹(定时器周期) ②为何去广告后会弹 ③为何不依赖点击.
→ 解法: AdNoOpPlugin stub接管这些channel(不抛异常) = 从源头消灭故障弹窗+喵喵饿了.

## 首启弹窗SP键名 (实证)
- flutter.ensureDeclare = true  → 跳过"免责声明" (实测有效, 之前flutter.disclaimer是错的)
- flutter.noticeId = 191227      → 跳过"提醒"公告
- flutter.firstTime / remoteConfigSign / remoteConfig / ruleVersion 也是首启相关(远程配置/VIP绑定)

## V3 stub 改造 (解决null崩溃)
原V3 onMethodCall 对所有method success(null) → reward路径Dart对null索引崩(NoSuchMethodError []("channel_name")).
改造: success(空HashMap) → Dart对Map索引得null不崩. reward仍推EventChannel onRewardArrived/onAdClose.
注册块inject到registerWith(注意: 撤除残留catch_ad会导致重复label, 需清理).

## test3 VIP链路报告关键认知 (分析报告6_补VIP链路.md)
广告是【三套并行机制】(无单一isVip开关,三方一致):
1. 奖励特权计时: 看激励广告→得rewardTime秒免广告特权. 特权状态机0x8cf36c(已生效/已过期,17caller), onReward授权0x88aacc, getRewardTime getter 0x59d964.
2. 逐源noAd: 书源级广告抑制. noAdRegex 0x890c6c/0x920a60, 白名单0x839e80.
3. 捐赠VIP: ctor 0xa54178, 状态机0xb9fc84(→0xba0070/7c限制), 过期0x8ba3d0, 后端 ppcat.gentle.com/?i=/u=.

★反作弊 onReward Cheat Triggered!(ref11545): 加载点0x875ee8/0x89219c/0xaa62f4/0xaacee8.
  → 解释V3失败: stub让reward立即success→反作弊判"未真看广告就领奖=作弊"→不发喵粮+Dart对null索引崩溃.
广告引擎分发器 0x8758bc: 4SDK(AdNet/AdPgl/AdMob/AdKs)×4类型(Splash/Interstitial/Fullscreen/Reward)中央调度.

隐藏面板0xaa5848: 开发者测试后门(CrackTest/AdsTest/ShellTest/JsTest + isCrack/checkCrack/getCrackLog/shellTestCommand + 可运行任意JS). 非patch目标,但触发后可调试ad/VIP.

test3推荐最高杠杆方案(按置信度):
- 方案1 反作弊旁路(NOP 0x875ee8判定): 让即时reward不被判作弊→得喵粮+触发rewardTime秒ad-free. 置信中,需反汇编0x8758bc的Cheat分支精确字节.
- 方案2 强制0x8cf36c恒已生效: 阅读期广告全抑制. 置信低-中(多字段计数器非简单bool).
- 方案3 逐源noAd全局命中: 置信低(命中点未定位).
- 方案4 伪造捐赠VIP服务器响应: 待查(channel还是HTTP).

## V3 stub 完整集成步骤 (可复现)
1. 放 V3: git show origin/test3:analysis_workdir/smali_deliverable/AdNoOpPluginV3.smali > build/smali_classes2/com/gentle/ppcat/AdNoOpPluginV3.smali
2. 改造onMethodCall: const/4 v1,0x0(null) → new HashMap(空Map), 避免reward null崩溃. 见 analysis/AdNoOpPluginV3_map.smali
3. 注入注册块: PYTHONIOENCODING=utf-8 python analysis/inject_stub.py (token从注册器自抽取, 插入:try_start_ad前)
   - 注意:重复注入会残留catch_ad导致重复label编译错. 撤除用python re.sub删 try_start_ad..catch_ad块.
4. apktool.yml versionCode递增(强制覆盖libapp, 解决install-r陷阱)
5. apktool b → uber-apk-signer → install -r

## 装机后受控测试流程
- fresh_launch.sh: pm clear + 预写SP(ensureDeclare+noticeId) + 授权 + 启动直达主界面
- tohome.sh: 鲁棒过首启弹窗到主界面(install-r保留数据时用)
- obs.sh <tag>: dump UI + 提取广告/弹窗关键词

## ★★★ 第八轮突破:故障弹窗第三源定位 (2026-06-20)
三分支(test1/2/3)都没找到的故障弹窗第三源, 第八轮通过logcat+BL扫描定位:
- 真故障body builder = 0x920d7c (加载ref27673"无法正常联网…广告无法显示")
- 0x920d7c 的3个caller: 0x920d1c, 0xc4cc7c, 0xc4d298
- ★ 0xc4cc7c 所在函数 0xc4cb30 是故障弹窗编排器! 它有4个showDialog BL:
  0xc4cc2c(bl 0x47369c), 0xc4ccac(bl 0x47369c), 0xc4ce0c(bl 0x4670b0), 0xc4ce60(bl 0x472c98)
- 4个BL全部安全模式(前2xSTP push, 后add x15 pop + mov x0,x22 + ret), NOP安全.
- Patch: 0xc4cc2c/ccac/ce0c/ce60 = 1f2003d5 (P_FAULT3_NOP in patch_libapp.py)
- testC_fault3配置 = TestC + 第三源4点NOP. 待运行时验证是否压制故障弹窗.

## V3 stub 三次实验结论 (广告响应无法完美模拟)
- success(null) → reward路径NoSuchMethodError []("channel_name") on null
- success(空HashMap) → type 'HashMap' is not subtype of 'bool' (showSplashAd期望bool)
- success(Boolean.TRUE) → type 'bool' is not subtype of 'qsa?' (下游期望自定义对象)
→ 结论: 不同广告方法期望不同类型(bool/Map/自定义对象qsa), 无差别返回无法满足.
  完美模拟需逐方法返回正确类型(复杂, test1说Pangle是MethodChannel+EventChannel双通道).
→ 改用直接NOP故障弹窗showDialog编排器(第三源0xc4cb30)更彻底.

## ★ 故障弹窗最终机制定性 (2026-06-20, 多轮验证)
故障弹窗(ref27673) T+260s 必触发, 试过的压制方案全失败:
1. 第三源0xc4cb30 NOP(4BL) → 仍弹
2. 22个广告失败catch showDialog NOP(6函数,栈帧定位) → 仍弹
→ 结论: 故障弹窗【不走常规showDialog BL调用链】!
Dart栈帧证实: MissingPluginException是【Unhandled Exception(未捕获)】, 冒泡到Flutter全局错误处理.
→ 故障窗由 app全局onError/zone错误处理 弹出, 不经过0x47369c等showDialog.
→ 根治唯一路径: 消除MissingPluginException(让广告channel调用不抛异常) = V3 stub, 但需精确返回类型.

V3返回类型实验:
- null → NoSuchMethod []("channel_name") on null
- 空HashMap → type HashMap not bool (showSplashAd期望bool)
- Boolean.TRUE → type bool not 'qsa?' (下游期望自定义对象)
→ 不同方法期望不同类型, 需逐方法精确返回. test1建议initAd/showSplashAd返回TRUE但实测showSplashAd下游要qsa对象.

根本矛盾: 去广告(注释插件注册)必然MissingPlugin → 故障窗. V3假响应是唯一兼顾方案但返回类型难精确.
这是三分支6轮+第八轮都没根治的核心难点.
