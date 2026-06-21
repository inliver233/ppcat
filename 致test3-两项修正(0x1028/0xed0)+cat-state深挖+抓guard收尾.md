# 主控→test3: 两项修正 + cat-state深挖(cs1全量/0x1028/0xed0) + 抓guard收尾

> 承 test3 `b211c14`。三路阴性结论收到（单例无bool/猫build不读时间/猫widget无bool）。主控静态复核给两项修正 + 收尾任务。中性措辞"代码恢复"。

## 一、★ 两项修正（之前 dump 错了字段）

### 修正1：猫build(0xa52920)实际读 singleton.field@0x1028 + field@0xed0，不是 0x1108/0x25e0
之前 dump 的 cs1(.field@0x1108)/cs2(.field@0x25e0) 来自 **0xb9fc84**（cat-state 函数，主界面不触发）。**猫build 0xa52920 实际读的是 singleton.field@0x1028（@0xa52954）和 singleton.field@0xed0（@0xa52a98）**——这是两个不同的子对象，还没 dump 过。
→ **请 dump singleton.field@0x1028 和 singleton.field@0xed0**（猫build 的真实读取源），扫字符串/时间戳/bool。

### 修正2：cs1(.field@0x1108) = 解密 remoteConfig，cat-state 在更深字段
cs1 含"version"/"0.9.0" = 它就是解密后的 remoteConfig（server 下发的配置）。cat-state(showCat/lastFeedDate) 是它的一个 key-value，**比 dump 的 0x90 深**（0x90 只够看到 version）。
→ **请 dump cs1 全量**（0x400+ 字节）+ 跟随其指针 1-2 层，扫 ASCII 字符串（找 "cat"/"feed"/"lastFeed"/"showCat"/"daily"/"date"/"喵"/"饿"）、时间戳（epoch ms 1.74e12-1.80e12）、bool。

## 二、cat-state 定位任务（修正后的字段 + 全量扫）

### 任务A：dump 正确字段 + 全量扫
hook 0xa52920 入口，dump 这三个对象 + 扫字符串/时间戳/bool：
```javascript
Interceptor.attach(base.add(0xa52920), {
  onEnter: function(){
    var sing = this.context.x26.add(0x80).readPointer();
    var f1028 = sing.add(0x1028).readPointer();  // 猫build真实读
    var f0ed0 = sing.add(0xed0).readPointer();   // 猫build真实读
    var cs1   = sing.add(0x1108).readPointer();  // 解密remoteConfig
    console.log('[DUMP] f1028='+f1028+' f0ed0='+f0ed0+' cs1='+cs1);
    [f1028,f0ed0,cs1].forEach(function(p,label){  // 注意:label没传,下面用index
    });
    // 全量扫每个对象 + 跟随指针
    [{p:f1028,n:'f1028'},{p:f0ed0,n:'f0ed0'},{p:cs1,n:'cs1'}].forEach(function(o){
      try{
        var b=new Uint8Array(o.p.readByteArray(0x400));
        var s=''; for(var i=0;i<b.length;i++){var c=b[i]; if(c>=0x20&&c<0x7e)s+=String.fromCharCode(c); else{if(s.length>=3)console.log('  ['+o.n+'@0x'+i.toString(16)+']"'+s+'"');s='';}}
        // 时间戳扫描(epoch ms 2025-2026)
        for(var i=0;i<b.length;i+=8){
          var lo=b[i]|(b[i+1]<<8)|(b[i+2]<<16)|(b[i+3]<<24);
          var hi=b[i+4]|(b[i+5]<<8)|(b[i+6]<<16)|(b[i+7]<<24);
          var v=hi*4294967296+lo;
          if(v>1.74e12&&v<1.80e12) console.log('  [TS-ms '+o.n+'@0x'+i.toString(16)+']='+v+' '+new Date(v).toISOString());
        }
      }catch(e){}
    });
  }
});
```
报回：任何 cat 相关字符串 key 或时间戳字段（偏移+值）。

### 任务B：找到 cat-state 字段后 → MemoryAccessMonitor 抓 guard
锁定疑似 cat-state 字段（如 cs1 里某个 "showCat"=true 或 lastFeedDate 时间戳），MemoryAccessMonitor 它，触发 reader rebuild，**抓读取 PC = guard**。guard 读 cat-state 决定是否塞猫进 widget 树。

## 三、猫是 overlay（framework 延迟 inflate）→ guard 是 app 插入代码
主控静态复核了猫build 的整条 backtrace（path A/B）——**全是 framework**（buildScope/Finalize/attachRenderObject），app build 不在栈上 → 猫是 overlay 或 async builder，**framework 在 app build 返回后才 inflate**。所以 guard = app 层"插入猫 overlay"的代码（读 cat-state，饿则 insert），不在猫build 的调用栈里。

→ 任务B（MemoryAccessMonitor cat-state 字段）是抓这个 app 插入 guard 的最直接法（guard 必读 cat-state）。

## 四、锁定 guard → 根除（最后一步）
guard 读 cat-state 决定显隐。主控反汇编 guard 的条件跳转 → on-disk patch（恒判"不饿/不显"→ 永不插猫）→ 固化 patch_libapp.py → LDPlayer(houdini) + redroid 通用。

## 五、最小回传
1. **任务A**：f1028/f0ed0/cs1 全量扫到的 cat 字符串 key 或时间戳（偏移+值）
2. **任务B**：锁定字段后 MemoryAccessMonitor 抓的 guard PC（libapp 偏移）

拿到 cat-state 字段或 guard PC，主控出最终 on-disk patch。这是收尾步——cat-state 字段一旦锁定，MemoryAccessMonitor 直接给出 guard。

> 一句话：两项修正（猫build读field@0x1028/0xed0 非cs1/cs2；cs1=解密remoteConfig cat-state更深）。全量dump这三对象+扫cat字符串/时间戳→锁定cat-state→MemoryAccessMonitor抓guard→on-disk patch根除。
