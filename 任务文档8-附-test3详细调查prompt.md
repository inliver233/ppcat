# 致 test3:喵喵块 + 开屏overlay + 首页banner 联合深挖(第九轮交接)

> 这是给 test3 分支(ARM64原生 + 全量对象池反序列化 + xref DB + scan_slot)的详细调研任务.
> test3 是本任务最关键分支——你的对象池+xref 能力是突破 pool 间接闭包墙的唯一希望.
> 完整背景: backup分支 backup/第八轮-去广告去首启弹窗/ + 任务文档7/8. 中性措辞"代码恢复".
> 主控负责patch-and-test(设备LDPlayer9, frida不可用, 只能静态+装机验证).

═════════════════════════════════════════════
〇、先读什么
═════════════════════════════════════════════
1. git fetch --all
2. git show origin/backup:backup/第八轮-去广告去首启弹窗/ROUND8_FACTS.md  (主控全部运行时硬事实)
3. git show origin/backup:backup/第八轮-去广告去首启弹窗/说明.md
4. 任务文档7-附-三方调研提示词.md + 任务文档8-喵喵块深挖.md (本文件延续)

═════════════════════════════════════════════
一、重大进展:test3上轮突破已被主控验证(故障弹窗根治)
═════════════════════════════════════════════
test3上轮的 0x920d7c 截断(0x920d90:692c0054→29000014)主控运行时验证成功:
挂机T+327s(超之前必触发T+260s)全程无故障弹窗, app稳定, 主界面干净.
MissingPluginException仍在但故障显示路径(0x920d7c)截断故不弹窗.
→ 新基线 = TestC + 0x920d90. 故障弹窗已根治. 这是三方协作的重大胜利.

═════════════════════════════════════════════
二、★★★ 任务1:喵喵饿了悬浮块【视觉根除】(最高优先)
═════════════════════════════════════════════

### 用户诉求
阅读页"喵喵饿了"悬浮块挡视线, 用户要求【看不到】(不只是不可点击). 能根除最好.

### 喵喵块运行时特征(主控a11y dump, 确定性)
节点树(深度优先):
- #9  View  bounds=[0,0][1080,1920]  content-desc="8 9 10 11 12 13"(翻页缩略图=阅读内容层)
- #10 ImageView bounds=[0,0][1080,1551]  (全屏, 是阅读页背景层, ★非喵喵块图)
- #11 ★Button bounds=[720,1260][1080,1392] content-desc="喵喵饿了" clickable=true (右下角360x132小块=喵喵块本体)
均为com.gentle.ppcat包(标准Flutter widget树). 即:喵喵块=右下角小Button, 无独立大图, 视觉是文字/小图标Button.

