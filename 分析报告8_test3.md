# test3 第九轮深挖报告：喵喵块 + 开屏overlay + 首页banner

## 摘要
- 故障弹窗已由 test3 上轮 0x920d7c 截断根治（主控验证：T+327s 无弹窗）
- 本报告聚焦三大残留 UI 的定位与 patch 方案
- **核心突破**：定位到首页 build 函数链 0xbd2e1c→0xbd3540（加载喵喵块 class 区域 slot）
- **喵喵块能力边界**：pool 间接 BLR 墙阻挡了精确父级定位（blutter cid84 失败+callers=0），但通过多维度交叉找到了最可能的入口

---

## §0 基线确认

| 项目 | 状态 |
|------|------|
| 故障弹窗 (ref27673) | ✅ 根治 (0x920d90: 692c0054→29000014) |
| 故障弹窗第三源 (0xc4cb30) | ✅ NOP 安全 |
| 喵喵饿了常驻块 | ❌ 仍显示（0xae30e0/0xa54178 patch 无效） |
| 首页 overlay「剩余X喵/立即获取免广告特权」 | ❌ 待处理 |
| 首页 banner「二次元涩兔合集」 | ❌ 待处理 |
| 冷启动 WebView 开屏 | ⚠️ 网络偶发，走 AdMob SDK 非 Flutter |

---

## §1 ★★★ 任务1：喵喵饿了悬浮块（最高优先）

### 1.1 已知事实（主控运行时验证）

```
a11y 节点树:
  #9  View  bounds=[0,0][1080,1920]  content-desc="8 9 10 11 12 13"
  #10 ImageView bounds=[0,0][1080,1551]  (阅读背景，非喵喵块)
  #11 ★Button bounds=[720,1260][1080,1392] content-desc="喵喵饿了" clickable=true
```

**已排除的路径（主控 patch-and-test 证实无效）：**
1. 0xae30e0 b.ne→NOP + PATH_A return-null → 块完全没变
2. 0xa54178 entry return-null → app 没崩但块还在
3. 替换 skmm/yhmm 为透明 PNG → ImageView#10 仍全屏
4. force 0x8cf36c→TRUE → 对喵喵块显示无效

### 1.2 函数架构清查（本轮深化）

#### 1.2.1 喵喵块 class 的 pool 区域（0x5980-0x59d0）

该区域含 ~80 个 pool entries，被 17 个函数加载。核心布局：

```
slot 0x59a5: ref=8910   "通过捐赠绑定设备获取"
slot 0x59ab: ref=13169  "功能，通过捐赠绑定账号获取"
slot 0x59bb: ref=21707  "每日喂喵"
slot 0x59bc: ref=28525  "喵喵饿了"     ← 唯一"喵喵饿了" ref（全局仅1个）
slot 0x59be: ref=6939   status.jpg
slot 0x59ba: ref=22939  kamm.jpg
```

**主要加载者：**
| 函数 | 加载 slot 数 | 角色 |
|------|-------------|------|
| 0xa54178 | 30 | VIP/喵喵页 constructor（训练喵喵/让喵喵更智能/分享喵喵）|
| 0xb9fc84 | 7 | VIP 状态管理器（喵喵喵~/饿了喵~/检测喵喵编号）|
| 0xae30e0 | 1 | 喵喵饿了 widget build（仅 slot 0x59bc = ref 28525）|
| 0xae71bc | 3 | 每日喂喵 widget build（仅 slot 0x59bb = ref 21707）|
| 0xbc5dc8 | 1 | Reward prompt（slot 0x59bd, 饿了喵~ 等） |
| **0xbd3540** | **1** | **首页 build（slot 0x59a4, 立即获取+AdMob banner）** |
| 0xb68308 | 1 | 加载 slot 0x59bd, bool=True, 角色未明 |

#### 1.2.2 两者分属不同页面

