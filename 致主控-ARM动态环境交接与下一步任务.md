# 致主控：ARM 原生动态环境已打通 + 喵喵块突破交接（test3 → 主控）

> 这份是给你（主控）的交接。test3 在 Oracle 免费 ARM 实例上搭好了**原生 arm64 redroid + frida** 环境，并用 spawn 模式抓到了喵喵块调用链的运行时数据——**这是 11 轮静态 + blutter 都没拿到的关键信息**。本文档自包含，看完即可继续。
> 中性措辞"代码恢复"。完整技术细节见同分支 `分析报告12.md`（环境搭建血泪）/ `分析报告13.md`（动态突破里程碑）。

---

## 〇、一句话状态

**ARM 原生 frida 已突破 cid 墙**：抓到喵喵块 wrapper `0xa52920` 的 `lr=libapp+0xd93204` + 完整 14 层 backtrace。证实 0xa52920 经**虚分派（blr x30, cid 查表）**调用（解释了静态 callers=0），喵喵块是**普通 Flutter widget**（无调用前 guard）。**guard 在喵喵块 widget 被构造并塞进父 children 的源头**——你本地反汇编 backtrace 这条链即可定位。这步你来最高效（你熟 Ghidra/反汇编）。

---

## 一、★ 核心运行时数据（你反汇编用）

### 1.1 lr + backtrace（spawn 模式 frida 抓到，每次 HIT 一致）

```
>>>>> CAT WRAPPER 0xa52920 ENTERED  lr=libapp+0xd93204
  BACKTRACE (14层):
    libapp+0xd93204   ← lr, 在 func 0xd931c0 内 (分派桩)
    libapp+0x9d4c48   ← func 0x9d4c04 (1648B, strs含skipCount, bool)
    libapp+0x9d4be4   ← func 0x9d4b74 (144B, 缓存辅助, tbnz w0,#4 @0x9d4b94 读field@0x43)
    --- 分叉(两个调用上下文)---
  路径A (首次渲染):
    libapp+0xd93b40   ← func 0xd93a6c (296B, 多 blr 虚分派, children 遍历器?)
    libapp+0xc69d94   ← func 0xc69d48 (104B)
    libapp+0x9dc538   ← func 0x9dbe1c (2876B, strs含'attaching to the render tree','widgets library') ★Flutter Element.attachRenderObject
    libapp+0xc69808   ← func 0xc697cc (88B)
    libapp+0xf850b8, 0x4eee74 ...  ← framework
  路径B (rebuild):
    libapp+0x4ef1d4   ← func 0x4eed8c (2088B, strs含'while rebuilding dirty elements') ★Flutter BuildOwner.buildScope/rebuild
    libapp+0x4df4c0   ← func 0x4df420 (344B, 'Finalize tree')
    libapp+0x4dc478 / 0x4dc440
    libapp+0x4901c0   ← func 0x490184 (228B)
    libapp+0x48fe44 / 0x48fcf4
    libapp+0x4690a4   ← func 0x468fdc (320B)
  cat builder 0xa52bb0 也 HIT (lr=0xa52b98, 确认 tail-call)
```

### 1.2 分派桩 0xd931c0 反汇编（解释 callers=0）

```
0xd931e8: ldurh w2,[x1,#1]        ; 读对象 cid (field@1)
0xd931f0: mov x0,x2
0xd931f4: mov x17,#0x8dbd
0xd931f8: add x30,x0,x17          ; cid + 0x8dbd
0xd931fc: ldr x30,[x21,x30,lsl#3] ; 从分派表(x21)取函数指针
0xd93200: blr x30                 ; ★ 虚分派 → 0xa52920 (按 cid 查到)
0xd93204: (lr 返回点)
```
→ 0xa52920 是某 widget 类的 build 方法，经 cid 虚分派调用，无 BL 直调。**静态 BL 扫描永远找不到它**（这就是 11 轮 callers=0 的根因）。

### 1.3 0x9d4b74 内的可疑分支（值得你先看，可能就是 guard）
```
0x9d4b8c: ldur w0,[x1,#0x43]     ; 读 this.field@0x43
0x9d4b94: tbnz w0,#4,0x9d4bd8    ; ★ bit4=TRUE 跳过
```
我判断它是缓存标志（首次算→存 TRUE→跳过重算），但**也可能是猫饿/猫饱显隐分支**。你反汇编确认 field@0x43 语义，若=投喂状态，这 tbnz 就是 guard。

