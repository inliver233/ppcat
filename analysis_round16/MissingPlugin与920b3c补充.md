# MissingPlugin 与 0x920b3c 补充

## 1. `MissingPluginException` 构造函数复核

`test2` 第八轮新增的 `0xca8bdc` 在 `test1` 本地已复核通过：

```asm
0x00ca8bdc: fd79bfa9    stp     x29, x30, [x15, #-0x10]!
0x00ca8bf0: e10316aa    mov     x1, x22
0x00ca8bf4: 820180d2    mov     x2, #0xc
0x00ca8bf8: 6c6c0b94    bl      #0xf83da8
0x00ca8bfc: 713b7ef9    ldr     x17, [x27, #0x7c70] ; ref=27913 MissingPluginException(
0x00ca8c04: 718748f9    ldr     x17, [x27, #0x1108] ; ref=28182 channel_name
0x00ca8c3c: 5df2de97    bl      #0x4655b0
0x00ca8c4c: c0035fd6    ret
```

对象池映射也对上：

- `ref=27913 -> slot 0xf8e -> off 0x7c70`
- `ref=28182 -> slot 0x3302 -> off 0x19820`
- `ref=21867` 是旁边的 `PlatformException(` 兄弟构造函数 `0xca8c58`

## 2. 为什么不直接推荐 patch `0xca8bdc`

尽管构造函数本体定位是对的，但当前静态证据还不足以证明：

- 返回 `null` 的异常对象之后，调用方是“吞掉错误继续跑”
- 还是“马上把 null 当异常对象继续传给 runtime”，从而触发另一种崩溃

已知事实：

- `0xca8bdc` 在 `test3` 的 `xref_db` 中 `callers=0`
- 直接 `BL` 扫描也找不到显式 caller
- 说明它大概率像很多 Dart AOT helper 一样，是通过高地址 runtime / 间接分发表进入的

因此这条线当前只能定性为：

- **“定位成功，但 patch 风险未知”**

不应在没有运行时回馈前，优先于 `0x920b3c / 0x920d7c` 这类更可控链路。

## 3. `0x920b3c` 的地位高于 `0xc4cb30`

这一轮对 `0x920b3c` 做了更完整的本地复核：

`test3 xref_db`：

- `0x920b3c`
  - `callers = 0`
  - `callees = [0x47f1c8, 0x5a9bd4, 0x892290, 0x920d7c, 0xf216e4, 0xf83fec, 0xf8482c, 0xf91140]`
  - `bool_ret = False`

它和 `0xc4cb30` 的差异是：

- `0xc4cb30` 更像一个“展示层分叉 + 局部 dialog 包装器”
- `0x920b3c` 则在调完 `0x920d7c` 后，继续把对象送进：
  - `0xf216e4`
  - `0xf8482c`

这和 `backup/ROUND8_FACTS` 中“故障 body 对象经高地址 runtime 再分发给全局错误处理链”的定性更一致。

关键片段：

```asm
0x00920d14: 700361f9    ldr     x16, [x27, #0x4200]
0x00920d18: f001bfa9    stp     x16, x0, [x15, #-0x10]!
0x00920d1c: 18000094    bl      #0x920d7c
0x00920d20: ef410091    add     x15, x15, #0x10
...
0x00920d50: e18d1ff8    str     x1, [x15, #-8]!
0x00920d58: 63021894    bl      #0xf216e4
...
0x00920d78: ad8e1994    bl      #0xf8482c
```

所以：

- `0x920d1c -> NOP` 依然是这条链上更值得优先测试的点
- 它比继续围绕 `0xc4cb30` 的 `showDialog BL` 做文章更贴近根因

## 4. 对 `0xae312c` 的方向纠正

上一轮 `test1` 报告里把 `0xae312c` 的方向解释反了，这里更正：

```asm
0x00ae3128: 1f500071    cmp     w0, #0x14
0x00ae312c: c10d0054    b.ne    #0xae32e4
```

`喵喵饿了` 的真实字符串加载点：

```asm
0x00ae36fc: 31f246f9    ldr     x17, [x17, #0xde0] ; ref=28525 "喵喵饿了"
```

而 `0xae36fc` 位于：

- `0xae32e4` 之后

也就是说：

- **PATH_B 才是含 `喵喵饿了` 文本装载点的那条支路**

因此：

- `0xae312c -> 6e000014` 会强制进 **PATH_B**
- 它不是“跳过喵块”，而更像“强制进喵块相关支路”

正确的静态结论应是：

- 若想强制不进 PATH_B，优先候选是把 `0xae312c` 改成 `NOP`
  - `c1 0d 00 54 -> 1f 20 03 d5`
  - 含义：去掉 `b.ne`，让流程落回 PATH_A

但：

- `PATH_A` 是否一定“不显示喵块”，当前仍缺运行时佐证
- 所以这条仍然只能标成“方向已纠正的候选”，不能包装成已确认方案
