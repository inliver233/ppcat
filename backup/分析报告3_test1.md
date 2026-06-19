# 皮皮喵 Flutter / DEX 静态分析报告3

> 第三轮目标是收口 `任务文档3.md`：优先尝试对象池完整反序列化；若仍受定制 VM 阻塞，则至少完成 `导入书源 bug(C)` 与 `故障窗 caller/分支(A)` 这两个独立子任务。

## 1. 本轮结论摘要

- **核心对象池完整反序列化仍未打通。**
  - `unflutter` 能给出 `snapshot.json`、`ref -> string`，但没有现成的 `Code 对象 -> pool slot -> .text -> caller` 导出。
  - `blutter` 仍卡在定制 Dart 2.19 VM 的反序列化差异，无法生成可信的 Code/ObjectPool 映射。
  - 因此第三轮的“完整映射表”未完成，`ppcat_code_map.txt` 一类产物不可采信。
- **任务 C（导入书源 ANR）已收口到可执行的字节级修复点。**
  - 根因不是字面上的 `L了/了;->了`。
  - 真正的坏点在 `classes2.dex` 的 Flutter `MethodChannel` 混淆类里：同名字段 `ۥ้้۟۟ۡ` 存在两个 `field_id`，其中一个是**不存在于 class_def 中的假 String 字段引用**。
  - `MethodChannel$Result` 风格的内部回调构造器在日志路径里错误读取了这个假字段，运行时会触发 `NoSuchFieldError` 形态的 field 解析失败。
- **任务 A（故障窗）目前只能给出高置信候选，不足以给出“已证实最终 patch 点”。**
  - `0x00bbc22c` 已确认只是正文 Text builder。
  - `0x00bbec34` 虽然像 dialog 编排器，但它加载的是篡改窗字符串簇 `0xad90/0xad88`，不应再作为故障窗 patch 点。
  - `0x00bc0f40` 是当前最强的故障窗上层候选；其分支 `0x00bc1020` 是高置信门控点，但还没有拿到 `0xbbc22c` 的直接 caller 证明。
- **任务 D（VIP/更新）仅复核了旧地址上下文，未完成命名级确认。**

## 2. 证据与方法

- AOT 侧主要使用：
  - `unflutter_dump/asm.txt`
  - `unflutter_dump/snapshot.json`
  - `origin/test2:analysis_workdir/output/function_summary.txt`
  - `origin/test2:analysis_workdir/pool_accesses.txt`
- DEX 侧主要使用：
  - `main_dex/classes2.dex`
  - `tools/dex_probe.py`
  - `androguard.core.dex.DEX` + `Analysis`
- 地址约定：
  - 本样本中 `vaddr == file offset`

## 3. 核心任务状态：对象池完整反序列化

### 3.1 当前可确认内容

- `unflutter_dump/snapshot.json` 已确认：
  - `version.CIDs.String = 84`
  - `version.CIDs.Code = 17`
  - `version.CIDs.ObjectPool = 21`
  - `version.OldPoolFormat = true`
- 已验证锚点仍成立：
  - `ref=30922` 长版篡改正文 -> `slot 0x17168`
  - `ref=27673` 故障窗正文 -> `slot 0x13c68`
  - `slot 0x17168` 的已知 `.text` xref 在 `0x8e52d0/0x8ef414`
  - `slot 0x13c68` 的已知 `.text` xref 在 `0xbbc31c`

### 3.2 为什么本轮仍未完成完整 Code 映射表

- `symbols.json` 只有两条顶层区段记录，不含函数级符号。
- `unflutter` 当前产物没有导出 `Code object -> instructions entry` 表。
- 自行从 snapshot 反序列化 `ObjectPool/Code` 仍受定制 VM 差异影响：
  - 旧 pool 格式存在多种 entry type；
  - 当前仅能稳定追踪字符串 `slot -> .text`，不能稳定追出 `Code slot -> entry -> caller`。
- 因此本轮不能诚实地给出“完整核心映射表”，只能保留为后续待攻关项。

## 4. 任务 A：故障窗（广告失败提示）定位

### 4.1 已确认事实

- 故障窗正文 `ref=27673` -> `slot 0x13c68`
- 已确认 `.text` 加载点：
  - `0x00bbc31c`，所在函数 `0x00bbc22c`
  - `0x00913d3c`，所在函数 `0x00913bf8`
- 其中 `0x00913bf8` 已知是“加载 22 个杂字符串的列表构建器”，**不能 patch**。
- `0x00bbc22c` 反汇编片段：

