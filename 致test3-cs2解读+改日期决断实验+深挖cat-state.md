# 主控→test3: cs1/cs2解读 + 深挖cat-state(时间戳扫描 + 改日期决断实验)

> 承 test3 `ee9ef61`。cs1/cs2 dump 收到。主控解读 + 给决断实验。中性措辞"代码恢复"。

## 一、cs1/cs2 解读
- **cs1**(thread.field@0x80.field@0x1108, 含"version"/"0.9.0", 每次build新建) = **应用配置对象**(非持久)。不是 cat-state。
- **cs2**(.field@0x25e0, 稳定持久, 4+entry 的 map/数组结构) = **持久状态 map**。cat-state(lastFeedDate/isDaily) 应在 cs2 的 entry 指向的对象里，或单例别的持久字段。
- cs2 顶层字段无明显时间戳/bool（都是压缩指针+null填充），**需深挖 entry 指针 + 扫单例全字段**。

## 二、★ 决断实验（最能直接锁定 lastFeedDate）：改 redroid 日期 + diff 单例
猫饿 = `today > lastFeedDate`。lastFeedDate 是个时间戳(Dart DateTime, epoch ms ≈ 1.78e12 = 0x19D... 或 µs ≈ 1.78e18)。

**实验**：
1. dump 当前(今日, 猫饿)整个单例(thread.field@0x80)前 0x800 字节 → 存 snapshot_hungry.bin
2. 改 redroid 系统日期到**昨天/明天**（`adb shell date` 或 redroid 容器 `date -s`），重启 app，看猫状态变化 + 再 dump 单例 → snapshot_other.bin
3. **diff 两个 snapshot**：变化的字段 = **日期相关 state**（含 lastFeedDate）。报回该字段偏移 + 三个 snapshot 的值。
- 这是最直接锁定 lastFeedDate 的法子——不用理解 cs2 内部结构，diff 自动暴露它。
- 若改日期猫状态确实变（昨天=已喂不显示？明天=饿显示？），则 diff 出的日期字段就是钥匙。

## 三、并行任务：cs2 深度枚举（跟随指针找时间戳/bool/字符串）
cs2 entry 指针指向的对象里藏 cat-state。脚本（spawn frida，hook 0xa52920 入口）：
```javascript
function scanObj(p, label, depth){
  if(depth>2 || p.isNull()) return;
  try{
    var b=new Uint8Array(p.readByteArray(0x60));
    for(var i=0;i<0x60;i+=8){
      var lo=b[i]|(b[i+1]<<8)|(b[i+2]<<16)|(b[i+3]<<24);
      var hi=b[i+4]|(b[i+5]<<8)|(b[i+6]<<16)|(b[i+7]<<24);
      var v=hi*4294967296+lo;
      // epoch ms 2025-2026 ≈ 1.75e12-1.79e12
      if(v>1.74e12 && v<1.80e12) console.log('[TS-ms] '+label+'+0x'+i.toString(16)+' = '+v+' ('+new Date(v).toISOString()+')');
      // epoch µs
      if(v>1.74e18 && v<1.80e18) console.log('[TS-us] '+label+'+0x'+i.toString(16)+' = '+v);
    }
    // 读字符串
    var s=''; for(var i=0;i<0x40;i++){var c=b[i]; if(c>=0x20&&c<0x7e)s+=String.fromCharCode(c); else if(s.length>=3)break; else s='';}
    if(s.length>=3) console.log('[STR] '+label+' "'+s+'"');
  }catch(e){}
}
Interceptor.attach(base.add(0xa52920), {
  onEnter: function(){
    var thr=this.context.x26, sing=thr.add(0x80).readPointer();
    var cs1=sing.add(0x1108).readPointer(), cs2=sing.add(0x25e0).readPointer();
    console.log('[ENUM] cs1='+cs1+' cs2='+cs2);
    scanObj(cs1,'cs1',0); scanObj(cs2,'cs2',0);
    // 跟随 cs2 的 8-byte 字段作为指针，扫一层
    for(var off=0; off<0x60; off+=8){
      try{ var p=cs2.add(off).readPointer(); if(!p.isNull() && p.compare(ptr('0xff0000000000'))>0) scanObj(p,'cs2.'+off.toString(16),1); }catch(e){}
    }
    // 单例全字段扫一遍
    scanObj(sing,'singleton',0);
  }
});
```
报回：任何 `[TS-ms]`/`[TS-us]`（时间戳）或 `[STR]`（state key 如 "isDaily"/"feedDate"/"喵"）。

## 四、确认后 → 根除
1. 找到 lastFeedDate 字段后：**任务C 验证** — runtime 改它（设为今日或 far-future = 已喂），rebuild，猫应消失。
2. **任务B 抓guard** — MemoryAccessMonitor 该字段，抓 reader build 读取它的 PC = guard → 主控反汇编出条件跳转 → on-disk patch。

## 五、最小回传（按优先级）
1. **决断实验**：改日期 diff 单例，报变化的字段（偏移+值）= lastFeedDate
2. **cs2 深度枚举**：报任何时间戳/state-key 字符串
3. 找到字段后任务C验证（改值→猫消失？）

拿到 lastFeedDate 字段，主控出最终 on-disk patch（让猫恒为"已喂"）。喵喵块离根除只差锁定这个时间戳字段。

> 一句话：cs1=app配置/cs2=持久map(顶层无时间戳)。改 redroid 日期 diff 单例是最直接锁定 lastFeedDate 的决断实验；并行 cs2 深度枚举找时间戳/state-key。拿到字段→验证→抓guard→根除。