- **0xa54178** = VIP/喵喵页（点击首页的喵图标进入），含训练/分享/绑定等功能
- **0xae30e0** = 喵喵饿了 widget builder（W0==0x14→喵喵饿了，W0!=0x14→每日喂喵）
- **0xae71bc** = 每日喂喵 widget builder（独立的 widget 构建函数）
- **0xbc5dc8** = Reward prompt（onTap handler，点击喵喵块→显示"是否看推荐信息获取喵粮喂喵？"）

**关键发现：0xbc5dc8 是阅读页喵喵块的 onTap handler**
- 主控验证：patch 0xbc5dd0-8 reward-prompt null-return → 喵喵块仍可见但不可点击
- 这意味着阅读页喵喵块的 onTap/onPressed 闭包 → pool 间接 BLR → 0xbc5dc8
- **构建该 Button 并将 onTap 指向 0xbc5dc8 的函数 ≠ 0xae30e0**

### 1.3 阅读页 build 函数链（新发现）

通过字符串搜索（"加载中...", "翻页", "ComicReader", "NovelReader", "webBgColor", "fontSize" 等阅读特征）定位到以下函数：

```
阅读页架构:
  0xb3abd0 (bool=True, 27 callees)
  ├── "加载中...", "webBgColor", "fontSize", "completer:", "fVb", "QMb"
  ├── 调用 0xb3b064 (ComicReader setup)
  ├── 调用 0x7e02c0 (image loader)
  ├── 调用 0xf83da8 (alloc) ← Widget 构造标志
  └── callers=0 (pool 间接 BLR)

  0xb3b064 (bool=False, 18 callees)
  ├── "ComicReader", "WebReader", "major", "img@src", "音频"
  ├── 调用 0xb3c368 (NovelReader)
  └── 被 0xb3abd0 调用

  0xbc82d0 (bool=True, 45 callees, 1 CALLER!)
  ├── "加载中...", "author", "webBgColor", "QMb", "站点名称", "站点分组"
  ├── "我的仓库", "订阅仓库", "解锁", "混合"
  ├── 调用 0xf83da8 (alloc) ← Widget 构造
  └── caller: 0xbc7f9c → caller: 0xbc71ec
  → 0xbc71ec (callers=0) = 书源/书详情页的入口

  0xb3ff04 (bool=True, 加载 slot 0x59be=status.jpg)
  ├── "useWebView", "ScrollListView", "nightMask", "topPanel", "fontSize"
  ├── "data", "webUrl", "group", "total"
  └── callers=0
```

### 1.4 首页 build 函数链（新发现，★关键）

```
首页架构:
  0xbd2e1c (bool=True, 14 callees, "Home" + "fontSize")
  ├── 调用 0xbd3084 (商店版/极速版/站点名称)
  ├── 调用 0xbd3540 (立即获取 + admobBannerFurtureView)
  └── callers=0 (pool 间接 BLR)

  0xbd3540 (bool=True, 53 callees, 166 pool loads)
  ├── "立即获取" ← ★首页 overlay 文案
  ├── "admobBannerFurtureView" ← ★AdMob banner 组件
  ├── "商店版", "教程", "站点类型", "站点名称", "站点分组"
  ├── "全能的自定义检索阅读工具"
  ├── 加载 slot 0x59a4 (ref=121017, ★在喵喵块 class 区域内)
  └── caller: 0xbd2e1c
```

**★ 核心发现：0xbd3540 同时加载"立即获取"字符串 AND 喵喵块 class 区域的 slot 0x59a4**

这意味着首页 build 0xbd3540 构建的 widget 树中既包含"立即获取免广告特权"overlay，也包含与喵喵块 class 相关的组件（可能是首页上的喵喵状态指示器或悬浮入口）。

### 1.5 Pool 间接 BLR 墙（能力边界）

**问题：** 0xae30e0/b3abd0/bd2e1c 等 widget build 函数全部 callers=0。
它们通过 pool 间接 BLR 被调用（函数地址存在 pool entry → 某处 LDR pool slot → BLR）。

