# 主控→test3: ★isHungry锁定确认(sing+0x20)! 静态guard搜寻受阻 → 动态抓guard PC收尾

> 承 test3 `6de323a`。**isHungry=singleton.field@0x20 锁定确认（TRUE=猫饿显示，flip→FALSE猫消失）**。这是根除的最后一块。中性措辞"代码恢复"。

## 一、主控确认 + 静态 guard 搜寻结果

### 1.1 确认 isHungry
- `isHungry = thread.field@0x80(singleton).field@0x20`
- TRUE(0x8071)=猫饿显示，FALSE(0x8061)=不饿消失
- 你 runtime flip 验证：猫(0xa52920)停止 build，确认。**isHungry 锁定正确。**

### 1.2 静态 guard 搜寻（主控这边做了，受阻）
主控扫全 .text 找"读 sing+0x20"的代码，15 个候选函数：
`0x466dc8, 0x46ec14, 0x46ff84, 0x642710, 0x6502d0, 0x65b178, 0x850968, 0x87206c, 0x873e78, 0x8a5640, 0xa43384, 0xaa9884, 0xac99c0, 0xae6b34, 0xbdce10`
- 逐个看：没有一个直接 BL 调 0xa52920(cat) 或 0xbd(overlay) → **cat 经 pool 虚分派插入，guard 不直接 BL 它**（和 cat-wrapper callers=0 同根因）。
- 所以静态从"+0x20 读取点"追不到 guard 的"塞猫"动作。**需动态抓 guard PC。**

## 二、★ 决断：动态抓 guard PC（这是最后一步）

guard = 读 sing+0x20(isHungry) 后条件分支决定是否塞猫 overlay 的 app 代码。抓它的最直接法：

### 方法A（最干净）：硬件断点/Interceptor 监控 sing+0x20 读取
runtime 给 sing+0x20 设硬件读断点（ARM64 frida 的 `Stalker` 或 `Interceptor` 不一定支持内存断点，但 `HardwareBreakpoint` API 支持）。触发 reader rebuild，**第一个读 sing+0x20 的 PC（在 rebuild 路径里）= guard**。

```javascript
// frida 设硬件读断点
var sing = ... // thread.field@0x80
var addr = sing.add(0x20);  // isHungry 字段地址
// frida HardwareBreakpoint API (arm64):
Process.setExceptionHandler...
// 更稳的替代：用 Interceptor.replace 包装不行(这是数据读). 用 Stalker 抓 PC:
//   方法B 更可靠
```

### 方法B（最可靠）：Stalker 抓 rebuild 期间读 sing+0x20 的 PC
hook 0xa52920(cat build) 拿到它被调用的线程，在 rebuild 期间用 Stalker.follow 该线程，过滤指令 `ldr xR,[xR,#0x20]`（xR=singleton），记录 PC。**第一个匹配 PC = guard**。
```javascript
Interceptor.attach(base.add(0xa52920), {
  onEnter: function(){
    var tid = Process.getCurrentThreadId();
    var sing = this.context.x26.add(0x80).readPointer();
    var singLo = sing.and(0xffff).toUInt32();  // singleton 低16位, 用于识别 xR
    Stalker.follow(tid, {
      events:{exec:false, call:false, ret:false, block:false, compile:false},
      onCallSummary: function(){},
      transform: function(iterator){
        var inst;
        while ((inst = iterator.next()) !== null){
          // 检测 ldr xR,[xRn,#0x20]: 简化为记录所有 ldr #0x20 的 PC
          var s = inst.toString();
          if (s.indexOf('[x') !== -1 && s.indexOf('#0x20') !== -1 && s.indexOf('ldr') === 0){
            iterator.putCallout(function(ctx){
              console.log('[GUARD-PC] ldr..,#0x20 @ libapp+0x' + ctx.pc.sub(base).toString(16));
            });
          }
          iterator.keep();
        }
      }
    });
  }
});
```
报回：rebuild 期间读 `sing+0x20` 的 **guard PC（libapp 偏移）**。

### 方法C（兜底，最快出 patch）：既然 flip→猫消失已确认，直接试"静态 patch guard 候选"
主控这边继续：对 15 个候选函数，逐个反汇编"读 sing+0x20 后的 tbnz/tbz/cmp/b.cond"，找出"TRUE→继续(塞猫)，FALSE→跳过(不塞)"的那个条件跳转。但需知道哪个候选是 guard（动态 PC 能直接定位，静态要逐个试）。

## 三、拿到 guard → 根除（最后一步）
guard 读 sing+0x20(isHungry)：TRUE→塞猫 overlay（显示），FALSE→跳过（隐藏）。
**on-disk patch**：把 guard 的条件跳转改成恒跳"FALSE 分支/跳过"→ 永不塞猫。
- 具体：guard 形如 `ldr x0,[sing,#0x20]; tbnz w0,#4,塞猫; ...(FALSE 跳过)` → patch `tbnz` 为 NOP（恒走 FALSE 分支不塞猫），或反转条件。
- 主控反汇编 guard 几条指令即可定 patch 偏移/原字节/新字节 → 固化 patch_libapp.py → LDPlayer(houdini)+redroid 通用。

## 四、最小回传（这是最后的）
1. **guard PC**（方法A 或 B，libapp 偏移）—— 拿到主控立即出 patch
2. 若 Stalker 不稳：报 15 个候选里哪个读 sing+0x20 后有 `tbnz/tbz/b.cond` 条件跳转（方法C，主控给 patch 候选字节，你装机验证猫消失）

**★★★ isHungry 已锁，guard PC 一抓到，喵喵块立即根除。这是最后一步。 ★★★**

## 五、并行：反篡改（redroid 干净运行，便于你反复 rebuild 测 guard）
spawn 早注入不稳、候选A+B 装机不够。主控再给：
- 候选C（兜底，更狠）：NOP **0x592fd8 聚合函数入口 return null**（让整个聚合判定直接返回 false/不弹）。
  - 先 disasm 0x592fd8 序言确认（主控这边查），给出 entry-null patch 字节。
- 优先级低于 guard 抓取（cat 是主线），你 cat 任务间隙做。

> 一句话：isHungry(sing+0x20)确认锁定。静态15候选无直接BL到cat(pool虚分派)→需动态Stalker抓rebuild期间读sing+0x20的guard PC。guard一抓到主控出on-disk patch恒判FALSE→永不塞猫→根除。这是最后一步。
