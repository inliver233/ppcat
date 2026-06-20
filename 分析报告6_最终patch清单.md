# 最终 Patch 清单（test3 三轮交叉验证后定稿）

> 所有地址 vaddr==file offset。本清单只列**已验证安全**或**三方一致**的 patch。
> 风险等级：✅已验证安全 / ⭐高置信待运行时确认 / ⚠️实验性 / 🚫禁止。

---

## 一、libapp.so patch（Dart 侧）

### ✅ 已验证安全（第七轮已装机，保持）

| 地址 | 原始字节 | patch 字节 | 作用 |
|---|---|---|---|
| 0x8e1dd0 | fd79bfa9 fd030faa | e00316aa c0035fd6 | 篡改窗 return null |
| 0x8ef2b8 | fd79bfa9 fd030faa | e00316aa c0035fd6 | 篡改窗 return null |
| 0xbc1020 | a0120054 | 00020054 | 故障门控双保险 |
| 0xbc1058 | 46368c97 | 1f2003d5 | NOP 0xbc0f40 dialog-show BL① |
| 0xbc1134 | 46368c97 | 1f2003d5 | NOP 0xbc0f40 dialog-show BL② |
| 0xbc1234 | …… | 1f2003d5 | NOP 0xbc0f40 dialog-show BL③ |
| 0xbd60ac | …… | 1f2003d5 | NOP 0xbd5a24 dialog-show BL① |
| 0xbd6264 | …… | 1f2003d5 | NOP 0xbd5a24 dialog-show BL② |
| 0xbd6300 | …… | 1f2003d5 | NOP 0xbd5a24 dialog-show BL③ |
| 0xbd6130 | …… | 1f2003d5 | NOP 0xbd5a24 dialog-show BL④ |

### ⭐ 本轮新增：更新/远程配置弹窗 NOP（三方定位 + test3 安全模式复核）

BL 目标均为 0x47369c（dialog-show），前 2×STP push、后 add x15,#0x20 pop、再 mov x0,x22（返回null）—— **与 0xbc0f40 同型安全手法**。所在函数 0x8663bc/0x8671d0 加载 `remoteConfigSign`+`gitlab.com/ghostgzt/ppcat`（更新/远程配置链）。

| 地址 | 原始字节 | patch 字节 | 作用 |
|---|---|---|---|
| 0x8667a8 | bd33f097 | 1f2003d5 | NOP 更新/远程配置 dialog-show BL① |
| 0x8675bc | 3830f097 | 1f2003d5 | NOP 更新/远程配置 dialog-show BL② |

> 效果：止住"发现新版本"更新弹窗 + 远程配置校验提示窗（不弹）。返回 null，栈平衡，安全。

### 🚫 绝不可改（关键教训 + 三方一致）

| 地址 | 原因 |
|---|---|
| 0xbc0f40 / 0xbd5a24 / 0x7e1464 入口 | 改 return null 破坏开屏广告（运行时硬事实）|
| 0x7e1464 内部 dialog-show BL | NOP 破坏开屏"二次元涩兔合集"关闭（运行时硬事实）|
| 0xb9fc84 / 0xa54178 异步状态机入口 | 异步状态机，盲改风险极高 |
| 0x911788 共享门 csel/入口 | 18 caller + 多非bool出口，单点强改不干净 |

---

## 二、Java/smali 侧 patch

### ✅ AdNoOpPlugin（V1，安全基线，已交付）
- 新类 `smali_classes2/com/gentle/ppcat/AdNoOpPlugin.smali`
- 注册 4 channel（flutter_pangle_ads/ksad/google_mobile_ads/gdt_plugins）无操作 handler，全 method `success(null)`
- 注册器 `smali_classes2/สۥ۠ۦۢ/สۥ۟۟ۡ.smali` registerWith 开头插入 try/catch add
- **效果**：广告调用不再 MissingPluginException → 从源头消灭故障/每日喂喵弹窗的触发

### ⚠️ AdNoOpPluginV2（实验性升级，已交付，已编译验证）
- 在 V1 基础上：含 "Reward" 的 method → `success(null)` 后起 Thread sleep 30s → 向 Pangle channel `invokeMethod("onRewardArrived")`+`invokeMethod("onAdClose")`
- **目的**：模拟看完激励广告 → 绕过反作弊时间阈值（ref11545 "onReward Cheat Triggered!"）→ 让即时 reward 真正生效 → 得喵粮 + 触发 rewardTime 秒 ad-free
- **风险**：Thread/invokeMethod 较复杂；若 Dart 侧 reward 事件经 EventChannel(`flutter_pangle_ads_event`)而非 MethodChannel，则 invokeMethod 不达。**V1 仍是安全兜底**。
- 用 V2 替换 V1：把注册器里的 `AdNoOpPlugin` 改成 `AdNoOpPluginV2`（二选一，不要同时注册）

---

## 三、smali 既有（保持）

- `registerWith` 注释 4 广告插件注册（去广告）
- 导入书源 bug 内部类删诊断日志
- PmsHook 签名 spoof（过签名墙）

---

## 四、推荐装机组合（按目标）

**目标A：稳定可用、无故障/篡改/更新弹窗（最稳）**
→ libapp §一全部（含本轮 0x8667a8/0x8675bc）+ smali V1 stub + 既有 smali。

**目标B：A + 喵喵饿了能得喵粮（实验）**
→ 把 V1 换成 V2 stub（reward 模拟）。若 V2 无效（Dart 走 EventChannel），回退 V1，并考虑后续做 EventChannel StreamHandler stub。

**未做（高风险，三方一致不建议盲改）**：强制 isVip（无单一开关）、VIP expiresDate 比较点（需动态确认）、强改 0x911788 共享门。

---

## 五、验证清单（主控装机后用 `adb shell uiautomator dump` 检测）
- [ ] 篡改窗不弹
- [ ] 故障窗不弹（启动+阅读 65s+4min+）
- [ ] 更新窗不弹（0x8667a8/0x8675bc 生效后）
- [ ] 开屏广告正常播放几秒消失（未破坏）
- [ ] V1：广告相关无 MissingPluginException 日志
- [ ] V2（若装）：点喵喵饿了 ~30s 后得喵粮、块消失