### ★ 主控已排除(勿重复, 节省你时间)
1. ref28525"喵喵饿了"全局仅2处LDR加载: 0xae36f8(func 0xae30e0内) + 0xa55cbc(func 0xa54178内). (scan_slot确认)
2. 改0xae30e0(强制PATH_A @0xae312c b.ne→NOP + PATH_A return null @0xae32d4 mov x0,x1→mov x0,x22) → 块【完全没变】.
3. 改0xa54178入口return null(@0xa5418c b.ls→mov x0,x22 + @0xa54190→b 0xa567d8尾声) → app没崩但块【还在】. (0xa54178=VIP/喵喵页整页build 0xa54178-0xa56828 2476条指令, 加载42个VIP区slot, 非阅读页)
4. img/kamm.jpg仅0xa54178加载; img/skmm.png在0x7e02d0/0xbc2278/0xc2ab28/0xc2b344/0xc2b4b0; img/yhmm.png. 替换skmm/yhmm为透明PNG → 喵喵块那个全屏ImageView(#10)仍[0,0][1080,1551] → 喵喵块不用skmm/yhmm/kamm图(全屏#10是阅读背景).
5. 对象池"喵喵饿了"只ref28525一个(无多ref指向同字面).
6. 0xae30e0/0xa54178/skmm加载函数 callers均=[] (pool间接BLR).

### 核心矛盾(请test3突破)
喵喵块Button的content-desc"喵喵饿了"来自Flutter Semantics(label). 但ref28525的两个LDR加载点(0xae30e0/0xa54178)都不是块build → 块的Semantics label经【构造参数传递】(Semantics widget构造时label是上层传入的字符串对象), 非build函数内LDR ref28525.
→ 这是pool间接闭包链. blutter在本定制VM失败(cid84=String, class table异常).

### ★ 求test3用你的对象池+xref突破(只有你能做)
**方向A(最高优先):对象池Code簇逆向找阅读页reader build**
test3对象池已全反序列化(51140 entry, pool_deserialized.json). 虽blutter失败, 但你可手动:
- pool里kTaggedObject entry若指向Code对象(含entry_point=函数地址), 反向建表: 哪个pool entry的entry_point=0xae30e0或喵喵块真实build → 那个pool entry被谁LDR → 调用者.
- scan_slot扩展版: 扫描pool里所有含.text函数地址的entry, 建"函数地址→pool entry→引用函数"反查表.
- 找【阅读页reader主build】: 加载阅读特征串(章节/第01话/WIFI/页码/翻页缩略图"8 9 10...")的函数. reader build内把喵喵块layer加入Stack/Overlay的BLR x30(间接调用)指向喵喵块闭包.
- 关键: 阅读页喵喵块的build地址 ≠ 0xae30e0/0xa54178(这俩主控已排除). 找第三个.

**方向B:Semantics构造点扫描**
- 喵喵块Button的Semantics label="喵喵饿了"来自Semantics(label:...)构造. 扫描所有构造Semantics widget的点(label字段写入str x?,[?,#off]), 哪个的label是ref28525对应的字符串对象(但经参数传, 不是LDR).
- 喵喵块可点击→GestureDetector/onPressed闭包. 扫描闭包构造.
- 找阅读页范围内调用这些构造的build.

**方向C(你上轮scan_slot的进化):slot反向+闭包**
- 你上轮用scan_slot(scan_slot.py)锁定故障body唯一源. 同法: 喵喵块Button的onClick回调地址存pool(闭包). 扫描"喵喵饿了"周边的closure entry.
- 扩展scan_slot: 不只扫LDR pool加载, 还扫pool里kTaggedObject指向Code的entry, 追"闭包→注册点→调用者".

### 喵喵块已知相关函数(参考)
- skmm.png加载: 0x7e02d0(173条)/0xbc2278(99条,在故障编排器区0xbc0f40-0xbd5a24)/0xc2ab28/0xc2b344/0xc2b4b0. 均callers=[]. 0xbc2278值得深挖(故障区邻近).
- 0xa54178=VIP整页build. 0xae30e0=喵喵相关build(2路径PATH_A cmp w0,#0x14 / PATH_B). 喵喵块文字ref28525在0xae36f8(PATH_B内).
- img asset全表: status.jpg(ref6939) / yhmm.png(ref15351) / kamm.jpg(ref22939) / icon.png(ref23599) / skmm.png(ref29409).

═════════════════════════════════════════════
三、★★ 任务2:开屏overlay广告 + 首页banner(用户要求一并去掉)
═════════════════════════════════════════════

### 用户诉求
以下都算"开屏广告/弹窗", 要去掉:
1. 首页overlay「剩余X喵 / 立即获取免广告特权」(VIP/特权推广, install或重启后出现)
2. 首页banner「二次元涩兔合集XXXXX期下载」+「关闭喵」按钮(推广广告)
3. 冷启动偶发的WebView开屏(loadDataWithBaseURL, AdMob SDK行为, 网络偶发)

### 主控已查
- 开屏WebView是AdMob SDK(gms/internal/ads)的loadDataWithBaseURL, 不走Pangle/GDT/AdMob/Ksad的Flutter插件注册(已注释). SP showSplashAd=false无效(已运行时证伪). 0x8863e8开屏NOP无效.
- 首页overlay文案「立即获取免广告特权」「剩余X喵」「二次元涩兔合集」在unflutter_strings/SHARED_STRING_INDEX【没找到】→ 动态拼接或图片或远程配置. 「24小时内累计浏览」ref2878、「已生效！剩余」在0x8cf36c(特权状态机).
- 这些overlay/banner可能是【同一个全局悬浮层】在不同页面的显示(和喵喵块同源?). 若任务1定位到全局悬浮widget build, 可能同时解决.

### 求test3
- 定位首页overlay「立即获取免广告特权」的widget build(文案虽动态, 但"立即获取免广告特权"是固定推广文案, 应在pool. 用更宽的grep: "免广告"/"特权"/"立即获取"). 找其build, 给让它不显示的patch.
- 首页banner「二次元涩兔合集」可能是远程推送(非本地文案), 若是则难静态定位→找banner容器widget让它不渲染.
- 判断这些overlay/banner和喵喵块是否同属一个全局悬浮widget(若是, 一次根除).

═════════════════════════════════════════════
四、交付要求
═════════════════════════════════════════════
test3在分析报告8.md(或对应轮次)给出:
1. 【喵喵块】阅读页喵喵块Button的真正build函数地址 或 把它加入阅读页overlay的调用点. 让块不显示的patch(地址+原字节+patch字节+栈平衡安全+不崩widget树).
2. 【开屏overlay/banner】其build + 不显示patch. 是否和喵喵块同源.
3. 区分静态确定 vs 需主控patch-and-test.
4. 交叉验证test1/test2(他们也在调研, test1有Ghidra).
5. 用你的scan_slot/对象池工具给出字节级证据.

主控汇总后立即patch-and-test装机验证. 故障弹窗已根治(你的0x920d7c突破), 这是最后的主要残留(喵喵块视觉 + 开屏overlay). 拜托test3再立一功.

═════════════════════════════════════════════
五、主控环境约束(供你判断patch可行性)
═════════════════════════════════════════════
- 设备LDPlayer9 x86_64 Android9, frida不可用, 只能静态+patch-and-test.
- 观察靠adb shell uiautomator dump的content-desc(含Flutter文字+坐标).
- install -r同versionCode不换libapp, 主控靠versionCode递增.
- 装机后pm clear清书数据(测阅读页需install -r保留数据).
- 栈帧virt(libapp file offset)=logcat Dart栈帧地址去tag对齐. _kDartIsolateSnapshotInstructions@0x464ce0.

一句话: 故障弹窗已被你的0x920d7c根治. 现请test3用对象池+xref+scan_slot进化版, 突破喵喵块(右下小Button)的pool间接闭包定位, 顺带搞定开屏overlay/banner. 这是去纯净版最后的堡垒. 谢谢.
