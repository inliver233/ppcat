# VIP / 广告链路深度分析（test3 补充报告）

> 续 `分析报告6.md`。本篇专攻用户提出的"VIP 链路打通 → 广告自然消失 + 功能解锁"假设。
> 方法：用 test3 已解穿的 ObjectPool（51140 entry 全映射，test1/test2 当时未具备）做 ref→slot→.text 全链路追踪。
> 中性措辞"代码恢复"。结论先行：**用户的假设方向是对的**，但本 app 没有单一 `isVip` 布尔开关，而是"奖励特权计时 + 逐源 noAd + 捐赠 VIP"三套并行机制。最高杠杆的"强制特权/奖励成功"路径已定位。

---

## 一、核心发现：三套广告门控机制并存

通过对象池把广告/VIP 相关字符串全部落到精确 .text 后，确认 ad-suppression 不是单一开关，而是：

### 1.1 奖励特权计时（reward privilege）—— 主要的"看广告免广告"机制
| 元素 | ref | slot off | .text | 说明 |
|---|---|---|---|---|
| `getRewardTime` | 8067 | 0x152b8 | func **0x59d964** | 奖励时长 getter（0 caller=虚方法/被 pool 调）|
| `rewardTime` | 7606 | 0x13d10 | 0x913bf8 / 0xa7fcd4 | SharedPreferences 读写 |
| 特权状态机 | — | — | func **0x8cf36c** | 读 adNum/lastTime/today/totalNum/totalTime，输出"已生效！剩余X秒"或"已过期！"，**17 个调用方**（含 VIP ctor 0xa541c8、每日喂喵区 0x7e813c/0x7e8618、奖励区 0x8a0448/0x8a05ec/0x86f154/0x89b004）|
| `onReward` 授权 | 6808 | 0x1c488 | func **0x88aacc** | 看完激励广告 → 授予 rewardTime 秒特权 |
| `earned reward:` | 32387 | 0x192f0 | 0x882128/0x88361c/0x88402c | 奖励到账日志 |

**含义**：看完一条激励广告 → 获得 `rewardTime` 秒"已生效"特权 → 在特权期内**广告被抑制**。这正是"喵喵饿了"块要触发的东西。`0x8cf36c` 的"已生效/已过期"就是 ad-free 状态判定。

### 1.2 逐源 noAd（per-book-source 广告抑制）—— 内置广告过滤
| 元素 | ref | slot off | .text | 说明 |
|---|---|---|---|---|
| `noAdAllowSourceList` | 5996 | 0xf1c8 | func **0x839e80**（caller 0x8391d4）| 免广告书源白名单 |
| `noAdRegex` | 6278 | 0x13ad0 | func **0x890c6c**（caller 0x87598c）/ **0x920a60** | noAd 正则配置 |

**含义**：app 对部分书源内置/支持自定义 noAd 规则，命中则该源不加载广告。这是逐源的广告开关。

### 1.3 捐赠 VIP（donation-bound VIP）
| 元素 | ref | .text | 说明 |
|---|---|---|---|
| VIP 内容页 ctor | — | **0xa54178** | VIP 页文案（含 8910"通过捐赠绑定设备获取"、13169"通过捐赠绑定账号获取"、13928"未获得特权将在0点重置浏览次数"、10073"已绑定账号"）|
| VIP 状态机 | — | **0xb9fc84**（→0xba0070/0xba007c 限制提示路径）| VIP/每日喂喵/账号绑定/更新混合状态机（**非纯 isVip**，test1 亦确认）|
| `expiresDate` | 7406 | func **0x8ba3d0** | VIP 过期日（SharedPreferences）|
| `expires` | 12056 | func **0x67994c**（读 expires/date/skipCount）| 过期+跳过计数 |
| `可以捐赠` | 11366 | func **0x8a0fd4** | 捐赠入口提示 |
| 服务器端点 | — | — | `ppcat.gentle.com/?i=`、`?u=`（app 后端，i/u 参数=邀请/用户）；`ghostgzt/ppcat` 的 `/version`、`/meta`、`/store`（gitlab/github 镜像，版本+元数据）|

