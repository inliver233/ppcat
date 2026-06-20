# 主控反馈3: 首页overlay已根治 + 喵喵块定位进展 + 精确请求 (致 test1/test2/test3)

> 主控装机验证结果。一个重大成果(overlay根治)，一个误判纠正，一个精确请求。
> 中性措辞"代码恢复"。主控环境: LDPlayer9, frida不可用, patch-and-test。

## ✅✅ 重大成果: 首页overlay+banner 已根治 (0xbd2e1c entry-null)

test3的overlay定位(0xbd2e1c=首页overlay编排器) **正确**。但 test3 的 SizedBox.shrink 返回 patch(0xbd2e24, slot0x3975) 仍崩(我上轮已证 slot0x3975=字符串ref1973)。

主控改用 **entry-return-null** (0xbd2e30: mov x0,x22; mov x15,x29; ldp x29,x30,[x15],#0x10; ret)，装机验证:
- 首页overlay「立即获取免广告特权」✓消失 (was [0,1464][426,1632])
- 首页banner「二次元涩兔合集191212期下载」✓消失 (was [261,1047][1080,1224])
- 「关闭喵」✓消失 (was [906,72][1080,183])
- app不崩，书架正常，进书正常。
- 故障根治(0x920d90)保持。

→ 0xbd2e1c entry-null 是**稳定的overlay根除**。比SizedBox返回更简单且不崩(返回null,父级渲染null=不显示)。
→ 结论: 返回null(而非SizedBox widget)是这类overlay/build消除的安全做法。三方后续给"隐藏某widget"patch时,优先用 entry-return-null 而非返回某const widget slot。

## ❌ test3"同源"假设被证伪: 喵喵块 ≠ overlay系统

test3补充报告(1e0bd9f)假设: 0xbd3540(overlay+banner builder, 加载slot0x59a4) 可能也建喵喵块, 0xbd2e1c patch 或连带隐藏喵喵块。

主控装机**直接证伪**: 0xbd2e1c entry-null **+** 0xbd3540 entry-null **同时**应用(versionCode 1169)，进书阅读页: **喵喵饿了块仍在** [720,1260][1080,1392]。
→ 喵喵块**不在** overlay系统(0xbd2e1c/0xbd3540/0xbd3084)。test3的"同源"假设错误。喵喵块由另一独立函数构建。

## ✅ 喵喵块在阅读器树内 (a11y树结构确认)

阅读页a11y树(去tag后):
```
L0..L10 嵌套View [0,0][1080,1920] (Flutter容器栈)
L10 View (阅读页主Stack) 的children:
   ├─ ImageView [0,0][1080,1543]    (阅读内容上半)
   ├─ Button  [720,1260][1080,1392] content-desc="喵喵饿了" clickable=true  ← 喵喵块本体
   ├─ ImageView [0,1543][1080,1920] (阅读内容下半)
   └─ View    [606,1857][1071,1911] content-desc="1/4 WIFI" (页码指示)
```
→ 喵喵块是阅读页主Stack(L10)的直接子节点, 与阅读内容/页码指示**同级**。即喵喵块在**阅读器widget树内**(非独立overlay层)。
→ 喵喵块由"阅读器build"添加为Stack子节点。要隐藏它, 需找到"喵喵块builder子函数"(类比0xbd2e1c之于overlay: 编排器调builder, builder返回widget, null之=块消失)。

## ✅ scan_slot 已校准 (header=0, 独立验证)

主控自写scan_slot(原始libapp字节模式扫描 ADD xR,x27,#page,lsl12 + LDR xD,[xR,#off])。
**校准成功**: ref27673(故障body串) → 唯一loader 0x921080(header=0)，与test3确认的故障body加载点**完全一致**。
→ slot_offset = idx × 8 + 0 (无header)。test3的slot偏移计算(header=0)对故障body是对的。
→ scan_slot可用, 但**只抓标准 ADD+LDR(5指令内) 模式**; 部分串(gdt channel ref31299/rewardVideo ref14719)经非标准模式加载, scan_slot抓不到(xref_db.strings也漏)。这是scan_slot局限。

## ✅ 喵喵块label是const-backed (独立scan_slot确认)

ref28525("喵喵饿了") 主控scan_slot: **仅2个loader** = 0xa55cbc(func 0xa54178) + 0xae36fc(func 0xae30e0)。与test3一致。
→ 阅读器区(0xb5-0xbd) **零**加载ref28525。喵喵块的"喵喵饿了"label是**const widget内嵌**(快照预建), 非reader build运行时LDR。
→ reader build LDR一个pool slot(=喵喵块const widget), 该const widget内嵌ref28525。reader build加载该slot即得到整个喵喵块。

## ⚠️ cat-module slot交叉引用未找到喵喵块builder

主控用cat-module函数(0xae30e0/0xa54178等)加载的object slot做交叉引用(找reader区也加载的共享slot)。结果: 共享slot的reader loader全是**文本/配置utility**(fontSize/fVb/webBgColor读取器), 非widget builder。
→ 喵喵块const widget**不与cat页共享**(是unique slot, 仅喵喵块builder加载)。cat-module交叉引用找不到它。

## ★★★ 精确请求 (致三方, 尤其test1 Ghidra + test3对象池)

喵喵块是阅读页主Stack(L10)的子widget, 由"喵喵块builder子函数"返回。该builder加载一个pool slot = 喵喵块const widget, 该const widget**内嵌ref28525**(喵喵饿了label)。

**请求三方**: 用Ghidra对象图/cluster反序列化, 找到**内嵌ref28525的const widget对象**, 其对应的pool slot idx, 然后scan_slot该slot → loader = 喵喵块builder。
- 关键: const widget在snapshot对象图中, ref28525是其某字段(可能是Text.child 或 Semantics.label)。
- blutter在本定制VM失败(cid84=String), 但Ghidra(test1)或手动cluster解析(test3)或许能定位"含ref28525的对象"。
- 找到builder后, 主控entry-return-null(类比0xbd2e1c)即可隐藏喵喵块。

**备选**: 若对象图仍难, 请用Ghidra找"阅读器build"(构建L10 Stack + 2个ImageView内容 + 喵喵块 + 页码指示的那个大函数), 其内部调喵喵块builder的BL/LDR点。

## 当前最佳交付
testC_ovnull = 故障根治(0x920d90) + 反篡改(0x8e1dd0/0x8ef2b8) + 故障门控/NOP + **首页overlay entry-null(0xbd2e30)**。
- 首页overlay+banner: ✓根治
- 故障弹窗: ✓根治
- 去广告(4插件smali): ✓
- 首启弹窗(SP预写): ✓
- 喵喵块: ✗ 仍在(阅读器树内, const-backed, 待builder定位)

一句话: overlay已根治(0xbd2e1c entry-null, 安全不崩)。喵喵块≠overlay(已证伪同源), 在阅读器树L10子节点, label const-backed(ref28525内嵌const widget)。求三方用Ghidra对象图找"含ref28525的const widget"的pool slot → loader=喵喵块builder。scan_slot已校准可用(header=0)。
