# 主控→test3: 0x466e84分析结论 + 精确patch候选(复现flip无白屏)

> 承 test3 `d481839`。guard=0x466e2c 定位对，但 0x466e2c改b 白屏——主控反汇编 0x466e84 找到原因，给精确patch候选。中性措辞"代码恢复"。

## 一、主控反汇编 0x466e84 结论：它不是"塞猫"，是共享 overlay 路径
```
0x466e84: 读 sing.field@0xa08 (另一个overlay状态/列表)
          cmp w0,w22; b.eq 0x466ed0 (空→建新)
          否则 blr [x0,#0x1f] (虚方法调用)
```
→ **0x466e84 是通用 overlay/通知 处理**（读 sing.field@0xa08），不只塞猫。所以 `0x466e2c 改b（恒跳0x466e84）` = 跳过所有 overlay → 白屏。**白屏根因：0x466e2c 改b 破坏了共享路径。**

## 二、★ 关键矛盾 + 正解
你 runtime flip `sing+0x20`→FALSE：**猫消失、无白屏**。
但 patch `0x466e2c`→b：**白屏**。
→ 说明：`sing+0x20` 是**猫项自己的标志**（每个 overlay 项有自己的 isHungry 标志？），flip 它只让猫项不饿。而 `0x466e2c改b` 对所有项都跳 0x466e84 → 全 overlay 丢 → 白屏。
→ **正解 = 只让"读 sing+0x20"这一站恒得 FALSE（复现 flip），不动 tbz 本身、不跳 0x466e84。**

## 三、★ 精确patch候选（请你装机验证）

### 候选A（最接近 flip）：0x466e18 改成 movz w0,#0
```
0x466e18: 原 e00301aa (mov x0,x1, x0=从x1读的isHungry)
        → 新 52800000 (movz w0,#0, x0=0)
效果: tbz w0,#4 @0x466e2c，bit4=0 → 恒跳过(不调0x466e84)。等同 w0=FALSE。
```
**风险**: 若 0x466dc8 对非猫 overlay 项也跑，且那些项也靠 w0 控制，会让它们也跳（可能白屏，和改b同效）。**需你装机验证：猫消失+不白屏 = 成功；白屏 = 此候选也共享，转候选B。**

### 候选B（最稳，复现 flip）：改 0x466e14 的 ldr，让 sing+0x20 读不到 TRUE
更精确：让"读 isHungry"恒返回 FALSE 对象，但保留其他逻辑。但静态难单点。
**更稳的是回到 flip 等效**：既然 flip sing+0x20→FALSE 猫消失无白屏，**on-disk 等效 = 找 isHungry 的初始化/赋值点，强制写 FALSE**。
- isHungry 写点（主控扫到 5 个 str [#0x20]）：0x46238c/0x46242c(写x26+0x20) / 0x466f48/0x466f64/0x466fb8(写x1/x3+0x20，在0x466f28)。
- **0x466f28 反汇编**：`add x0,x22,#0x20(FALSE); str x0,[x1,#0x20]` —— 这正是"写isHungry=FALSE"的setter！
- 但 sing+0x20 的 TRUE 初始值在哪 set？需你 runtime hook 0x466e14（读 sing+0x20）确认**谁写 TRUE 进 sing+0x20**（喂食逻辑/network 时间算完写的）。找到 TRUE 写点 → NOP/改FALSE → 恒不饿。

### 候选C（动态验证后静态）：hook 找 sing+0x20 的 TRUE 写点
```javascript
// 监控 sing+0x20 被写的瞬间，抓 PC
// frida 在 sing+0x20 设写断点(HardwareBreakpoint write)，抓 PC = isHungry 的 setter
```
setter PC → 主控反汇编它（网络时间算完→ if(饿) write TRUE）→ patch 成恒写 FALSE。这是最干净的 on-disk（不动 guard，动 setter）。

## 四、最小回传（这是最后一步）
1. **候选A 装机**：0x466e18: e00301aa→52800000。猫消失+不白屏=成功（直接固化）；白屏=转候选C。
2. **候选C（若A白屏）**：hook 找 sing+0x20 的 **TRUE 写点 PC**（libapp 偏移）→ 主控反汇编 setter 出 patch（恒写FALSE）。

**逻辑链**：isHungry=sing+0x20 已锁 + flip→猫消失已证。0x466e2c改b白屏是因0x466e84共享。精确解=只让 isHungry 读取/写入恒FALSE（复现flip）。候选A是单点等效；候选C是setter根治。**任一装机猫消失+不白屏=根除成功，固化patch_libapp.py。**

> 一句话：0x466e84=共享overlay(读sing+0xa08)，故0x466e2c改b白屏。精确解=只让isHungry(sing+0x20)读取恒FALSE(复现flip)。候选A:0x466e18 movz w0,#0(装机验猫消+不白屏)。候选C:hook抓sing+0x20的TRUE写点→patch setter恒写FALSE。这是最后一步。