**尝试过的突破方法：**
1. ❌ 快照 Code 对象解析 → 自定义 Dart 2.19 VM 压缩指针快照格式，函数地址非原生存储
2. ❌ 直接 caller 追踪 → 所有 widget 函数 callers=0
3. ✅ 字符串交叉 → 找到阅读页/首页函数链（但无法确定谁加入喵喵块到 widget 树）
4. ✅ pool slot 交叉 → 找到 0xbd3540 加载喵喵块 class 区域的 slot

**无法突破的根本原因：** blutter cid84=String 失败，class table 异常，无法解析快照中的 Code→Function→Class 关系链。

### 1.6 喵喵块视觉根除—务实 patch 方案

鉴于无法精确定位「谁把喵喵块加入阅读页 Stack」，以下方案从不同截断点切入：

#### 方案 M1 (推荐优先测试)：截断 0xbc5dc8 reward prompt 的全部 callee widget 构建

```
地址: 0xbc5dc8
策略: entry+8 处插入 return-null (MOV X0,X22; RET)
原字节: efa100d1 a00b40f9 (STP/SUB prologue continuation)
patch:  e00316aa c0035fd6 (MOV X0,X22; RET)  仅 8 字节

效果: 点击喵喵块→reward prompt 不弹（主控已验证不可点击）
      但喵喵块仍可见（因为 build 函数未被触及）
风险: 低（仅影响 reward prompt 弹窗，不影响其他 UI）
```

#### 方案 M2 (根除尝试)：截断 0xbd3540 中喵喵块相关子组件

```
地址: 0xbd3540 (立即获取 + admobBannerFurtureView builder, 166 pool loads)
策略: 需要反汇编精确定位构建 喵喵块/overlay/banner 的分支
注意: 0xbd3540 构建大量 UI（首页整体），不能简单 return-null
建议: 先 disasm 0xbd3540，找 slot 0x59a4 的 LDR 点→追溯其使用→NOP 该分支
状态: 需 capstone 级反汇编精确定位
风险: 中（可能影响首页其他 UI）
```

#### 方案 M3 (最保守)：NOP 喵喵块 onTap → 视觉保留但无功能

```
地址: 0xbc5dd0 (reward prompt 的 return-null)
原字节: efa100d1 a00b40f9
patch:  e00316aa c0035fd6
效果: 喵喵块可见但点击无效（test3 已验证）
```

#### 方案 M4 (实验性)：NOP 全局悬浮层 DraggableFloatWidget

```
地址: 0xa02e14 (DraggableFloatWidgetState)
callers: 0xa01288, 0xc3d5b0
策略: 需要确认喵喵块是否使用该可拖浮窗作为容器
     若确认，在 caller 处 NOP 调用即可
状态: 需主控运行时确认（a11y 检查喵喵块是否可拖动）
```

### 1.7 喵喵块—待主控 patch-and-test 优先级

| 优先级 | 方案 | 风险 | 预期效果 |
|--------|------|------|---------|
| **P0** | M1: 0xbc5dc8 return-null（已证不可点击） | 低 | 消除点击行为 |
| **P1** | M2: 0xbd3540 精确定位+NOP | 中 | 可能根除喵喵块+overlay+banner |
| **P2** | M3: 0xbc5dd0 return-null | 低 | 仅消除点击（已知） |
| **P3** | M4: DraggableFloatWidget NOP | 中 | 若喵喵块是浮窗子组件→全部消失 |

---

## §2 ★★ 任务2：开屏 overlay + 首页 banner

### 2.1 首页 overlay「立即获取免广告特权」

**文案来源确认：**
- "立即获取" → 0xbd3540 (唯一加载点)
- "免广告特权" → **快照中不存在**（动态拼接或远程配置）
- "已生效！剩余" → 0x8cf36c (特权计时器状态机)
- "剩余X喵" → 0x8cf36c 动态拼接数字

