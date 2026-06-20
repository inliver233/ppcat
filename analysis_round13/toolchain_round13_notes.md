# 第十三轮工具链与深挖记录（test1）

## 1. 本轮新增可用工具能力

- `jadx`：`analysis_round6/tools/jadx/bin/jadx --version` = `1.5.5`
- `apktool`：`java -jar analysis_round6/tools/apktool/apktool.jar --version` = `3.0.2`
- `rizin`：`analysis_round8/tools/bin/rizin -v` = `0.8.2`
- `Ghidra`：`analysis_round8/tools/ghidra_12.1.2_PUBLIC`
- `PyGhidra`：已在隔离环境 `.venv_pyghidra` 离线安装成功

安装命令：

```bash
python3 -m venv /root/ppcat_repo/.venv_pyghidra
source /root/ppcat_repo/.venv_pyghidra/bin/activate
python -m pip install --no-index \
  -f /root/ppcat_repo/analysis_round8/tools/ghidra_12.1.2_PUBLIC/Ghidra/Features/PyGhidra/pypkg/dist \
  pyghidra
```

验证结果：

```text
Successfully installed Jpype1-1.5.2 packaging-25.0 pyghidra-3.1.0
```

## 2. `unflutter` 针对 ppcat 的新增可用点

### 2.1 `doctor` 可直接识别 ppcat 快照

命令：

```bash
unflutter/unflutter doctor lib/arm64-v8a/libapp.so
```

结果：

```text
ELF:        OK (16352152 bytes)
Snapshot:   OK
Pointers:   compressed (4 bytes)
Support:    OK
```

### 2.2 `meta` 仍卡在 ObjectPool

命令：

```bash
unflutter/unflutter meta lib/arm64-v8a/libapp.so
```

结果：

```text
error: fill: fill: cluster 572 (ObjectPool): pool 0 entry 1:
unknown type 103 (bits=0x67 pos=0x2e0bfe)
```

这说明 `unflutter` 的通用 `meta` 流水线还未真正兼容 ppcat 的 ObjectPool。

### 2.3 `ppcat-prepool` 专用路径已能稳定跑通

命令：

```bash
cd unflutter
go run ./cmd/unflutter ppcat-prepool ../lib/arm64-v8a/libapp.so
```

结果：

```text
ppcat-prepool ok: strings=32135 named=22173 codes=31387 fill_start=0x2ff25
wrote ../lib/arm64-v8a/libapp.unflutter/ppcat-prepool
```

产物目录：

- `lib/arm64-v8a/libapp.unflutter/ppcat-prepool/summary.json`
- `lib/arm64-v8a/libapp.unflutter/ppcat-prepool/named.json`
- `lib/arm64-v8a/libapp.unflutter/ppcat-prepool/codes.json`
- `lib/arm64-v8a/libapp.unflutter/ppcat-prepool/focus_codes.json`

## 3. 对 `unflutter` 现有 ppcat 兼容状态的新判断

### 3.1 ObjectPool 前的 pre-pool 解析已经够稳定

`go test ./internal/cluster -run TestInspectPpcatPrePool -v` 输出：

```text
pre-pool parsed: strings=32135 named=22173 codes=31387 classes=5079 fields=1543 functypes=3615 pos=0x2e0bfb
```

这说明：

- pre-pool 的字符串、命名对象、Code、Class、Field、FunctionType 恢复已经能稳定工作；
- 当前真正阻塞的是 **进入 ObjectPool fill 的流位置 / 读法**，而不是前面所有 cluster 都错了。

### 3.2 关键字符串锚点的窗口扫描已被 `unflutter` 自带测试复现

`go test ./internal/cluster -run TestScanPpcatPoolTaggedWindows -v`

核心命中：

- `26842 @ rel 0x2e820c`
- `29112 @ rel 0x2e9ad5`
- `27673 @ rel 0x2ebb9a`
- `30922 @ rel 0x2ed0e5`
- `21707 @ rel 0x2f5951`
- `22466 @ rel 0x30292a`

这和 `test1/test3` 之前的人肉锚点完全同向。

### 3.3 当前 `ppcat-prepool` 导出的 `codes.json` 不能直接当 `.text` 映射用

原因：

- `TestExportPpcatCodeMap` 走的是 `ResolveCodeRangesFromTextOffset(res.Codes)`
- 导出的 `ppcat_code_map.txt` 命中了明显错误的大范围区间
- `ParseInstructionsTable` 在 `TestInspectPpcatPrePool` 中仍返回
  `instrtable: no instruction table data offset`

结论：

- 当前 `ppcat-prepool` 产物适合作为 `owner_ref / cluster_index / code_ref / named` 的辅助语义层
- 不适合直接替代 `test1` 现有的 `.text` 地址映射体系

## 4. Ghidra / Reward / VIP 的本轮新结果

### 4.1 `RewardProbe` 继续支持 reward anti-cheat 主结论

`RewardProbe.java` 仍能稳定恢复：

