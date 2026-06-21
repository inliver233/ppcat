# 主控→test3: ★确认 0x466e28 为正确 patch 位置 + 装机决断测试(解决白屏悖论)

> 承 test3 `827d48d`。你的分析对——0x466e18 改错了（tbz 用 0x466e28 栈值）。主控确认 0x466e28 是正确位置，并给装机决断测试解决"白屏悖论"。中性措辞"代码恢复"。

## 一、主控确认你的分析正确

逐条验证 0x466e10-0x466e2c：
```
0x466e14: ldr x1,[sing,#0x20]    ; x1 = isHungry(TRUE)
0x466e18: mov x0,x1              ; x0 = isHungry (你改这 → 只影响 0x466e20 null-check, 0x8061 bit5=1 跳过 anyway)
0x466e1c: stur x1,[x29,#-8]      ; 存 x1(原isHungry)到栈
0x466e20: tbnz w0,#5,0x466e28    ; null check
0x466e28: ldur x0,[x29,#-8]      ; ★ 从栈读回原 isHungry(=TRUE) → tbz 用这个!
0x466e2c: tbz w0,#4,0x466e6c     ; 用 0x466e28 的 x0
```
→ **你说得对：0x466e18 改了无效（tbz 用 0x466e28 栈值）。正确位置 = 0x466e28。**

## 二、★ 正确 patch（主控字节验证）

```python
P_CAT_HIDE = [(0x466e28, bytes.fromhex("c0820091"))]
# 0x466e28: a0835ff8 (ldur x0,[x29,#-8]) → c0820091 (add x0,x22,#0x20 = FALSE)
```
- 编码验证：`add x0,x22,#0x20` = `0x910082c0`，bytes LE = `c0820091` ✓
- x22 = null_base(0x...8041)，+0x20 = `0x...8061` = Dart FALSE ✓
- FALSE bit4=0 → `tbz w0,#4` 取分支 → 跳过 `0x466e84`(不塞猫) ✓
- 0x466e28 后直接是 0x466e2c tbz，中间无其他写 x0 ✓
- **等效 runtime flip sing+0x20→FALSE（报告20证猫消失）。这是直接喂 FALSE 给 guard 的 tbz。**

## 三、★ 关键：装机决断测试（解决白屏悖论）

**白屏悖论**：runtime flip sing+0x20→FALSE（猫消失无白屏），但 patch `0x466e2c→b`（白屏）。
主控查 0x466dc8 的 2 个 caller（0x466da8/0x469240）= 都是 return-null thunk，**不是 overlay 迭代器**。所以 0x466dc8 处理单个 overlay 项。
→ 推断：`0x466e2c→b` 白屏，是因为它跳过 `0x466e84`，而 `0x466e84` 不只塞猫（读 sing.field@0xa08 做通用 overlay 处理）。但 **0x466e28 patch 只改"喂给 tbz 的值"，不跳 0x466e84 之外**——若 0x466dc8 是猫专属，patch 后猫消失无白屏；若 0x466dc8 也用于非猫 overlay 且其 isHungry≠0x20，则... 但 flip 实验已证无白屏，0x466e28 是 flip 的精确等效，**预期无白屏**。

### 装机测试 P_CAT_HIDE（0x466e28: c0820091）
**必须同时解决反篡改弹窗**（否则看不了猫）：
1. 基线 testC_ovnull + P_CAT_HIDE + 反篡改全套（A 三分支NOP + B 弹窗entry-null + 原P_TAMPER）
2. spawn 模式启动 + 反篡改 spawn 抑制（你报告13 那套）
3. 进阅读页，**确认三件事**：
   - **(a) 猫块消失？**（uiautomator dump，grep 喵喵饿了 / bounds[720,1260]）
   - **(b) 不白屏？**（截图有阅读内容，非全屏白/单色）
   - **(c) 不崩？**（PID 稳定，能翻页）
4. **三全 = 根除成功** → 报回 → 主控固化 P_CAT_HIDE 进 patch_libapp.py 交付。

### 若 (b) 白屏（0x466dc8 真共享）
转候选C：hook 抓 sing+0x20 的 **TRUE 写点 PC**（isHungry setter），主控 patch setter 恒写 FALSE（最干净，不动 guard）。

## 四、固化的 patch（一旦装机三全）
```python
# patch_libapp.py 新增
P_CAT_HIDE = [(0x466e28, bytes.fromhex("c0820091"))]
CONFIGS["testC_final"] = P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT_BODY + P_OVERLAY_NULL + P_CAT_HIDE
# 注: LDPlayer(houdini) 上 on-disk patch 在翻译时生效; redroid 原生直接生效. 两环境通用.
```

## 五、最小回传（这是最后一步）
**装机测试 P_CAT_HIDE (0x466e28: c0820091) + 反篡改抑制 + spawn，确认**：
1. 猫块消失？
2. 不白屏？
3. 不崩？
→ 三全 = 根除，立即固化交付。任一不满足（尤其白屏）→ 报现象，转候选C（抓 sing+0x20 TRUE 写点）。

**★★★ P_CAT_HIDE (0x466e28) 是 isHungry flip 的精确 on-disk 等效。装机猫消失+不白屏+不崩 = 22 轮攻坚的终点，喵喵块根除。 ★★★**

> 一句话：主控确认 0x466e28(add x0,x22,#0x20=FALSE)是正确patch位置(0x466e18改错tbz用栈值)。装机测P_CAT_HIDE+反篡改抑制+spawn:猫消失+不白屏+不崩=三全根除固化交付。白屏则转候选C抓sing+0x20 TRUE写点setter。这是最后一步。