**overlay build 函数链：**
```
0x8cf36c (特权状态机, 16 callers)
  ├── 被 0xbca240 调用 (adNum:)
  ├── 被 0x7e8534 调用 (isNoAdLock, 41 callers!)
  ├── 被 0xb3ff04 调用 (阅读页函数)
  ├── 被 0xa54178 调用 (VIP 页)
  └── 被 0xb9fc84 调用 (VIP 状态)

0xbd3540 (立即获取 builder, caller=0xbd2e1c)
  ├── "立即获取" ← overlay 按钮文案
  ├── "admobBannerFurtureView" ← AdMob banner
  └── 加载 slot 0x59a4 (喵喵块 class 区域)
```

**关键判断：** 首页 overlay 和喵喵块可能共享 0xbd3540 或其子组件作为 builder。
0xbd3540 加载喵喵块 class 区域 slot（0x59a4），暗示它构建包含喵喵块相关 widget 的页面。
首页上的"立即获取免广告特权"overlay 与 喵喵块可能是同一个全局悬浮层的不同状态。

### 2.2 首页 banner「二次元涩兔合集」

**该文案在快照中不存在** → 远程推送内容（非本地硬编码）。
但 banner 容器由本地构建。

**banner 容器相关函数：**
```
0x87f250 (1 caller): onBannerWillPresentScreen / onBannerDidDismissScreen / onBannerImpression
0x87d030 (1 caller): loadAdManagerBannerAd
0x923744 (0 callers): flutter_pangle_ads_banner (Pangle banner channel)
0xa20b3c (1 caller): admobBannerFurtureView (AdMob banner 组件)
0xbd3540 (1 caller): "admobBannerFurtureView" ← 首页使用此组件
```

**banner 的 AdMob SDK 层面：**
- loadDataWithBaseURL 是 AdMob SDK 内部行为，不走 Flutter channel
- SP showSplashAd=false 无效（主控已验证）
- 0x8863e8 开屏 NOP 无效（不经过 Dart showDialog）

### 2.3 开屏 overlay/banner patch 方案

#### 方案 O1 (推荐)：截断 0xbd2e1c→0xbd3540 调用

```
地址: 0xbd2e1c (Home page build) 内 BL 0xbd3540 处
策略: 找到 BL 0xbd3540 的精确地址 → NOP (1f2003d5)
效果: 首页不再构建"立即获取" overlay 和 AdMob banner
风险: 中（0xbd3540 也构建其他首页 UI，需确认影响范围）
状态: 需反汇编 0xbd2e1c 找到 BL 0xbd3540 的精确偏移
```

#### 方案 O2：0xbd3540 内部条件 NOP

```
地址: 0xbd3540 内构建 overlay/banner 的分支
策略: disasm 0xbd3540 → 定位"立即获取" string 加载点 → 追溯其 widget 构造路径 → NOP 该分支
风险: 低（只影响 overlay/banner，其他首页 UI 保留）
状态: 需 capstone 级反汇编
```

#### 方案 O3 (WebView 开屏)：放弃静态 patch

```
WebView 开屏由 AdMob SDK 内部 loadDataWithBaseURL 触发，非 Flutter 层。
网络偶发，不建议投入静态分析。可尝试运行时方案（如 hosts 屏蔽或 Xposed 模块）。
```

#### 方案 O4：特权的"已生效！剩余"截断

```
地址: 0x8cf36c (特权状态机, 16 callers)
策略: 将其改为恒返回"已过期"→ overlay 不显示特权推广
风险: 可能影响特权计时器的其他功能（如阅读页免广告计时）
注意: test3 已验证 force TRUE→对喵喵块显示无效，但 force FALSE 可能有用
状态: 需实验验证
```

### 2.4 开屏/banner—与喵喵块同源判断