### 1.4 奖励反作弊 ★（关键，与任务D 直接相关）
| 元素 | ref | .text | 说明 |
|---|---|---|---|
| **`onReward Cheat Triggered!`** | 11545 | 0x875ee8（func 0x8758bc 广告引擎分发器）/ 0x89219c（func 0x8920d0 奖励配置）/ 0xaa62f4 / 0xaacee8 | **奖励反作弊**：检测"未真正看广告就领奖励" |

**★ 这是任务D 的关键解释**：任务D 的 no-op stub 让广告 channel `success(null)` 立即返回 → Dart 侧奖励流程瞬间完成 → **反作弊判定"Cheat Triggered"→ 不发喵粮/特权**。这正是"喵喵饿了点击卡加载、得不到喵粮"的根因之一。

---

## 二、广告引擎分发器 0x8758bc（广告系统的"中央调度"）

func 0x8758bc（caller 0x875794）是**广告类型分发器**：大 switch 按 ad-type 常量分发到各 SDK handler：

```
AdNet_Splash/Interstitial/Fullscreen/Reward   (off 0x19000-0x19030)  ← 网络配置层
AdPgl_Splash/Interstitial/Fullscreen/Reward   (off 0x19008-0x19020)  ← Pangle(穿山甲)
AdMob_Splash/Interstitial/Fullscreen/Reward   (off 0x19028-0x19040)  ← AdMob(Google)
AdKs_Splash/Interstitial/Fullscreen/Reward    (off 0x19050-0x19068)  ← KSAD(快手)
"No Type!"(28932)  /  "onReward Cheat Triggered!"(11545)  分支尾部
```

分发模式：`BL 0xc833ac`(类型比较) → `tbnz w0,#4, next_case`（不匹配走下一 case）→ 匹配则 `BL <SDK-handler>`。

**含义**：0x8758bc 是"按配置/策略决定加载哪种广告"的核心。要"全局禁广告"，这里是最上游的候选——但它是分发器（决定用哪个 SDK），不是"是否显示"的总闸。

---

## 三、最高杠杆的"强制特权/奖励成功"路径（任务D 协同）

基于上述链路，用户"VIP打通→广告消失"假设的**最可工程化**实现（按置信度）：

### ★ 方案 1：奖励反作弊旁路（与任务D 协同，最高价值）
- **目标**：让任务D 的即时 reward 不被 "onReward Cheat Triggered!"(ref 11545) 判作弊 → 喵喵饿了点击立即得喵粮+特权 → 块消失 + 触发 rewardTime 秒 ad-free。
- **机制**：反作弊在 func 0x8758bc（0x875ee8 区）+ 0x8920d0（0x89219c）。需定位"作弊判定"的比较点（判定标准可能是：广告展示时长 < 阈值、或 onReward 与 load 间隔过短）。
- **下一步**（主控动态/进一步静态）：反汇编 0x8758bc 的 Cheat 分支，找到判定比较，NOP 该判定使其恒"非作弊"。
- **置信度**：中。地址已定位（0x875ee8/0x89219c），但精确判定字节需进一步反汇编 + 运行时确认（不能盲改）。

### 方案 2：奖励特权计时强制常开
- **目标**：让特权状态机 0x8cf36c 恒报"已生效"→ 阅读期广告全抑制。
- **机制**：0x8cf36c 返回状态对象（已生效/已过期/leaveTime），17 调用方据此决定是否显示广告。
- **置信度**：低-中。0x8cf36c 是多字段计数器，返回非简单 bool；强制其"已生效"需精确理解返回约定，风险高。建议主控动态 dump 确认其返回如何 gate 广告后再动。

### 方案 3：逐源 noAd 全局命中
- **目标**：让 noAdRegex(0x890c6c) / noAdAllowSourceList(0x839e80) 对所有源命中 → 全局无广告。
- **机制**：0x890c6c 是 noAd **配置管理**（读 noAdRegex + showSplashAd + delete），0x839e80 是白名单。命中判定在别处。
- **置信度**：低。命中点未定位到。

