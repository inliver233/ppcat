# 第十轮: frida 能力实测 + 喵喵块状态层探索 (2026-06-21)

> 主控(LDPlayer9 x86_64, houdini arm64翻译)实测 frida 真实能力边界 + 喵喵块投喂状态层探索。
> 接续第九轮(首页overlay根治 + 喵喵块builder 0xa52bb0定位)。

## ★★★ 核心纠正: frida 不是"完全不可用", 但 hook 在 houdini 下失效

之前文档一直说"frida完全不可用"——**这是不准确的**。实测发现:
- frida 基础设施**齐全**: 设备 `/data/local/tmp/frida-server`(111MB)存在, 本机有 frida/frida-ps/frida-trace(Python313, frida 17.14.1)。
- frida-server **可启动**(`nohup frida-server -D`, 监听27042), **可attach** 皮皮喵进程。
- 但 **Interceptor hook 不拦截**, **内存 patch 不生效**(详见下)。

→ 本文档修正所有交接材料里的"frida完全不可用"表述, 改为"frida可attach可读内存, 但hook/patch在houdini翻译层下失效"。

## ★ frida 在 houdini 模拟器的能力边界 (实测确认)

| 能力 | 结果 | 实测证据 |
|---|---|---|
| 启动frida-server | ✅ | PID 29803, 监听 127.0.0.1:27042 |
| attach皮皮喵 | ✅ | pid 27211 (name乱码"皮皮喵"), attach成功 |
| Process.arch | x64 | frida运行在x86_64侧 |
| findModuleByName('libapp.so') | **null** | arm64库被houdini管理, 不在frida模块表 |
| findModuleByName('libflutter.so') | **null** | 同上 |
| enumerateRanges('r--') 见libapp | ✅ | base 0x5178000, 文件偏移0 |
| **内存读取(裸地址)** | ✅ | 读0x920d90=29000014(patch字节), 0xa52bb0=fd79bfa9(序言), 对象池区可读 |
| **Interceptor.attach** | ⚠️ armed无报错但**不拦截** | hook 0xa52bb0+0xa52920, 进书+翻页触发, **0次HIT** |
| **内存patch** | ❌ **不生效** | 改0xa52bb8为return-null(writeByteArray成功+mprotect OK), 重进书后喵喵块**仍在** |

### 为什么 hook/patch 失效? (houdini 翻译机制)
- libapp.so 是 arm64 库, 被 **houdini 翻译成 x86_64** 执行。
- libapp 内存映射: 0x5178000 r--p(off 0, 前0xA52000只读) + **0x5bca000 r-xp(off 0xa52000, 可执行段, 含0xa52xxx cat区)** + 0x5bcb000 r--p + 0x6110000 rw-p(.bss)。
- 0xa52bb0 落在 r-xp 可执行段(0x5bca000 + (0xa52bb0-0xa52000) = 0x5bcabb0, 与frida报告的hook地址吻合)。
- 但 **houdini 在加载时已翻译arm64→x86_64并缓存**, 实际执行走翻译缓存(在别处), 不走libapp原arm64地址。
- frida 的 Interceptor 在原arm64地址插桩(trampoline, 实测0xa52bb0字节被改成 `e9538445...`=bl跳转=trampoline残留), 但翻译执行绕过它。
- 内存patch改的是原arm64字节, 翻译缓存不读它, 故不生效。

→ **结论: frida 在本houdini模拟器无法做动态hook/patch来追踪Dart调用栈(reader build等)**。
→ frida 仍能**读内存**(可做对象图分析翻cid84墙, 但工作量大), 但不如装机patch-test闭环可靠。

## ★ libapp 内存布局确认 (运行时实测)
- 文件偏移 == 内存偏移(文件直映, 非翻译重布局)。内存读0x464ce0=d029b300... 与文件字节**完全一致**。
- libapp基址 = **0x5178000**(内存), 文件偏移0。
- 函数 X 的内存地址 = 0x5178000 + (文件偏移 X)。

## ★ 喵喵块状态层探索 (寻找"饿→饱"持久化字段)

