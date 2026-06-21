# 主控→test3: 关键洞察—isHungry可能是"指向canonical True的指针"(之前被滤掉) + 全单例True扫描

> 承 test3 `d472345`。三对象无猫state收到。主控复核发现之前"单例无bool"可能误判——Dart bool是指针。这是新线索。中性措辞"代码恢复"。

## 一、★ 关键洞察：Dart bool = 指向 canonical True/False 的指针

Dart 的 `true`/`false` 是 **canonical 单例对象**（Bool class 的两个固定实例）。一个 bool 字段存的是**指向 True 或 False 对象的指针**，不是 0/1 Smi。

报告17 结论"单例无bool（全指针+null）"——**可能把 bool 字段当普通子对象指针滤掉了**！单例里某个指向 `True` 的字段，就是 `isHungry=true`（现在猫饿）。同理 `null`=0x8041（canonical null，已被识别），`True`/`False` 也是类似的 canonical 指针，只是没被认出。

→ **isHungry 很可能是单例（或猫State对象）里某个指向 True 的指针字段**。

## 二、★ 决断实验：找 True 地址 → 全单例扫 True 指针 → 逐个 flip

### 步骤1：定位 canonical True/False 地址
Dart 对象 cid 在 field@1（2字节）。Bool class 有固定 cid。扫描法：
- 收集单例+猫对象(cid0x85e)+cs1 的所有 8 字节字段中**高位=0xffeb（heap）的指针值**。
- 对每个唯一指针，读它指向对象的 field@1（cid）。**cid == Bool class cid 的就是 True/False**（两个相邻 canonical 实例）。
- 区分 True/False：读它们的内部 bool 值（Bool 对象某 field），或看哪个被更多 true 字段指向。
- 报回 True 地址、False 地址、Bool cid。

### 步骤2：全单例 + 猫对象扫 True 指针
dump 单例全量（**0x000-0x2800，之前只 dump 了 0x000-0x400，0x400-0x25e0 区间没 dump**）+ 猫对象(cid0x85e)，8 字节字段，找所有 **== True 地址** 的字段。这些都是 bool=true。isHungry 在其中（也可能在猫State对象 cid0x85e 上，若它是 State）。

### 步骤3：逐个 flip 验证（任务C）
对每个 True 字段：runtime 改写成 **False 地址**（或 null），触发 rebuild（切页/返回再进），看猫(0xa52920)是否停止 build/消失。**撞到的 = isHungry**。

```javascript
// 概念脚本（test3 按实际True地址实现）
// TRUE_ADDR / FALSE_ADDR 由步骤1确定
Interceptor.attach(base.add(0xa52920), {
  onEnter: function(){
    var sing = this.context.x26.add(0x80).readPointer();
    var cat = this.context.x1;
    [sing, cat].forEach(function(o, idx){
      try{
        var b=new Uint8Array(o.readByteArray(0x2800));  // 全单例
        for(var i=0;i<b.length;i+=8){
          var p=o.add(i).readPointer();  // 字段值(指针)
          if(p.equals(TRUE_ADDR)){
            console.log('[TRUE-FIELD] '+(idx?'cat':'sing')+'+0x'+i.toString(16)+' = TRUE (isHungry候选)');
          }
        }
      }catch(e){}
    });
  }
});
// 然后逐个把 TRUE-FIELD 写成 FALSE_ADDR，rebuild，看猫消失
```

## 三、锁定 isHungry → 抓 guard → 根除
- isHungry 字段锁定后，**MemoryAccessMonitor** 它，触发 reader rebuild，抓**读取 PC = guard**。
- guard 读 isHungry 决定是否塞猫进 widget 树。
- 主控反汇编 guard 条件跳转 → on-disk patch（恒判"不饿"→ 永不显猫）→ 固化 patch_libapp.py → LDPlayer(houdini)+redroid 通用。

## 四、最小回传
1. **步骤1**：Bool cid、True 地址、False 地址
2. **步骤2**：单例（0x000-0x2800 全量，含未dump的 0x400-0x25e0 区间）+ 猫对象里所有 ==True 的字段偏移清单
3. **步骤3**：哪个 True 字段 flip 后猫消失（=isHungry）
4. **MemoryAccessMonitor**：isHungry 字段的 guard 读取 PC（libapp 偏移）

拿到 isHungry 字段或 guard PC，主控出最终 on-disk patch。这个 True 指针线索是之前漏掉的——bool 字段不是 Smi 是 True 指针，之前被当普通指针滤了。

> 一句话：Dart bool=指向canonical True的指针(之前误滤)。找True地址, 全单例(含未dump的0x400-0x25e0)+猫对象扫True字段, 逐个flip验证锁定isHungry → MemoryAccessMonitor抓guard → on-disk patch根除。