### 方案 4：捐赠 VIP 服务器响应伪造（任务D 风格）
- **目标**：app 经 `ppcat.gentle.com/?i=/u=` 校验 VIP。若 VIP 校验走某 channel/HTTP，可仿任务D 伪造"已是 VIP"响应。
- **置信度**：待查（需确认 VIP 校验是 channel 还是 HTTP；若是 HTTP，伪造需网络层）。

---

## 四、诚实结论

1. **用户的方向正确**：打通 VIP/特权链路确实能让广告消失（奖励特权期内广告被抑制，1.1 已证实），且解锁 VIP 功能（13928"未获得特权将在0点重置浏览次数"= 浏览次数限制被解除）。
2. **但本 app 没有单一 `isVip` 开关**：是三套并行机制（奖励特权计时 + 逐源 noAd + 捐赠 VIP）。test1/test2 也独立得出此结论（"0xb9fc84 是混合状态机，非单一 isVip"）。
3. **最高杠杆且与已交付任务D 协同的是"奖励反作弊旁路"**（ref 11545 "onReward Cheat Triggered!"）：它直接解释了任务D 下"喵喵饿了卡加载/不得喵粮"的根因，旁路它能让任务D 的即时 reward 真正生效 → 得喵粮 + 触发 rewardTime 秒 ad-free。
4. **不建议盲改异步状态机入口**（0xb9fc84/0xa54178）—— 前几轮教训（0xbc0f40 等）证明改状态机入口风险极高。

## 五、已精确定位的 VIP/广告函数清单（对象池映射，test3 独有）

| 函数 | 角色 | 关键字符串 |
|---|---|---|
| 0x8758bc | 广告引擎分发器（4SDK × 4类型）| AdNet/AdPgl/AdMob/AdKs Splash/Interstitial/Fullscreen/Reward + onReward Cheat Triggered! |
| 0x8cf36c | 奖励特权状态机（已生效/已过期）| adNum/lastTime/today/totalNum/totalTime/leaveTime/已生效/已过期/秒 |
| 0x59d964 | getRewardTime getter | getRewardTime |
| 0x88aacc | onReward 授权 | onReward |
| 0x8794b0 | 奖励名/数量 | rewardName/rewardAmount |
| 0x8859e4 | 奖励类型/校验 | rewardType/rewardVerify |
| 0x882128/0x88361c/0x88402c | 奖励到账 | earned reward: |
| 0x891930 | 展示激励广告失败 | 展示RewardVideo广告失败 |
| 0x890c6c / 0x920a60 | noAd 正则配置 | noAdRegex |
| 0x839e80 | noAd 白名单 | noAdAllowSourceList |
| 0xa54178 | VIP 内容页 ctor | 通过捐赠绑定设备/账号获取/未获得特权重置浏览次数/已绑定账号 |
| 0xb9fc84 | VIP 混合状态机 | （限制提示 0xba0070/0xba007c）|
| 0x8ba3d0 | VIP 过期日 | expiresDate |
| 0x67994c | 过期+跳过计数 | expires/date/skipCount |
| 0x8a0fd4 | 捐赠入口提示 | 可以捐赠 |

## 六、交付脚本
- `analysis_workdir/vip_deep.py` / `vip_funcs.py` / `vip_getters.py`：VIP 字符串→slot→.text 全映射
- `analysis_workdir/reward_chain.py`：奖励授权→特权→计数链
- `analysis_workdir/ad_gate.py` / `disasm_8758bc.py`：广告引擎 + ad-gate 分析
- `analysis_workdir/anticheat.py`：反作弊"onReward Cheat Triggered!"定位（4 处加载点）

> 综合：**任务D（no-op stub，已交付）+ 反作弊旁路（本篇方案1）** 是"强制奖励成功 → 得喵粮 + ad-free 特权触发"最可工程化的组合，且不依赖难以定位的单一 isVip 开关。反作弊精确 patch 字节建议主控进一步反汇编 0x8758bc 的 Cheat 分支 + 运行时确认后再动。