```asm
0x00bbc310  5f 00 16 6b  CMP W2, W22
0x00bbc314  00 0b 00 54  B EQ, .+0x160
0x00bbc318  70 4f 40 91  ADD X16, X27, #0x13, LSL #12
0x00bbc31c  10 36 46 f9  LDR X16, [X16,#3176]   ; slot 0x13c68
0x00bbc320  f0 09 bf a9  STP X16, X2, [X15,#-16]!
0x00bbc328  ce 23 f5 97  BL .+0xffffffffffd48f38
```

结论：`0x00bbc22c` 是**正文 Text widget builder**，不是完整 showDialog 编排器。

### 4.2 direct caller 检查结果

- 对完整 `asm.txt` 重新生成 `BL calls (from -> to)` 后，**没有任何 direct `BL -> 0x00bbc22c`**。
- 这说明 `0x00bbc22c` 更像被闭包 / framework 间接 `BLR` 调度的 builder，而非普通 direct-call 函数。

### 4.3 候选上层函数对比

#### 候选 1：`0x00bbec34`

- 规模：`size=596 / instrs=149 / pool=4 / bl=17 / cond=6 / cmp=5`
- 关键分支：

```asm
0x00bbece0  60 13 41 91  ADD X0, X27, #0x44, LSL #12
0x00bbece4  00 cc 46 f9  LDR X0, [X0,#3480]   ; slot 0x044d98
0x00bbece8  eb 0d 0f 94  BL .+0x3c37ac
0x00bbecec  a0 83 1e f8  STUR X0, [X29,#-24]
0x00bbecf0  1f 00 16 6b  CMP W0, W22
0x00bbecf4  60 0c 00 54  B EQ, .+0x18c
```

- 但该函数后续还加载：
  - `slot 0x00ad90` at `0x00bbedfc`
  - `slot 0x00ad88` at `0x00bbee5c`
- `0x00ad90 / 0x00ad88` 已知分别对应篡改窗标题与短版正文簇。
- **因此 `0x00bbec34` 不应再作为故障窗 patch 点，它更接近篡改窗相关编排器。**

#### 候选 2：`0x00bc0f40`

- 规模：`size=828 / instrs=207 / pool=5 / bl=16 / cond=15 / cmp=14`
- 第一处门控：

```asm
0x00bc1010  60 93 40 91  ADD X0, X27, #0x24, LSL #12
0x00bc1014  00 68 44 f9  LDR X0, [X0,#2256]   ; slot 0x0248d0
0x00bc1018  1f 05 0f 94  BL .+0x3c147c
0x00bc101c  1f 00 16 6b  CMP W0, W22
0x00bc1020  a0 12 00 54  B EQ, .+0x254
```

- 第二处字符串/对象分支：

```asm
0x00bc1090  00 fc 47 f9  LDR X0, [X0,#4088]
0x00bc1098  1f 00 10 6b  CMP W0, W16
0x00bc10a8  81 00 00 54  B NE, .+0x10
0x00bc10ac  60 4f 40 91  ADD X0, X27, #0x13, LSL #12
0x00bc10b0  00 a4 46 f9  LDR X0, [X0,#3400]   ; slot 0x013d48
0x00bc10b4  f8 04 0f 94  BL .+0x3c13e0
```

- 当前判断：
  - `0x00bc0f40` 是**故障窗上层候选中最强的一支**。
  - `0x00bc1020` 是**高置信条件门控分支**。
  - 但由于没有 direct caller / 命名映射，仍不能把它写成“最终已证实 patch 点”。

### 4.4 本轮对故障窗的可交付结论

- **已证实：**
  - `0x00bbc22c` = 故障窗正文 builder
  - `0x00913bf8` 不是故障窗，不可 patch
- **高置信候选：**
  - 上层编排器候选：`0x00bc0f40`
  - 条件分支候选：`0x00bc1020`
  - 分支前比较：`0x00bc101c  CMP W0, W22`
  - 机器码：
    - `0x00bc101c`: `1f 00 16 6b`
    - `0x00bc1020`: `a0 12 00 54`

## 5. 任务 C：导入书源报错 / ANR

### 5.1 根因修正

前几轮文档中的报错外观是：

```text
No field 了 of type Ljava/lang/String; in class L了/了;
```

本轮确认这不是应继续追踪的真实 DEX 类名，而是混淆/编码后的报错外观。真实坏点位于 Flutter Java 层 `MethodChannel` 混淆类：

- `Lสۥ۠ۦۡ/สۥ۟۟۠;` = `MethodChannel`
- `Lสۥ۠ۦۡ/สۥ۟۠ۢ;` = `BinaryMessenger`
- `Lสۥ۠ۦۡ/สۥ۟۠ۡ;` = `MethodCodec`
- `Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۠ۢ;` = 其内部 callback / result 相关小类

