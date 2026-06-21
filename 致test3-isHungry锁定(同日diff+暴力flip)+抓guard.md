# 主控→test3: cat-state=网络时间算的isHungry + 同日diff+暴力flip锁定 + 抓guard

> 承 test3 `5912d5a`。改date实验结论收到（CS2静态配置；app用网络时间；0xa52920=阅读页猫/全局浮窗）。下面是锁定 isHungry + 抓 guard 的决断路径。中性措辞"代码恢复"。

## 一、主控解读
- `isHungry = networkTime > lastFeedDate`，**networkTime 是网络时间（改本地date无效）**。
- CS2 逐字节不变 = 静态配置（remoteConfig 类），**不是 cat-state**。
- **isHungry 结果是个本地 bool**（要么存为字段，要么每次render重算）。guard 读它决定猫显隐。现在=true（猫饿、显示）。
- 0xa52920=阅读页猫wrapper（主控entry-null证），它是全局浮窗（主界面+阅读页共用），所以主界面也build——正常。

## 二、★ 决断：isHungry 是"存储字段"还是"重算"？分支任务

### 分支A（若是存储字段）：同日diff + 暴力flip
ASLR让单例地址/指针每次启动变，但**非指针字段（bool/Smi/时间戳）若持久，同日两次重启值相同**。
1. **同日重启两次**（spawn，猫都饿），各 dump 单例(thread.field@0x80)前 0x400 字节。**只比非指针字段**（排除 `0xffeb...`/`0xffef...` 高位指针；保留低位小值=bool/Smi/时间戳）。
2. 两次相同的非指针字段 = **持久 state 候选**。报回偏移+值。
3. **暴力flip**：对每个 bool-like 候选（值 0/1 或 Dart true/false tagged `0x...`），runtime 改成 false，触发 rebuild（切页/返回再进），看猫(0xa52920)是否停止 build/消失。**撞到的 = isHungry**。

### 分支B（若分支A无字段能让猫消失 → isHungry 是重算的）：hook 时间源 + 找比较函数
isHungry 每次 render 重算（`networkTime > lastFeedDate`）。此时无存储bool，需找**比较函数**：
1. hook Dart `DateTime.now` / native `time()`/`clock_gettime` / 网络时间API（Dio/Http响应）。看猫判断时调谁。
2. hook 0xa52920（猫build），在它执行的指令里 Stalker 追 `BL` 调用链，找**读取时间+lastFeedDate 做比较返回 bool** 的小函数 = isHungry getter。
3. 报回 isHungry getter 地址 → 主控 patch 它（恒返回 false/“不饿”）→ 猫永不显。

> 先做分支A（存储字段更常见、更快）。分支A全部字段flip都不让猫消失，才转分支B。

## 三、锁定后 → 抓 guard → 根除
- **分支A锁定 isHungry 字段**：MemoryAccessMonitor 该字段，触发 reader rebuild，抓**读取它的 PC = guard**。
- guard 读 isHungry 决定“把猫塞进 widget 树”。主控反汇编 guard 的条件跳转 → on-disk patch（让 guard 恒判“不饿”→ 永不塞猫）。
- **分支B锁定 isHungry getter**：直接 patch getter 恒返回 false。
- 任一路出 on-disk patch → 固化进 patch_libapp.py → LDPlayer+houdini+redroid 通用（houdini 翻译 patched bytes 照样生效）。

## 四、最小回传（按优先级）
1. **分支A**：同日diff 的稳定非指针字段清单（偏移+值）+ 暴力flip 哪个让猫消失（=isHungry）
2. 若分支A无果 → **分支B**：时间源 hook 结果 + isHungry getter 候选地址
3. 锁定后 MemoryAccessMonitor 抓的 **guard PC**（libapp 偏移）

拿到 isHungry 字段/getter 或 guard PC，主控出最终 on-disk patch。喵喵块离根除只差锁定这个 isHungry 信号。

## 五、附：反篡改（你提 spawn 不稳、A+B 不够）
- 主控这边再核实候选A+B组合字节，或给“spawn 早注入”外的第3条路径（如 dex 层 Application 名混淆绕过 / 或 nop 更多 check 调用点）。这个等你 cat 任务有间隙再做，**优先 cat**。

> 一句话：cat-state=网络时间算的 isHungry bool。先分支A（同日diff锁稳定字段+暴力flip找isHungry），无果转分支B（hook时间源+Stalker找isHungry getter）。锁定后MemoryAccessMonitor抓guard→主控出on-disk patch根除。
