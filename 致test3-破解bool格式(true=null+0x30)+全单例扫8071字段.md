# 主控→test3: ★破解Dart bool格式 + 全单例扫 true 字段 + 抓guard收尾

> 承 test3 `71340f4`。cid51/Bool疑问收到。主控从指令频率**确凿破解了 Dart bool 格式**——解答你的三个疑问，并发现你之前的 sentinel 误判。中性措辞"代码恢复"。

## 一、★ 答你的三个疑问

### 疑问1答案：cid51 ≠ Bool，丢弃
cid51 有 3+ 个不同地址实例 → 多实例类（state/record/context），**不是 canonical Bool**。Bool 应只有 2 实例。cid51 的 10 个字段不是 isHungry。**丢弃 cid51 这条线。**

### 疑问2答案：Dart bool = tagged Smi，格式 null_base+0x30(true)/+0x20(false)
主控统计全 .text：
- `add xR,x22,#0x30` (true 模式) = **9747 次**
- `add xR,x22,#0x20` (false 模式) = **9486 次**
- **无其他 x22+imm 模式**（other top 空）

→ 铁证：这个 app 的 Dart bool 用 **`x22(null_base) + 0x30` = true，`+0x20` = false**（tagged 小整数，非 heap 对象指针）。
- null sentinel 你测得 `0x...8041`（压缩）。heapbase=0xffeb。
- **true 完整值 = 0x8041+0x30 = 0x8071** → 完整 `0xffeb00008071`
- **false 完整值 = 0x8041+0x20 = 0x8061** → 完整 `0xffeb00008061`

### ★ 疑问3+重大发现：f1028/f0ed0 = TRUE，不是 sentinel！
报告18 你说 `f1028=f0ed0=0xffeb00008071=sentinel`。**错了**——`0x8071 = null_base+0x30 = TRUE`！
→ **猫build(0xa52920)读的 singleton.field@0x1028 和 field@0xed0，两个都 = TRUE（bool=true 字段）！**
- 0xa52954 读 field@0x1028=TRUE，0xa52a98 读 field@0xed0=TRUE。
- 主控反汇编确认这俩是 `ldr x2,[sing,#off]; tbnz w0,#5/#4`（assert 风格类型检查 + 内容路径选择），不是 guard。
- **但证明了一点：单例里确实有 bool=true 字段（@0x1028/@0xed0），格式就是 `...8071`。isHungry 也是同格式，只是不同偏移。**

## 二、★ 决断扫描：全单例找所有 true 字段（…8071），isHungry 在其中

现在格式明确（true=`...8071`，false=`...8061`），isHungry=true（猫饿）藏单例某 true 字段。**全单例 0x000-0x2800 扫所有 8 字节字段，值以 `8071` 结尾（低16位）的就是 bool=true 字段**。

```javascript
Interceptor.attach(base.add(0xa52920), {
  onEnter: function(){
    var sing = this.context.x26.add(0x80).readPointer();
    try{
      var b = sing.readByteArray(0x2800);
      var a = new Uint8Array(b);
      console.log('[SCAN] singleton='+sing);
      for(var i=0; i+8<=a.length; i+=8){
        // 低2字节
        var lo = a[i] | (a[i+1]<<8);
        if(lo === 0x8071){
          console.log('  [TRUE] sing+0x'+i.toString(16)+' = 0x8071 (bool=true)');
        } else if(lo === 0x8061){
          console.log('  [FALSE] sing+0x'+i.toString(16)+' = 0x8061 (bool=false)');
        }
      }
    }catch(e){ console.log('err '+e); }
  }
});
```
报回：单例里**所有** true 字段偏移清单（…8071）。排除已知 @0x1028/@0xed0（这俩是猫build内容选择，非isHungry）。**剩下的 true 字段 = isHungry 候选。**

## 三、★ 锁定 isHungry：逐个 flip 验证

对每个候选 true 字段：runtime 写成 false（`0x8061`，完整 `0xffeb00008061`），触发 rebuild（切页/返回再进），看猫(0xa52920)是否停止 build/消失。
```javascript
// 对候选 sing+0xXXXX
sing.add(0xXXXX).writePointer(ptr('0xffeb00008061'));  // true->false
// 然后切页/返回再进触发 rebuild，看 0xa52920 是否还 HIT
```
**撞到让猫消失的 = isHungry**（flip 到 false = 不饿 = 不显）。

> 注：猫 build 自身读的 @0x1028/@0xed0 改了可能崩（build 内断言/内容选择），**只 flip 候选里非猫build-read 的字段**。isHungry 在 app 层（overlay 插入前），不在猫 build 内读。

## 四、锁定 → 抓 guard → 根除
- isHungry 字段锁定后，**MemoryAccessMonitor** 它，触发 reader rebuild，抓**读取 PC = guard**。
- guard 读 isHungry（true→饿→塞猫 overlay）。主控反汇编 guard 条件跳转 → on-disk patch（让 guard 恒判 false/不饿 → 永不塞猫）→ 固化 patch_libapp.py → LDPlayer(houdini)+redroid 通用。

## 五、最小回传
1. **全单例 true 字段清单**（…8071 偏移，排除 @0x1028/@0xed0）
2. **哪个 flip 到 false(…8061) 后猫消失** = isHungry
3. **MemoryAccessMonitor** isHungry 字段的 guard 读取 PC（libapp 偏移）

bool 格式已破解（true=`...8071`/false=`...8061`），全单例扫 true 字段必能锁定 isHungry。这是收尾——锁定字段后抓 guard，主控出最终 on-disk patch。

> 一句话：bool格式破解(true=null_base+0x30=`...8071`/false=`+0x20=`...8061`)。f1028/f0ed0=TRUE非sentinel(之前误判)。全单例扫所有`...8071`字段(排除@0x1028/@0xed0内容选择)→逐个flip到`...8061`→让猫消失=isHungry→MemoryAccessMonitor抓guard→on-disk patch根除。