**证据支持「同源」（同一全局悬浮层）：**
1. 0xbd3540 同时加载"立即获取"和喵喵块 class 区域 slot (0x59a4)
2. 0xbd3540 同时引用"admobBannerFurtureView"和 0x59a4（喵喵块 class）
3. 首页 overlay 文案和喵喵块共享相同的 obfuscated Arabic 字符串前缀 (QMb/gXc/iXc)

**如果同源确认：** 方案 M2（截断 0xbd3540 相关分支）可能一次解决所有三个问题（喵喵块+overlay+banner）。

---

## §3 交叉验证 test1/test2

### 3.1 test1 (Ghidra) 可贡献
- 0xbd3540 的 Ghidra 反编译（166 pool loads + 53 callees，静态分析耗时）
- 0xbd2e1c→0xbd3540 的精确 BL 地址
- 0xae30e0 所在 class 的完整 vtable（Ghidra 可恢复 class 结构）

### 3.2 test2 (前期分析)
- test2 的广告调度表（4 SDK × 4 类型）与 banner 回调函数对应
- test2 的 showDialog BL 安全 NOP 模式已验证可复用
- test2 的 MissingPluginException ctor 分析补充了故障弹窗机制

### 3.3 三方协作建议
- test1: Ghidra 反编译 0xbd3540 + 0xbd2e1c，找 BL 精确地址
- test2: 验证 ad banner 函数（0x87f250/0x87d030）的 showDialog BL 是否可安全 NOP
- test3 (本方): 继续 scan_slot + pool 交叉，若 test1 提供 BL 地址则验证字节

---

## §4 字节级证据汇总

### 4.1 函数入口验证（全部通过）

| 函数 | 地址 | prologue | 角色 |
|------|------|---------|------|
| MeowMeow build | 0xae30e0 | fd79bfa9fd030faa | 喵喵饿了 widget |
| VIP page ctor | 0xa54178 | fd79bfa9fd030faa | VIP/喵喵页 |
| Reward prompt | 0xbc5dc8 | fd79bfa9fd030faa | onTap handler |
| **Home page** | **0xbd2e1c** | **fd79bfa9fd030faa** | **首页 build** |
| **立即获取** | **0xbd3540** | **fd79bfa9fd030faa** | **overlay+banner build** |
| 商店版/极速版 | 0xbd3084 | fd79bfa9fd030faa | 首页子组件 |
| Reader loader | 0xb3abd0 | fd79bfa9fd030faa | 阅读页加载 |
| Book detail | 0xbc82d0 | fd79bfa9fd030faa | 书源/详情页 |
| MeowMeow daily | 0x846b1c | fd79bfa9fd030faa | 每日喂喵(Scaffold) |
| Privilege timer | 0x8cf36c | fd79bfa9fd030faa | 特权状态机 |

### 4.2 Pool slot 加载证据

```
slot 0x59a4 (ref=121017, 喵喵块 class 区域内):
  - 0xbd4188 [pair] in 0xbd3540 (立即获取+AdMob banner builder)

slot 0x59bc (ref=28525, "喵喵饿了", 全局唯一):
  - 0xae36fc [pair] in 0xae30e0 (喵喵饿了 widget build)
  - 0xa55cbc [pair] in 0xa54178 (VIP/喵喵页 ctor)

slot 0x59bd (ref=91705):
  - 0xa54178, 0xa570c0, 0xb68308, 0xb9fc84, 0xbc5dc8 (5 loaders)
```

### 4.3 已确认安全的 patch 点

```
0xbc5dd0 (reward prompt return-null): efa100d1a00b40f9 → e00316aac0035fd6
  效果: 喵喵块不可点击（主控已验证）
  
0xae32d4 (喵喵饿了 return-null): e00301aa → e00316aa
  效果: 0xae30e0 返回 null（主控验证对阅读页喵喵块无效）
  含义: 阅读页喵喵块不是 0xae30e0 构建的
```

### 4.4 待精确定位的 patch 点