- `0x875efc: TBNZ W0,#4 -> 0x875f24`
- 不跳转时会走 `0x875f18 -> BL 0x875f78`
- `0x875f78` 是独立的 reward fallback / anti-cheat handler

本轮没有推翻 `0x875efc` 这条关键分支的既有判断。

### 4.2 `VipDeepProbe` 再次证明 `0xa54178` 很薄，`0xb9fc84` 才是核心状态机

`VipDeepProbe` 的结果里：

- `0xa54178` 仍表现为一个薄包装函数
- `0xb9fc84` 仍是大体量、强状态化的主逻辑区

这继续支持 `test1` 现有结论：

- 不该继续把 `0xa54178` 当成“单点 VIP 判定函数”
- 真正值得继续拆的是 `0xb9fc84 / 0x911788 / 0x8cf36c`

### 4.3 `unflutter_prescript.py` 不能直接喂给 `analyzeHeadless`

尝试：

```bash
analyzeHeadless ... -preScript /root/ppcat_repo/unflutter/ghidra_scripts/unflutter_prescript.py
```

结果：

```text
Ghidra was not started with PyGhidra. Python is not available
```

含义：

- 这不是脚本逻辑错误
- 而是 `AnalyzeHeadless` 本身并不会自动启 PyGhidra 的 Python provider
- 要走这条线，需要改成 `pyghidraRun -H` 或 Java 版 pre-script

## 5. PyGhidra 的当前状态

### 5.1 已证明可用

脚本：

- `analysis_round13/pyghidra_probe.py`

已验证：

- 能在 `.venv_pyghidra` 中启动
- 能打开 `libapp.so`
- 能读到 `currentProgram`

当前输出：

```text
program=libapp.so
image_base=0x100000
target=0x8758bc fn=None ins=None
target=0x911788 fn=None ins=None
target=0x8cf36c fn=None ins=None
target=0xa54178 fn=None ins=None
target=0xb9fc84 fn=None ins=None
```

原因不是 PyGhidra 不可用，而是：

- 现在脚本还只是在普通 `open_program()` 里看默认分析结果
- 还没有在 Python 里主动 `createFunction / disassemble / decompile`

### 5.2 下一步明确

优先继续两件事：

1. 把 `pyghidra_probe.py` 升级成：
   - 指定地址 `disassemble`
   - `createFunction`
   - `DecompInterface.decompileFunction`
2. 如果这条链稳定，再替代当前部分 Java Ghidra 探针

### 5.3 已用 `PyGhidra` 跑通定向反编译闭环

本轮已经把上面的“下一步”真正落成了可复用脚本：

- `analysis_round13/pyghidra_targeted_decompile.py`
- `analysis_round13/pyghidra_targeted_decompile.txt`

脚本做的事情很直接：

- `pyghidra.open_program(...)` 打开 `libapp.so`
- 对已知区间手工 `disassemble`
- 用 `listing.createFunction(..., AddressSet body, USER_DEFINED)` 显式建函数
- 再用 `DecompInterface.decompileFunction(...)` 导出伪代码

当前已覆盖的 5 个目标：

- `0x8758bc .. 0x876154`
- `0x911788 .. 0x911b28`
- `0x8cf36c .. 0x8cf8f0`
- `0xa54178 .. 0xa56824`
- `0xb9fc84 .. 0xba46ec`

已确认的事实：

- 5 个目标全部 `decompile_completed=True`
- `PyGhidra` 这条链不再只停留在“能打开 program”，而是已经能完整跑到“手工建函数 + 反编译”
- 语义层面没有推翻现有结论，反而再次支持：
  - `0xa54178` 仍然很薄，更像页面装配 wrapper
  - `0xb9fc84` 仍然是厚状态机
  - `0x911788 / 0x8cf36c` 的伪代码仍带大量 AOT 运行时噪音，说明它们更适合继续配合 `pool_accesses + Capstone + 对象池` 去拆，而不是直接依赖反编译伪代码

这条链对协作的实际意义是：

- 后续不必再完全依赖 Java 版 `GhidraScript`
- 其他分支如果需要复用 `test1` 的环境成果，现在可以直接基于这份 Python 脚本扩展目标区间
- `PyGhidra` 已经从“工具安装记录”升级成了 `test1` 分支上可直接复跑的共享分析入口

## 6. 本轮最有价值的结论

- 新工具不是停留在“装好了”：
  - `PyGhidra` 已本地落地
  - `unflutter ppcat-prepool` 已成功跑通
  - `RewardProbe/VipDeepProbe` 继续给出有效窗口
- `unflutter meta` 当前真正卡点已缩到：
  - `cluster 572 ObjectPool`
  - `unknown type 103 @ 0x2e0bfe`
- `VIP` 线没有被新工具推翻，反而再次支持：
  - `0xa54178` 不是单点 VIP 函数
  - `0xb9fc84 / 0x911788 / 0x8cf36c` 才是应继续投入的三层