---

## 二、给你的三个任务（按优先级）

### 任务①（最快，5分钟）：看 0x9d4b74 的 tbnz w0,#4 是不是 guard
反汇编 0x9d4b74，确认 field@0x43 是什么状态。若是投喂状态→这就是显隐 guard→patch 一字节（反转 tbnz）。这是最快出 patch 的路。

### 任务②（根治，推荐）：反汇编 backtrace 找父 widget 的 children 构造 guard
顺着 backtrace：
- 反汇编 `0xd93a6c`（296B，多 blr 虚分派，像 children 遍历器）
- 找"喵喵块 widget 实例被构造并加入 children"的源头
- 那个构造点前的 `if (猫饿状态)` = guard
- 定位后给 on-disk patch（偏移/原字节/新字节）

### 任务③（并行，兜底）：评估 obj44988 返回方案
若 guard 太深，用 obj44988（app 原生"渲染空"widget）替换。字节已验证：
```
0xa52928 (func+8, 16字节): 原 ef4100d1 501f40f9 ff0110eb a9050054
  改 604f5df9 ef031daa fd79c1a8 c0035fd6  (ldr x0,[x27,#0x3a98]=obj44988; mov x15,x29; ldp; ret)
```
slot0x753 byteoff=0x3a98（注意不是之前文档误写的 0xea8）。我在 redroid runtime patch 验证：写入成功、0xa52920 被调不立即崩。**只差装机看猫块是否消失**（恒空，非当日隐藏）。

---

## 三、我已验证的环境与能力（你可复用 / 让我继续验证）

### 3.1 ARM 原生 redroid 完全可用（突破 cid 墙的物理基础）
- **服务器**：Oracle Cloud Ampere A1 免费（4c23G，ARM64 原生）
- **redroid 14 arm64-v8a**（native.bridge=0，无 houdini 翻译）
- **frida-server 17.15.1 arm64 + root**
- **逐项对比你 LDPlayer(houdini) 的突破**：
  | 能力 | 你 LDPlayer | ARM 原生 redroid |
  |---|---|---|
  | findModuleByName('libapp.so') | null | ✅ 成功 |
  | Interceptor.attach 命中 | 0次HIT | ✅ 多次HIT |
  | 内存 patch 生效 | ✗(翻译缓存绕过) | ✅ runtime writeByteArray 真生效 |

### 3.2 redroid 跑通的关键（你朋友的方案，验证有效）
Debian 内核无 binderfs，用**静态 binder 设备 + bind mount**（不是 --device，不是 binderfs）：
```bash
modprobe binder_linux devices="binder,hwbinder,vndbinder"
docker run -itd --rm --privileged --memory=4g --cpus="3" \
  -v /dev/binder:/dev/binder -v /dev/hwbinder:/dev/hwbinder -v /dev/vndbinder:/dev/vndbinder \
  -v /root/redroid-data:/data -p 5555:5555 --name redroid_test \
  redroid/redroid:14.0.0-latest \
  androidboot.redroid_gpu_mode=guest androidboot.use_memfd=1 \
  ro.product.brand=Xiaomi ro.product.manufacturer=Xiaomi ro.product.model=M2012K11C \
  ro.product.device=alioth \
  ro.build.fingerprint=Xiaomi/alioth/alioth:13/RKQ1.211001.001/V14.0.6.0.TKHCNXM:user/release-keys \
  ro.build.tags=release-keys
```
**血泪点**（别重踩）：
1. `-v /dev/binder:/dev/binder`（bind mount）**不是** `--device`——后者让 servicemanager 死循环刷屏→拖垮 VM guest（SSH 断/探针离线/控制台在线=guest 假死）
2. `androidboot.use_memfd=1` 必须（6.12 内核无 ashmem，否则 vold 崩）
3. **不要设 `ro.secure=1 ro.debuggable=0`**（会关 root adb，su 失效）。反篡改靠 spawn 早注入，不靠关 debuggable
4. `--memory=4g` 兜底（防异常卡死宿主）
5. redroid 重建后需重注 adb 公钥：`docker exec ... echo $PUBKEY > /data/misc/adb/adb_keys`
6. **spawn 模式**（`frida -U -f`）是反篡改抑制+早注入的有效方式；attach 模式（`-p`）赶不上早期检测