### 5.2 类定义与坏 field_id

`MethodChannel` 的 class_def（`tools/dex_probe.py class 'Lสۥ۠ۦۡ/สۥ۟۟۠;'`）：

- instance fields
  - `field_idx=8163` `ۥ้้۟۟ۡ : Lสۥ۠ۦۡ/สۥ۟۠ۢ;`
  - `field_idx=8164` `ۥ้้้้۟۟ۡ : Ljava/lang/String;`
  - `field_idx=8165` `ۥ้้้้้้۟۟ۡ : Lสۥ۠ۦۡ/สۥ۟۠ۡ;`

但 `field_ids` 里还存在一个**额外的、无 class_def 对应项**：

- `field_idx=8162` `Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้۟۟ۡ : Ljava/lang/String;`

这就是坏引用。也就是说：

- 同名 `ۥ้้۟۟ۡ` 同时被登记成：
  - `field_idx=8162` `String` 版（假的）
  - `field_idx=8163` `BinaryMessenger` 版（真的）
- 真正的 channel name 字段其实是：
  - `field_idx=8164` `ۥ้้้้۟۟ۡ : String`

### 5.3 出错方法与字节证据

坏构造器：

- 类：`Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۠ۢ;`
- 方法：`<init>(Lสۥ۠ۦۡ/สۥ۟۟۠; Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;)V`
- `code_off = 0x4c6618`

其 class_def：

- `field_idx=8160` `ۥ้้۟۟ۡ : Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;`
- `field_idx=8161` `ۥ้้้้۟۟ۡ : Lสۥ۠ۦۡ/สۥ۟۟۠;`

`code_item` 原始字节（`classes2.dex:0x4c6618`）：

```text
004c6618: 05 00 03 00 02 00 00 00 00 00 00 00 0f 00 00 00
004c6628: 1a 00 c7 26 54 31 e2 1f 71 20 da 03 10 00 5b 23
004c6638: e1 1f 70 10 24 3c 02 00 5b 24 e0 1f 0e 00
```

关键指令序列（16-bit code unit 视角）：

- `0x0000` `const-string v0, "MC"`
- `0x0004` `iget-object v1, v3, field@8162`
- `0x0008` `invoke-static {v0, v1}, Log.i`

也就是：

- 构造器日志路径把 `MethodChannel` 对象上的“字符串字段”读成了 `field_idx=8162`
- 但这个字段并不存在于 `MethodChannel` 的 class_def 中
- 运行时因此可能抛出 `NoSuchFieldError` / field resolution failure

### 5.4 交叉引用：坏构造器是从哪里来的

`androguard Analysis.create_xref()` 结果：

- 坏构造器 `Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۠ۢ;-><init>` 的直接调用者为：
  - `Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้۟۟ۡ(Ljava/lang/String;Ljava/lang/Object;Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;)V`
  - 调用偏移：`0x2a`
  - caller `code_off = 0x4c679c`

因此坏点位于 `MethodChannel` 自身的消息/回调分发路径内，不是外围业务类单独实现的反射错误。

### 5.5 为什么这会影响“导入书源”

`classes2.dex` 中已确认存在 filepicker 插件相关字符串与类：

- channel name：
  - `miguelruivo.flutter.plugins.filepicker`
- 关键字符串：
  - `android.intent.action.GET_CONTENT`
  - `allowMultipleSelection`
  - `allowedExtensions`
  - `invalid_format_type`
  - `FilePicker`
- 对应类：
  - `Lสۦ۠ۦ/สۥ۟۠ۢ;`
  - `Lสۦ۠ۦ/สۥ۟۟ۡ;`，其中包含 `onActivityResult`

同时 Dart 字符串里也有：

- `yuedu://booksource/importonline?src=`
- `bookSource...`
- `importall`
- `subscribe`

结合前两轮背景，可合理判断：

- “导入书源/从文件导入”会经由 FilePicker 选文件
- FilePicker 结果通过 Flutter `MethodChannel` 回传 Dart
- 正是在这个 `MethodChannel` 回调路径里，坏字段引用会炸掉

### 5.6 可执行修复方案

#### 方案 A：修正 field index（首选）

将坏 `iget-object` 的 field 引用从 `field_idx=8162` 改到**真实 string 字段** `field_idx=8164`。

- 目标位置：
  - `classes2.dex`
  - `code_off = 0x4c6618`
  - 指令流起点：`0x4c6628`
  - 坏 `iget-object` 位于其后第 2 条 16-bit 指令开始，原始操作数字节可见于 `0x4c662c`
- 原始 16-bit operand：
  - `e2 1f` -> little-endian `0x1fe2` -> `field_idx=8162`