```
0xbd2e1c 内 BL 0xbd3540: 精确偏移待 test1 Ghidra 反编译确定
  patch: 1f2003d5 (NOP) — 跳过首页 overlay/banner 构建
  
0xbd3540 内"立即获取"widget 构造: 需 capstone disasm
  patch: NOP 相关分支 — 保留其他首页 UI
```

---

## §5 交付清单

| # | 内容 | 状态 |
|---|------|------|
| 1 | 喵喵块函数架构完整清查 | ✅ 完成 |
| 2 | 阅读页 build 函数链 | ✅ 定位 (0xb3abd0/0xbc82d0) |
| 3 | 首页 build 函数链 | ✅ 定位 (0xbd2e1c→0xbd3540) |
| 4 | 喵喵块精确父级 | ⚠️ pool 间接墙未突破，给替代方案 |
| 5 | 首页 overlay builder | ✅ 定位 (0xbd3540 + 0x8cf36c) |
| 6 | 首页 banner builder | ✅ 定位 (0xbd3540 + 0x87f250) |
| 7 | 字节级 patch 验证 | ✅ 全部 entry 点通过 |
| 8 | 与喵喵块同源判断 | ✅ 证据支持同源，待主控验证 |
| 9 | 交叉验证 test1/test2 | ✅ 建议已给出 |
| 10 | 主控测试优先顺序 | ✅ P0-P3 排序 |

---

## §6 建议主控测试顺序

### 第一轮 (验证同源假设)
1. **Patch 0xbc5dc8 return-null** (方案 M1/M3) — 确认喵喵块 onTap 消失
2. **Patch 0xbd2e1c entry return-null** — 观察：
   - 首页是否崩溃？
   - 喵喵块是否消失（在阅读页和首页都检查）？
   - overlay/banner 是否消失？
   - 如果首页崩溃→证明 0xbd2e1c 是首页框架，不能简单 return-null
   - 如果喵喵块和 overlay/banner 同时消失→**同源假设确认** ✅

### 第二轮 (精确截断，需 test1 Ghidra 先行)
3. 等 test1 提供 0xbd2e1c 内 BL 0xbd3540 的精确地址
4. NOP 该 BL → 观察 overlay/banner 是否消失，喵喵块是否受影响

### 第三轮 (备用)
5. 如上述均失败，回退到 M4 (DraggableFloatWidget NOP)
6. 如仍失败，接受「喵喵块视觉不可去」（只有不可点击方案 M3）

---

## 附录A：全局喵喵相关字符串索引

| 字符串 | ref | slot | 加载函数 |
|--------|-----|------|---------|
| 喵喵饿了 | 28525 | 0x59bc | 0xae30e0, 0xa54178 |
| 每日喂喵 | 21707 | 0x59bb | 0x846b1c, 0xa54178, 0xae71bc |
| 饿了喵~ | 19128 | 0x869c | 0xb9fc84, 0xbc5dc8 |
| 喵喵喂饱了~ | ? | ? | 0xa56be4 |
| 喵喵喵~ | ? | ? | 0xb9fc84 |
| 训练喵喵 | ? | ? | 0xa54178 |
| 让喵喵更智能 | ? | ? | 0xa54178 |
| 分享喵喵 | ? | ? | 0xa54178 |
| AI喵喵努力推荐中... | ? | ? | 0xadcad0 |
| 喵喵载入中... | ? | ? | 0xa53998 |

## 附录B：首页相关字符串索引

| 字符串 | 函数 |
|--------|------|
| Home | 0xbd2e1c |
| 立即获取 | 0xbd3540 |
| 已生效！剩余 | 0x8cf36c |
| adNum: | 0xbca240, 0x7e8534, 0xa54178 |
| noAdSourceNumLimit | 0x838c74 |
| noAdAllowSourceList | 0x839e80 |
| admobBannerFurtureView | 0xbd3540, 0xa20b3c |
| 商店版 | 0xbd3084, 0xbd3540 |
| 极速版 | 0xbd3084 |
| 全能的自定义检索阅读工具 | 0xbd3084, 0xbd3540 |
