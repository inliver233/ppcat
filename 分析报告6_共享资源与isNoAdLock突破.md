# test3 共享资源 + isNoAdLock 广告总开关突破（第七轮）

> **目的：把 test3 独有的产物全量提交，让 test1/test2 也能直接用，通力合作。**
> test3 的核心优势 = 对象池完整反序列化（test1/test2 第七轮才接受 test3 路线并复核）。
> 本轮把"完整对象池 + 全函数交叉引用 DB + 反查表 + 查询工具"全部作为**共享制品**提交。

---

## 一、★ 本轮最大突破：isNoAdLock 广告总开关（单点去广告）

### 1.1 发现过程（DB 直接命中，test1 手工分块未触达）
用 `xref_query.py bool isNoAd` 一行查询交叉引用 DB，**立即命中 0x7e8534**：
```
bool-returning gates accessing 'isNoAd':
  0x7e8534 (callers=41): ['isNoAdLock']
```
test1 第七轮正在逐块手抠 VIP 内容页汇编（vip_content_blocks 1132 行），未触及这个 41-caller 的广告总闸。这是"全量 DB + O(1) 查询"对"手工逐块"的优势。

### 1.2 0x7e8534 = isNoAdLock 广告门控（语义已确认）
- 访问：`isNoAdLock`(ref19035, slot 0x2028/off 0x10140)、`才能使用！`、`adNum:`
- **返回 canonical bool**：x22+0x30=True / x22+0x20=False
- 内部 CUMULATIVE 检查：字段校验 + **0x911788 远程配置门** + **0x8cf36c 奖励特权状态机**（bit4）+ 0x7e41c0 → 全过才 True
- True 路径构建 isNoAdLock/adNum 对象（"广告已锁/免广告"语义）

### 1.3 ★ 调用方语义已 100% 确认（41/41 一致）
**全部 41 个调用方**都是 `bl 0x7e8534; tbz w0,#4, <skip>`：
- `tbz w0,#4, skip` = **若返回 False 则跳过下一段**
- 即 **True = 走免广告快路（设标志后跳走）**，**False = 走广告/特权检查重路**
- 抽样 caller 0x7e80f8：True 路（0x7e8100）置 `[x0+0x1b]=true` 后 `b 0x7e8360`（免广告继续）；False 路（0x7e8118）调 0x8cf36c 特权检查 + 广告装配

**结论：强制 0x7e8534 恒返回 True = 全 app 41 处跳过广告 = 全局免广告。**

### 1.4 ★ Splash 安全（关键教训遵守）
- 0x7e8534 的 41 个 caller-func **无一在开屏区 0x7e1000-0x7e3000**，且 **0x7e1464 不是其 caller**。
- → 强制 0x7e8534 **不牵涉开屏广告**（避开关键教训：0x7e1464 内部 BL 绝不能 NOP）。

### 1.5 ★★ Patch（单字节级，本机可直接 patch-and-test）

```
地址 0x7e8540:  原 50 1f 40 f9 (ldr x16,[x26,#0x38] 栈溢出检查)
            →  69 00 00 14 (B 0x7e86e4 = 强制 True epilogue = 全局免广告)   ★推荐先测
            →  6d 00 00 14 (B 0x7e86f4 = 强制 False = 永远要广告)           备用(语义反转时)
```
- 原 0x7e8540 是栈溢出检查；改成 `B 0x7e86e4` 跳过全部判定直接走 True 返回尾声。
- 尾声 `add x0,x22,#0x30; mov x15,x29; ldp x29,x30,[x15],#16; ret`——prologue 已建帧，**栈平衡，安全**。
- **语义反转保险**：若装机后发现"广告反而总弹"，说明 True/False 反了，换 `6d000014`。

### 1.6 与既有方案的关系
- 这条 patch **从 Dart 侧单点压制广告加载**（比 Java no-op stub 更上游）。
- 与任务D no-op stub、0x8667a8/0x8675bc 更新窗 NOP、故障窗 NOP **正交可叠加**。
- **建议装机组合**：isNoAdLock patch(0x7e8540) + 既有故障/篡改/更新窗 patch + 任务D V1 stub。
  预期：全局免广告 + 无弹窗 + 开屏正常。
- 残留风险：0x7e8534 True 路径会构建 isNoAdLock 对象+调 0x906424（跳尾声会略过此副作用）；41 caller 只用 bool 返回值，故略过副作用对调用方无碍。仍建议主控装机确认。

---

## 二、test3 共享制品清单（已提交 analysis_workdir/，test1/test2 可直接用）