- 建议改为：
  - `e4 1f` -> little-endian `0x1fe4` -> `field_idx=8164`

即：

```text
classes2.dex @ 0x4c662c: e2 1f  ->  e4 1f
```

效果：

- 该构造器日志路径将读取真实的 channel name 字段，而不是不存在的假字段。

#### 方案 B：直接去掉日志读字段（保守）

若不想动 field index，也可把构造器里的：

- `const-string "MC"`
- `iget-object ... field@8162`
- `invoke-static Log.i`

整段改成 no-op / 直接跳过。

这会比 A 更粗暴，但也足以规避异常。

### 5.7 对“原版 bug 还是重打包引入”的判断

目前更像是 **当前 dex 产物本身就含有无效 field_id 引用**，而不是 Dart 业务逻辑 bug。

本轮不能仅靠静态分析证明“原版 APK 是否也有同一问题”，但可以确认：

- 报错根因在 `classes2.dex` 的 Java/Flutter 层
- 与 Dart 业务字符串 `bookSource/import` 本身无关
- 修复重点应落在 `classes2.dex` 的 `MethodChannel` 路径，而不是继续追 `了/了`

## 6. 任务 B：广告 / FilePicker 相关 Java 层补充

### 6.1 FilePicker 插件类

- `Lสۦ۠ۦ/สۥ۟۠ۢ;`
  - 持有 `Lสۥ۠ۦۡ/สۥ۟۟۠;` 字段（即 `MethodChannel`）
- `Lสۦ۠ۦ/สۥ۟۟ۡ;`
  - 含 `onActivityResult`
  - 字段中含 `String` 与 `String[]`

这两类足以支撑“导入文件 -> Activity result -> MethodChannel 回传”的链路。

### 6.2 广告部分

本轮没有继续深入广告 SDK 初始化与展示回调，只保留前一轮已知结论：

- 故障窗正文 `ref=27673` 与广告失败提示高度相关
- `0x00bc0f40` 比 `0x00bbec34` 更像广告失败后的故障窗路径

## 7. 任务 D：VIP / 更新

本轮只复核了旧地址周边上下文，未完成“函数名级确认”。

### 7.1 旧地址复核

- `0x00a54178`
  - 仍呈现对象构造 + 条件读取形态，像 UI/状态构造层
- `0x00b9fc84`
  - 含多处 `CMP/TBNZ/B EQ`
  - 其中可见：

```asm
0x00b9fcec  1f 00 16 6b  CMP W0, W22
0x00b9fcf0  20 05 00 54  B EQ, .+0xa4
...
0x00b9fd20  1f 00 16 6b  CMP W0, W22
0x00b9fd24  80 03 00 54  B EQ, .+0x70
```

- `0x00dac684`
  - 仍像 URL/文本选择器一类逻辑
- `0x0085f09c`
  - 仍像字段拼装器 / 文本构造器

### 7.2 当前结论

- 这些地址**仍值得保留为前两轮候选**。
- 但在没有 Code 对象命名映射前，本轮不把它们升级为已证实 `isVip/checkUpdate`。

## 8. 本轮最重要交付物

### 8.1 可直接用于修复“导入书源”ANR 的点

- 文件：`main_dex/classes2.dex`
- 位置：`0x4c662c`
- 原始字节：`e2 1f`
- 建议改为：`e4 1f`
- 含义：`field_idx 8162 -> 8164`

### 8.2 故障窗当前最强候选分支

- 候选函数入口：`0x00bc0f40`
- 候选判定调用：
  - `0x00bc1014  LDR X0, [X0,#2256]`
  - `0x00bc1018  BL ...`
- 候选条件分支：
  - `vaddr/file offset = 0x00bc1020`
  - 前一条比较：`0x00bc101c  CMP W0, W22`
  - 机器码：
    - `0x00bc101c`: `1f 00 16 6b`
    - `0x00bc1020`: `a0 12 00 54`

> 重要说明：这仍是**高置信候选**，不是已完全证实的最终故障窗 patch 点。

## 9. 后续建议

按收益排序：

1. **先修 `classes2.dex @ 0x4c662c` 的坏 field index。**
   - 这是第三轮最扎实、最可执行的交付。
2. 若要继续故障窗：
   - 以 `0x00bc0f40` 为中心继续做间接 caller / BLR 链跟踪。
   - 不要再把 `0x00bbec34` 误当故障窗，它明显复用了篡改窗字符串簇。
3. 若要继续核心反序列化：
   - 应从 `unflutter` 内部补导出 `ObjectPool/Code`，而不是重复靠字符串 slot 猜测。