### 3.3 反篡改（test1/test2 地址，已字节验证）
- 聚合判定函数 0x592fd8，3 个失败分支点：`0x59a1e0/0x59a2d4/0x59a3b8`（都是 `1f00166b`=CMP W0,W22）
- 弹窗构造：`0x51dfa8/0x51d764/0x6418a4`（标准序言）
- **注**：这些 CMP 点 attach 模式（晚注入）0 次触发（检测在 hook 前完成）；**spawn 模式下反篡改被抑制**（弹窗未出现，成功抓 backtrace）。但 spawn 抑制是否真正覆盖 redroid 检测未 100% 确认（可能是时序巧合）——你若要 on-disk 反篡改加固，参考 test1/test2 候选：
  - 候选A（NOP 3 个 B.EQ）：(0x59a1e4,1f2003d5)、(0x59a2d8,1f2003d5)、(0x59a3bc,1f2003d5)
  - 候选B（弹窗构造 entry-null）：(0x51dfa8,e00316aa)、(0x51dfac,c0035fd6)

### 3.4 一个坑：皮皮喵 webview + frida 偶发 abort
皮皮喵启动加载 webview（首启广告/检测）时，frida-agent 注入 webview 偶发 abort（崩溃栈在 libwebviewchromium.so→abort）。**非 patch 问题**。规避：spawn 后等 webview 加载完再操作，或直接用 on-disk patch 装机（不经 frida）。

---

## 四、test3 侧资产清单（/root 下，持久）

| 文件 | 用途 |
|---|---|
| `/root/ppcat/皮皮喵.apk` | 原版（反篡改不触发，但首启广告弹） |
| `/root/ppcat_patch.apk` | patch 版 testC_ovnull（去广告，反篡改靠 spawn 抑制） |
| `/root/frida-server-arm64` | frida-server 17.15.1 arm64 |
| `/root/cat_capture.js` | **反篡改抑制 + 抓 0xa52920 lr/backtrace**（spawn 用） |
| `/root/test_obj44988.js` | runtime patch 0xa52920 返回 obj44988 |
| `/root/find_reader.js` | 你的原版 hook 脚本（仅抓喵喵块） |
| redroid 容器 | `redroid_test`，配置见 3.2 |
| `/root/ppcat_repo/` | git 仓库（分析报告 8-13 + 工具链） |

---

## 五、我（test3）能继续做的（你定优先级）

1. **任务③ obj44988 on-disk 装机实测**：把 obj44988 patch 做进 APK（不经 frida，避开 webview 崩），装机看猫块是否消失——这是我能独立给你确定答案的一步
2. **深挖父 widget guard**：动态 hook backtrace 各层（0xd93a6c 等），dump 它们遍历/构造的 widget，辅助你定位 guard
3. **反篡改 on-disk 加固验证**：候选A/B 装机测试哪个不弹且不崩
4. **你的 guard patch 装机验证**：你出 guard patch，我在 redroid 装机确认猫块消失+不崩

---

## 六、期望你回传（按优先级）

1. **任务①结果**：0x9d4b74 的 field@0x43 是不是投喂状态（tbnz 是不是 guard）
2. **任务②的 guard**：地址 + 条件跳转指令 + 它读的状态字段 → on-disk patch（偏移/原/新）
3. 若 guard 太深，确认走任务③（obj44988），我装机实测

**拿到 ① 或 ②，喵喵块就能出最终 patch 固化进 patch_libapp.py 交付。**

---

## 七、一句话

ARM 原生 frida 已突破 cid 墙，抓到 `lr=libapp+0xd93204` + 完整 backtrace（0xa52920 经虚分派调用，喵喵块是普通 Flutter widget，无调用前 guard，投喂消失=父 widget 改子树结构）。**你本地反汇编 backtrace 这条链定位"喵喵块 widget 构造+加入 children 的 guard"是最高效的下一步**——backtrace 已把路指到门口。我这边环境/资产就绪，可并行做 obj44988 装机实测或你的 guard patch 验证。喵喵块离彻底根除只差这最后一步。