用户关键情报: 原版机器走完reward投喂后, **阅读页喵喵块当天消失**(活的ground truth, 证明app有原生隐藏逻辑)。故探索投喂状态持久化在哪。

### 探索结果: SharedPreferences 无 cat 字段
FlutterSharedPreferences.xml 全部key(9个, 无cat/feed/reward):
```
flutter.firstTime(long) | flutter.gitRuleMap | flutter.isExtStorage(bool)
flutter.remoteConfigSign | flutter.noticeId(long 191227) | flutter.remoteConfig(加密)
flutter.ensureDeclare(bool) | flutter.ruleVersion(long) | flutter.storeIndex(long)
```
→ 猫的"饿/饱"状态**不**在SharedPreferences。

### .app / ua.db SQLite 是 native 书架, 不含猫状态
- .app/.app-wal/.app-shm: 表 = History/Favorite/Book/Tag/Download(漫画书架数据, native层)。History有1行(高武进化书)。
- ua.db(45KB): 友盟统计。
→ 不含猫喂状态。

### .config (318KB) 是加密核心配置 (猫状态疑似在此)
- app_flutter/.config: 二进制(头部745df5a5...), 非明文, strings搜cat/feed/reward/喵/hungry全无。
- 是 app 的核心配置(含书源+状态), **加密了**, 无法直接读。
- 猫的投喂时间状态**疑似**在此加密config里。

### .imprint / exid.dat
- .imprint(995B): protobuf格式, 含 app_version:0.9.0 + 设备指纹hash。
- exid.dat(96B): 友盟 appkey 配置(JSON)。

## ★ 饥饿态状态快照 (投喂前基准, 已备份)
路径: backup/第十轮-frida能力实测与状态层探索/hunger_snapshot/
```
dot_config(318829B, md5=dbf5e976...) | imprint(995B) | exid.dat(96B)
dotapp.db + dotapp.db-wal(185432B) + dotapp.db-shm | ua.db(45KB)
FlutterSharedPreferences.xml(30699B)
```
→ 这是patch版饥饿态的完整状态基准。若后续走"投喂diff"路线, 用原版完成投喂后, diff投喂后状态 vs 此基准, 定位"饿→饱"字段。

## 喵喵块 builder 二次确认 (frida间接)
- frida读0xa52bb0内存 = fd79bfa9(标准stp序言), 确认builder入口正确(patch版libapp此地址未改)。
- 内存patch 0xa52bb8→return-null 不生效(houdini缓存), 但装机entry-null→阅读页空白(第九轮已证), 双重确认0xa52bb0是必需builder。

## 下一步 (路径决策)
1. **路径①(进行中)**: 装机验证三方现成方案 Patch D(0xa52c68: 01→16, cid-safe内容域null) + obj44988返回(偏移0x3a98)。
2. **路径②(若①失败)**: 装原版→走真实reward投喂→diff .config/.imprint/SQLite→定位"饿→饱"字段→patch版预写→app走原生隐藏逻辑。
3. frida内存读取作为翻cid84墙的备用手段。

## 复现: frida 启动 (本houdini模拟器, 仅读内存有价值)
```bash
ADB="/e/LDPlayer/LDPlayer9/adb.exe"; DEV="-s emulator-5554"
MSYS_NO_PATHCONV=1 "$ADB" $DEV shell "su -c 'nohup /data/local/tmp/frida-server -D >/dev/null 2>&1 &'"
# attach + 读内存 (Python313的frida):
PY313="/c/Users/inliver/AppData/Local/Programs/Python/Python313/python.exe"
"$PY313" -c "import frida; s=frida.get_usb_device().attach(27211); ..."  # 用裸地址ptr('0x5178000').add(off).readByteArray(n)
# 注意: Process.findModuleByName('libapp.so')返回null(arm64库被houdini隔离), 必须用enumerateRanges找基址0x5178000
# Interceptor.attach不拦截, Memory.protect+writeByteArray不生效(houdini翻译缓存)。
```
