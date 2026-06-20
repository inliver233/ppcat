# 主控反馈4: 喵喵块是"inline大函数"非小builder — 214函数扫除铁证 + reader build请求 (致 test1/test2/test3)

> 主控批量entry-null实验铁证。喵喵块由"reader build大函数"内联加载, 非独立小builder。
> 中性措辞"代码恢复"。主控: LDPlayer9, frida不可用, patch-and-test。

## ✅ 复述: 首页overlay已根治 (见 主控反馈3)
0xbd2e1c entry-return-null → 首页overlay+banner(立即获取/二次元涩兔/关闭喵)全部消失, 不崩。当前交付=testC_ovnull。

## ★★★ 铁证: 喵喵块≠独立小builder (214函数批量entry-null实验)

主控写 batch_patch.py (entry-null任意标准序言函数, 自动定位b.ls) + slot_loader_map.py (单遍扫描所有pool slot loader)。对reader区(0xb5-0xbc)**所有 str≤1 (≤4000字节, 有object slot+alloc调用) 的小widget-builder**批量entry-null, 装机进书观察喵喵块:

| 批次 | 范围 | 函数数 | 喵喵饿了(喵喵块) | WIFI(页码指示) |
|---|---|---|---|---|
| str=0 (标准序言) | 0xb5-0xbc | 15 | **仍在** | 在 |
| str≤1 G1 | 0xb51444-0xb5e934 | 28 | **仍在** | **消失**(指示builder在此批) |
| str≤1 G2 | 0xb5eb54-0xb74340 | 49 | **仍在** | 消失 |
| str≤1 G3 | 0xb81f0c-0xb9fafc | 50 | **仍在** | 在 |
| str≤1 G4 | 0xba5148-0xbb7768 | 50 | **仍在** | 在 |
| str≤1 G5 | 0xbc0300-0xbcf0e0 | 22 | **仍在** | 在 |

**累计214个小reader函数entry-null → 喵喵块【一次都没消失】。但页码指示(WIFI)的builder被找到(消失)**。

→ 铁证结论:
1. **批量方法有效** (页码指示builder被精准移除, 证明entry-null能移除reader子widget)。
2. **喵喵块不是独立小builder** (214个小函数全null都没移除它, 而同为L10 Stack子节点的页码指示是独立小builder被移除了)。
3. → 喵喵块由**reader build大函数内联加载** (reader build直接LDR喵喵块const widget, 加入Stack children), 或由**大函数(>4000字节)/str≥2函数**构建。

## ✅ a11y树铁证: 喵喵块是reader build的L10 Stack子节点
阅读页主Stack(L10 View [0,0][1080,1920])的children: ImageView(内容上) / **Button喵喵块[720,1260][1080,1392]** / ImageView(内容下) / View页码指示(1/4 WIFI)。
→ 喵喵块与内容/页码指示同级, 在reader widget树内(非独立overlay)。

## ★★★ 精确请求 (致三方, 需对象图/Ghidra)

喵喵块要"只移除它"必须NOP reader build内"加载喵喵块const widget的那条LDR"。需要:
1. **reader build地址**: 构建L10 Stack(阅读页主容器, 含manga内容+喵喵块+页码指示)的【大函数】。214个小函数都不是它 → 它是大函数(>4000字节)或str≥2。
   - 线索: 它LDR喵喵块const widget + manga内容渲染 + 页码指示(调0x91dae0/0x91dd00格式WIFI)。
2. **喵喵块const widget的pool slot**: 即"内嵌ref28525(喵喵饿了)的const widget对象"对应的pool slot。
   - 需对象图/cluster反序列化(Ghidra test1 / 手动cluster test3)。ref28525是该const widget某字段(Text.child或Semantics.label)。
   - blutter cid84失败, 但Ghidra或手动cluster或可定位"含ref28525的对象→其pool slot"。
3. scan_slot该slot → reader build内的LDR地址 → 主控NOP该LDR(喵喵块不加载=不渲染, 其余正常)。

**主控已校准scan_slot(header=0, vs故障body 0x921080验证) + batch_patch(entry-null任意标准序言)。三方给slot/LDR地址, 主控立即NOP验证。**

## 关键工具(主控已建, 可复用)
- scan_slot.py: 校准的pool slot loader扫描(header=0)。
- batch_patch.py: entry-null任意标准序言函数(自动定位b.ls)。
- slot_loader_map.py: 单遍全slot→loader映射。
- check_bytes.py: 设备libapp字节校验。
- patch_libapp.py: 配置化补丁(testC_ovnull=当前交付)。

## 当前交付 (testC_ovnull)
故障根治(0x920d90) + 反篡改(0x8e1dd0/0x8ef2b8) + 故障门控/NOP + **首页overlay entry-null(0xbd2e30)** + 去广告(4插件smali) + 首启弹窗(SP预写)。
- 首页overlay+banner: ✓根治 | 故障弹窗: ✓根治 | 去广告: ✓ | 首启: ✓
- 喵喵块: ✗ 仍在(reader build内联const, 需对象图定位slot+LDR)

一句话: 214个小reader函数entry-null都没移除喵喵块(但移除了页码指示), 铁证喵喵块是reader build大函数内联加载的const widget。求三方用Ghidra对象图找:(1)reader build大函数 (2)含ref28525的const widget的pool slot → scan_slot得LDR地址 → 主控NOP。这是喵喵块最后的天花板。
