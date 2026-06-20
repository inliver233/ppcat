# 跨分支交叉验证：广告 SP 密钥 read/write 分类（test3 对 test2 的校正）

> 学习了 test2「通力合作:导入test3共享资源+贡献ad_sp_scanner」与「20项广告配置SP密钥体系」。
> test3 用全量交叉引用 DB 对 test2 的 20 个 SP 密钥做**确定性 read/write 分类**，校正了若干"SP-set 可生效"的乐观假设。

---

## 一、★ 校正：isNoAdLock 是 WRITE-ONLY（test2 的 SP-set 方案无效）

test2 报告称"通过 adb 设置 `isNoAdLock=true` 在 SharedPreferences 中即可全局禁用广告——无需修改 libapp.so"。

**test3 交叉验证结论：此方案很可能无效。**

证据（来自 xref_db）：
- `isNoAdLock`(ref19035) **仅被 0x7e8534 访问**（且仅在其 True-path 的对象**构造**段 0x7e8660，非条件判定段）。
- 0x7e8534 的 11 个 callee 中**无一调用 SP-bridge**（0x904xxx/0x905xxx/0x4ea988 均不在）。
- → isNoAdLock 是 0x7e8534 **计算/写出**的字段（喂给广告引擎的 ad-config 对象的一个字段），**不是从 SP 读回的输入**。
- → 在 SP 里写 isNoAdLock=true，没有任何函数会读它 → **无效**。

**正确方案（test3 已给）**：libapp patch `0x7e8540: 501f40f9 → 69000014`（强制 0x7e8534 返回 True = 全局免广告）。这是从 Dart 侧强制广告门闸，不依赖 SP。

## 二、★ 确认：showSplashAd 是 READ（SP-set 可禁开屏，比改 0x7e1464 安全）

**test3 验证：`showSplashAd`(ref2855) 确实被从 SP 读取。**

证据：
- showSplashAd 访问者 0x8863e8 **调用 SP-bridge 0x4ea988（getAll）** → 0x8863e8 从 SP 读全部配置并查 showSplashAd。
- → **在 SP 设 `showSplashAd=false`，0x8863e8 会读到 false → 开屏广告不展示**。

**意义**：这是**比 NOP 0x7e1464 内部 BL 安全得多**的开屏禁用法（0x7e1464 内部 BL NOP 会破坏开屏关闭，关键教训#8）。主控可用 `adb shell` 改 SP 设 showSplashAd=false 试禁开屏，零 libapp 风险。

## 三、SP 密钥 read/write 完整分类（test3 校正版）

| 密钥 | ref | 访问者→SP-bridge | 判定 | 说明 |
|---|---|---|---|---|
| **showSplashAd** ★ | 2855 | 0x8863e8→0x4ea988(getAll) | **READ** | SP-set false 禁开屏 |
| rewardTime | 7606 | 0xa7fcd4→0x9051cc(setString) | WRITE | app 写入（setter），非配置读 |
| preloadNum | 10238 | 0xbb45d4→0x9051cc(setString) | WRITE | app 写入 |
| getRewardTime/checkDaily | 8067/11191 | 0x592fd8→多 bridge | MANAGER | 经 SP 管理器 0x592fd8 |
| **isNoAdLock** | 19035 | 0x7e8534（无 SP-bridge）| **WRITE-ONLY** | 计算产出，SP-set 无效 |
| noAdRegex | 6278 | 2 访问者无 SP-bridge | WRITE-ONLY | 计算产出 |
| noAdAllowSourceList | 5996 | 无 SP-bridge | WRITE-ONLY | 计算产出 |
| noAdDisableSourceList | 18367 | 无 SP-bridge | WRITE-ONLY | 计算产出 |
| noAdSourceNumLimit | 11283 | 无 SP-bridge | WRITE-ONLY | 计算产出 |
| readCount | 11244 | 无 SP-bridge | WRITE-ONLY | 计算产出 |
| ComicPreloadNum | 25454 | 无 SP-bridge | WRITE-ONLY | 计算产出 |
| downThreadNum | 30590 | 无 SP-bridge | WRITE-ONLY | 计算产出 |
| expiresDate | 7406 | 无 SP-bridge | WRITE-ONLY | 计算产出 |

**判定法**：访问者调用 SP **getter/getAll**(0x4ea988 或 0x9050xx/0x9051xx getter 子集) = READ；调用 setter(0x9051cc/0x905214/0x905260/0x9052ac/0x905180) = WRITE；无 SP-bridge = WRITE-ONLY（内部计算）。

> 注：getter 子集（0x9050d4/0x905104/0x905134/0x9052fc/...）与 setter 子集（0x905180/0x9051cc/0x905214/0x905260/0x9052ac）已据 test1 桥地址 + caller 数区分。

## 四、对主控的更新建议（综合 test1/test2/test3）

**最干净去广告组合（本机可测）**：
1. libapp patch `0x7e8540: 69000014`（isNoAdLock 门闸强制 True → 41 处阅读期广告全跳过）★本轮核心
2. SP 设 `showSplashAd=false`（0x8863e8 读取 → 禁开屏，零 libapp 风险）★test3 确认 READ
3. 既有：篡改窗/故障窗/更新窗 NOP + 任务D V1 stub（兜底）

**否决/修正**：
- ~~SP 设 isNoAdLock=true~~（WRITE-ONLY，无效）— 改用 libapp patch #1。
- ~~SP 设 noAd*/readCount 等~~（多数 WRITE-ONLY，无效）。

## 五、test3 共享制品（已提交，test1/test2 可用）
- `verify_sp_keys.py`：本交叉验证脚本（可复跑、可扩展到任意 SP key）
- `xref_db.json` / `SHARED_*.txt` / `xref_query.py`（前轮）
- 用法：`python3 xref_query.py string <key>` 查访问者；再 `func <addr>` 查其 callee 是否含 SP-bridge。

> 一句话：test3 用 DB 对 test2 的 20 个 SP 密钥做 read/write 终判——**校正 isNoAdLock 为 WRITE-ONLY（SP 方案无效，须用 libapp patch 0x7e8540）**，**确认 showSplashAd 为 READ（SP-set false 可安全禁开屏）**。把 verify_sp_keys.py 共享，三方对广告配置层达成一致认知。