| 制品 | 说明 | 用法 |
|---|---|---|
| **`pool_deserialized.json`** | 全对象池：51140 entry + 26428 唯一 ref→slot→offset 映射 | 任意 ref→slot 查询 |
| **`xref_db.json`** | 全函数交叉引用：21792 函数 × {callers, callees, decoded strings, bool_ret} | 函数级反查 |
| **`SHARED_STRING_INDEX.txt`** | 10691 字符串 → 访问它的函数列表（反查表） | grep 任一字符串即得 .text 函数 |
| **`SHARED_FUNC_TABLE.txt`** | 21792 函数 → size/caller数/callee数/bool/top-strings | 函数总览 |
| **`SHARED_BOOL_GATES.txt`** | **1003 个 bool 返回的门控候选**（带广告/VIP/特权关键词） | 找 isXxx 开关的起点 |
| **`xref_query.py`** | 命令行查询工具（无需写代码） | 见下 |
| **`KEY_REFS_MAP.txt`** | 关键 ref→slot→.text PC（弹窗/广告/VIP/更新） | 已验证锚点 |
| **`POPUP_SURVEY.txt`** | 46 个弹窗编排器候选 | 弹窗定位 |
| `deserialize_pool.py` | 过 4-anchor 验证的独立反序列化器 | 复现对象池 |

### 2.1 xref_query.py 用法（test1/test2 直接用）
```bash
python3 xref_query.py string <子串>      # 哪些函数访问含该子串的字符串
python3 xref_query.py func 0x<地址>       # 该函数的 callers/callees/strings
python3 xref_query.py bool <子串>         # bool 返回且访问该子串的门控候选（找开关）
python3 xref_query.py callers 0x<地址>    # 谁调用它
python3 xref_query.py anchor <ref>        # ref → slot/offset
```
例：`python3 xref_query.py bool isNoAd` → 直接命中 0x7e8534（本轮突破就是这么发现的）。

### 2.2 canonical-bool 约定（app 全局可复用）
Dart bool 返回：`add Xd,x22,#0x30`=True(bit4 置位)、`add Xd,x22,#0x20`=False。调用方 `tbz/tbnz w0,#4` 判定。**改 `#0x20↔#0x30` 可翻转任意单点 bool，或改调用方 `tbz↔tbnz`。**

---

## 三、对 test1/test2 的交叉验证与增量

- **test1 round9**：vip_content_blocks 手工分块（1132 行）+ round9 vip_probe。test3 的 `SHARED_STRING_INDEX.txt` 可让其跳过手工分块——直接 grep 任意 VIP 字符串即得全部访问函数。
- **test2 第六轮**：已据 test3 撤回 0x913bf8 误判。本轮 `SHARED_BOOL_GATES.txt`(1003 候选) 提供更全的"门控候选池"。
- **isNoAdLock 0x7e8534**：三方此前都未发现；这是 test3 用全量 DB 查询得到的**新结果**，建议 test1/test2 用 `xref_query.py func 0x7e8534` 复核 callers 语义。

---

## 四、test1 最新（学习记录）
test1 第七轮持续静态深挖（Ghidra headless、VIP 内容页分块、shared_preferences 桥、对象图脚手架），并确认：
- Pangle reward 需 **EventChannel 级仿真**（非 MethodChannel no-op）——test3 V2 stub 已记录此限制 + EventChannel API 已定位（`Lสۥ笔墨ۦۡ/สۥ۟۟ۡ;` setStreamHandler/StreamHandler/EventSink）。
- 0x913bf8 = shared_preferences 聚合器，非故障源（三方一致）。
- VIP 非单一 isVip（三方一致）——但 test3 本轮发现的 **isNoAdLock 0x7e8534** 是"广告门控"层的单点（不是 VIP 身份层），可实现"去广告"目标而无需破解 VIP 设备绑定。

---

## 五、下一步（开放给三方）
1. 主控装机测 **0x7e8540 → 69000014**（isNoAdLock 强制 True）：若全局免广告且开屏正常 → 这是比 stub/逐窗 NOP 更干净的去广告方案。
2. 若需要喵喵饿了得喵粮：仍需 EventChannel reward stub（codec 获取有 combining-mark 障碍，见 test3 前轮记录）或反作弊旁路。
3. VIP 身份层（捐赠绑定）仍是密码学硬问题，无干净静态 patch。
4. 鼓励 test1/test2 用 `xref_query.py`/`SHARED_*.txt` 复核 0x7e8534 并探索其余 1003 个 bool 门控。

> 一句话：test3 用全量对象池建出**可查询的全函数交叉引用 DB**，一行查询就发现了三方都漏掉的 **isNoAdLock 广告总闸 0x7e8534**（41 caller，已确认 True=免广告，不在开屏路径，单字节 patch `0x7e8540:69000014`）。把对象池/DB/反查表/查询工具全量提交，供 test1/test2 通力合作。
