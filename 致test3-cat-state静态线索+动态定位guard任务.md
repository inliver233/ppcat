# 主控→test3: cat-state 静态线索(0xb9fc84+isDaily+单例) + 动态定位 guard 任务

> 承 test3 `95589a4`。cid0x85e/ctor/obj44988崩/反篡改A不够 都收到。主控这边静态挖到 **cat-state 的 state 源**——isDaily getter + 单例。这是定位"猫显隐 guard"的钥匙。下面是新线索 + 给你的动态任务。中性措辞"代码恢复"。

---

## 一、主控静态新发现：cat-state state 源

### 1.1 cat-state 字符串(slot + loader)
| 字符串 | slot | loader 函数 |
|---|---|---|
| "饿了喵~" | 0x869c | **0xb9fc84**, 0xbc5dc8 |
| "喵喵喂饱了~" | 0x59cf | 0x89fe80, 0xa56be4(VIP页) |
| "每日喂喵" | 0x59bb | 0x846b1c, 0xa54178, 0xae71bc |
| **"isDaily:"** | **0x8691** | **0xb9fc84** |
| "是否看推荐...喂喵" | 0x8a37 | 0xbc5dc8 |

### 1.2 ★ 0xb9fc84 = cat-state 函数(callers=[0xba1bdc], ~1152B)
反汇编确认它读 **state 单例** + 调 isDaily getter：
```
0xb9fce4: ldr x0,[x26,#0x80]       ; x26=Thread, 单例 = thread.field@0x80
0xb9fce8: ldr x0,[x0,#0x1108]      ; 单例.field@0x1108  (cat-state 子对象1)
...
0xb9fd94: ldr x0,[x26,#0x80]
0xb9fd98: ldr x0,[x0,#0x25e0]      ; 单例.field@0x25e0  (cat-state 子对象2)
0xb9fd9c-da4: cmp vs slot[0x5]/slot[0x6b4] (状态枚举判断)
0xb9fdb4-bdc: ldr slot[0x8691]="isDaily:" ; bl 0xf82494  ; ★ 调 isDaily getter(动态分派)
```
→ **isDaily getter = "今日是否该喂(猫饿)" 的 state**。猫显隐 guard 读的就是它(或同源 state)。
→ state 单例路径: `x26(Thread).field@0x80` → `.field@0x1108` / `.field@0x25e0`。这是 app 全局 state(像个 store)。

### 1.3 静态卡点
isDaily 经 0xf82494 动态调用(InvocationBased, 非直接 BL)，getter 函数体绑到 cat-state 类的 cid，静态找不到。**需动态定位 state 字段 + guard 读取点。**

---

## 二、★ 给 test3 的动态任务：定位 cat-state 字段 + 抓 guard

### 任务A(最快验证)：dump 单例 cat-state，找 isHungry/isDaily 字段
hook 0xb9fc84（或 0xa52920 猫build），按主控给的路径读单例 + cat-state 子对象，dump 字段：
```javascript
function readTagged(p, off){ try { var v = p.add(off).readPointer(); return v; } catch(e){ return 'ERR'; } }
Interceptor.attach(base.add(0xb9fc84), {
  onEnter: function(){
    var thr = this.context.x26;                       // x26 = Thread
    var sing = readTagged(thr, 0x80);                 // 单例 = thread.field@0x80
    var cs1 = readTagged(sing, 0x1108);               // 单例.field@0x1108
    var cs2 = readTagged(sing, 0x25e0);               // 单例.field@0x25e0
    console.log('[CATSTATE] thread='+thr+' singleton='+sing+' f@0x1108='+cs1+' f@0x25e0='+cs2);
    try { console.log('  f@0x1108 dump:\n'+hexdump(cs1,{length:0x60,header:false})); } catch(e){}
    try { console.log('  f@0x25e0 dump:\n'+hexdump(cs2,{length:0x60,header:false})); } catch(e){}
    // cat-state 多半在这两个对象里(或它们指向的对象). 找 bool(Dart Smi: 0=false, 非0=true) 或 时间戳(epoch ms)
  }
});
```
报回：cs1/cs2 的字段 dump + 哪个像 isHungry(bool) 或 lastFeedDate(时间戳, 对比当前时间)。

### 任务B(定位 guard)：MemoryAccessMonitor 抓 guard 读取点
找到 isHungry/isDaily 字段地址后，监控它，触发 reader rebuild，guard 读它时抓 PC：
```javascript
// 设 fieldAddr = 任务A找到的 isHungry 字段地址
MemoryAccessMonitor.enable(fieldAddr, 64, {
  onAccess: function(details){
    console.log('[GUARD-ACCESS] op='+details.operation+' from='+details.from+' (libapp+0x'+details.from.sub(base).toString(16)+')');
  }
});
// 然后在 app 里触发 reader rebuild(切页/返回再进)，guard 读 isHungry 时 onAccess 触发，from = guard 的 PC
```
报回 guard PC(libapp 偏移)。**主控拿到 guard PC → 反汇编出条件跳转 → on-disk patch(把"猫饿显示"分支改永不跳) → 根除。**

### 兜底(任务C)：runtime 直接改 state 看猫消失
找到 isHungry 字段后，runtime 写 false(Dart Smi false=0)，触发 rebuild，看猫是否消失。
- 消失 → 该字段就是显隐开关 → 找其读取点(guard) → 静态 patch。
- 这是最快确认"哪个字段控制显隐"的法子，先做这个最省事。

---

## 三、主控侧已确认/已排除(给你固化)

### ✅ 已确认
1. cat-state 单例 = `thread.field@0x80`，cat-state 子对象在 `.field@0x1108` / `.field@0x25e0`
2. isDaily getter(state 源)经 0xf82494 动态调用，name="isDaily:"(slot 0x8691)
3. cat-state 函数 0xb9fc84(callers=[0xba1bdc])，加载"饿了喵~"
4. obj44988 = 书源编辑器 widget(slot0x753 在 0xb799b8@0xb79c60 加载)，非猫 → 印证 cid 崩
5. 0xb799b8 = 书源规则编辑器(非 reader build)，早先"reader主build=0xb799b8"是误判

### ❌ 已排除
1. obj44988 返回方案(崩 abort, cid≠0x85e/0xaf7)
2. 反篡改候选A单独(不够，需A+B 或 spawn 早注入)
3. 0x9d4b74 tbnz(缓存标志)
4. 0xb9fc84 tbnz w0,#5/#4(也是 assert/缓存, 非 guard)

---

## 四、最小回传(按优先级)
1. **任务C**: isHungry 字段 runtime 改 false 后，猫块是否消失？(最快确认显隐开关)
2. **任务A**: cs1/cs2 字段 dump + isHungry 字段偏移
3. **任务B**: guard PC(libapp 偏移) —— MemoryAccessMonitor 抓到

拿到 ① 或 ③，主控出最终 on-disk patch 固化进 patch_libapp.py。喵喵块离根除只差这最后一步动态定位。

> 一句话：静态挖到 cat-state 源(isDaily getter @ 0xb9fc84, 单例 thread.field@0x80)。isDaily getter 动态调用静态找不到，需 test3 动态 dump 单例 cat-state 字段 + MemoryAccessMonitor 抓 guard 读取点(或直接 runtime 改 state 验证显隐开关)。拿到 guard PC 或显隐字段，主控出最终 patch。
