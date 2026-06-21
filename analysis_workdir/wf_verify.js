export const meta = {
  name: 'ppcat-miao-block-verify',
  description: '对抗式验证 0xa52bb0 喵喵块 safe-hide 分析的高风险结论 + 突破静态天花板（皮皮喵代码恢复 test3 第九轮）',
  phases: [
    { title: 'Verify', detail: '6 个独立对抗验证者，各复核一条核心结论，默认存疑' },
    { title: 'Explore', detail: '2 个深挖者：找真 const Widget 实例 slot / 替代法找 reader build' },
  ],
}

const CTX = [
  '你在做 Dart AOT (ARM64) 静态逆向，皮皮喵 com.gentle.ppcat 的 libapp.so 代码恢复（中性措辞）。',
  '基准文件（原始未 patch，16352152 字节，vaddr==file offset）: /root/ppcat_repo/libapp.so',
  '对象池: /root/ppcat_repo/analysis_workdir/pool_deserialized.json (entries:[{idx,type,val,eb,off}...]，by_ref:{refStr:[idx,off]})',
  'xref: /root/ppcat_repo/analysis_workdir/xref_db.json (键是【十进制地址字符串】，如 1050644=0xa02e14)',
  '字符串: /root/ppcat_repo/unflutter_strings.txt (格式 [ref=N] (Nb) "...")',
  '符号名: /root/ppcat_repo/unflutter_names.txt',
  '工具(可直接 python3): disasm.py (python3 disasm.py <hex> <count> 或 python3 disasm.py func <hex>)、scan_slot.py (python3 scan_slot.py <slot_hex>)，都在 /root/ppcat_repo/analysis_workdir/',
  'capstone 5.0.7 可用。Python3 可用。',
  '',
  '调用约定: X15=影子栈, X26=Thread, X27=Pool(PP), X22=null, X28=heap base。',
  '序言: stp x29,x30,[x15,#-0x10]!; mov x29,x15 (字节 fd79bfa9 fd030faa)。',
  '尾声跳板: mov x15,x29 (ef031daa); ldp x29,x30,[x15],#0x10 (fd79c1a8); ret (c0035fd6)。',
  'bool: add xR,x22,#0x30=True / #0x20=False。',
  'PP slot 加载: add xR,x27,#page lsl12 (0x91xxxxxx) + ldr xD,[xR,#off] (0xF940xxxx)，slot_index=(page+off)/8。',
  '对象分配 thunk: mov x2,#imm; movk x2,#cid,lsl16(高16位=cid); ldr x4,[x26,#0x228或0x230]; br x4。返回 x0=新分配 cid 实例。',
  '对象域写: stur wR,[x0,#fieldoff]。',
  '',
  '背景: 喵喵块 builder=0xa52bb0(224字节,cat模块0xa52xxx)，caller 0xa52920(672字节,建大复合内容x1后tail-call 0xa52bb0)。0xa52920 callers=[](pool间接,reader build经pool间接调它)。喵喵块 a11y=Button [720,1260][1080,1392] content-desc="喵喵饿了"。',
  '已知: 0xa52bb0 entry-null→阅读页整页空白(主控装机实测)。返回 slot 0x1db(obj51369)/slot 0x368d(obj91683)→空白。返回 obj44988(slot 0x753)→偶尔渲染(点击无reward)通常空白。',
  '【关键坑勿重蹈】: pool slot 0x3975 = ref1973 = 字符串 "SizedBox.shrink"(调试符号名 String,非 const SizedBox Widget 实例)。test3 曾把它当 const widget 返回→装机 SIGSEGV。绝不可把 String/符号 ref 当 Widget 实例。',
].join('\n')

const VERDICT_SCHEMA = {
  type: 'object',
  properties: {
    claim_id: { type: 'string' },
    verdict: { type: 'string', enum: ['CONFIRMED', 'REFUTED', 'UNCERTAIN'] },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    independent_check_method: { type: 'string', description: '你实际做了什么验证(命令/字节/反汇编)' },
    byte_evidence: { type: 'string', description: '字节级证据: 地址+原始字节+反汇编+推理' },
    flaw_or_correction: { type: 'string', description: '若发现结论缺陷,精确说明正确的是什么(地址+字节)。结论正确填无。' },
    impact_on_patch: { type: 'string', description: '此结论若错,对哪个补丁有何影响' },
  },
  required: ['claim_id', 'verdict', 'confidence', 'independent_check_method', 'byte_evidence', 'flaw_or_correction', 'impact_on_patch'],
}

const verifyPrompts = [
  {
    claim_id: 'V1-field-dataflow',
    prompt: CTX + '\n\n【对抗验证 V1: 0xa52bb0 返回对象 field@0xf 与 field@0xb 的数据来源】\n我的结论: 0xa52bb0 返回的喵喵块 widget, field@0xf(偏移0xf)=内容 child(来自0xa52920建的大复合widget x1,cid 0x7df), field@0xb=回调/closure。补丁策略是让 field@0xf 内容变 null(0xa52c68: stur w1→stur w22)移除可见内容。\n请独立验证这条数据流:\n1. 反汇编 0xa52920。确认 0xa52b90 附近 str x1,[x15,#-8]!(把x1压影子栈) + 0xa52b94 bl 0xa52bb0(tail-call)。\n2. 反汇编 0xa52bb0。确认序言后, x1 在哪被取回(ldr/ldur x?,[x29,#0x10], 因为 caller 的 [x15,#-8] 对应 callee 的 [x29,#0x10])。\n3. 确认 0xa52c64 ldr x1,[x29,#0x10] 取回的就是 caller 传的 x1, 然后 0xa52c68 stur w1,[x0,#0xf] 写入 field@0xf。\n4. 确认 0xa52c5c-0xa52c60 ldur x1,[x29,#-8](取 0xa52c90 结果) + 0xa52c60 stur w1,[x0,#0xb] 写入 field@0xb。\n逐字节核对栈帧偏移。若 field@0xf 的源不是我说的 x1(内容),或偏移错位,判 REFUTED 并给出正确映射。默认存疑: 除非你独立追到字节证据,否则不轻信。',
  },
  {
    claim_id: 'V2-patchD-bytes',
    prompt: CTX + '\n\n【对抗验证 V2: field-null 补丁字节编码】\n我的补丁 D: 在 0xa52bb0 内,把两条 stur 的源寄存器从 w1 改成 w22(null):\n- 0xa52c68: 原 01f000b8 (stur w1,[x0,#0xf]) → 改 16f000b8 (stur w22,[x0,#0xf])\n- 0xa52c60: 原 01b000b8 (stur w1,[x0,#0xb]) → 改 16b000b8 (stur w22,[x0,#0xb])\n请独立用 capstone 验证:\n1. 读 libapp.so 在 0xa52c60..0xa52c6c 的原始字节,确认是 01b000b8 和 01f000b8。\n2. 用 capstone 反汇编 16b000b8 和 16f000b8,确认分别解码为 stur w22,[x0,#0xb] 和 stur w22,[x0,#0xf]。\n3. 确认 ARM64 stur 指令中 w22 寄存器编码(Rt=22)是否对应 0x16。验证 capstone 实际输出。\n4. 确认改这两条只动寄存器操作数,不影响控制流/栈/其它域。\n若编码错(w22 编码不对,或 stur offset 字段算错),判 REFUTED 给正确字节。',
  },
  {
    claim_id: 'V3-cid-uniqueness',
    prompt: CTX + '\n\n【对抗验证 V3: 返回对象 cid 与唯一性】\n我的结论: 0xa52bb0 返回的喵喵块 widget 是 cid 0xaf7(十进制2807)的实例,全.text仅0xa52c84一处分配(movk x2,#0xaf7,lsl16=字节 e25ea1f2);cid 0xaf3(2803)仅0xa532d8。→0xa52bb0是该 widget 类的唯一构造点。\n请独立验证:\n1. 全.text(从0x464ce0起到文件尾)搜字节 e25ea1f2(movk x2,#0xaf7,lsl16),确认仅1处命中0xa52c84。\n2. 反汇编 0xa52c80..0xa52c90,确认 mov x2,#0x204; movk x2,#0xaf7,lsl16; ldr x4,[x26,#0x228]; br x4 是分配 cid-0xaf7 的标准 thunk,返回 x0=cid0xaf7 实例。\n3. 确认 0xa52c58 bl 0xa52c80(call thunk)后 x0 流到 0xa52c60 stur w1,[x0,#0xb](x0=新对象)→0xa52bb0 返回的就是这个 cid0xaf7 对象。\n4. 交叉确认 obj44988(slot 0x753): 它不是 String(grep unflutter_strings 确认 ref44988 不在)。它是否很可能也是 cid0xaf7 实例?(需簇解析,可能无法100%静态确认—诚实标注)。\n若 cid 不对或分配点不唯一,判 REFUTED。',
  },
  {
    claim_id: 'V4-tail-call-wrapper',
    prompt: CTX + '\n\n【对抗验证 V4: 0xa52920 是干净的 tail-call 包装器】\n我的补丁 B(兜底): 在 0xa52920 func+8(0xa52928)写 3-word entry-null(mov x0,x22; ldp x29,x30,[x15],#0x10; ret),让 0xa52920 直接返回 null。已被主控证明→阅读页空白。本条只验证【补丁字节本身的正确性与栈对称性】,不验证视觉效果。\n请独立验证:\n1. 反汇编 0xa52920 全部672字节。确认 0xa52920..0xa52928 是标准序言(stp; mov x29,x15)。\n2. 确认 0xa52b94 bl 0xa52bb0 之后到 0xa52ba4 ret 之间是纯尾声(0xa52b98 add x15,#8; 0xa52b9c mov x15,x29; 0xa52ba0 ldp; 0xa52ba4 ret),没有对 x0 的额外操作(0xa52bb0 返回值 x0 原样返回)。\n3. 确认 entry-null 配方字节: e00316aa(mov x0,x22) + fd79c1a8(ldp x29,x30,[x15],#0x10) + c0035fd6(ret),用 capstone 验证解码。注意: 0xa52928 处直接写 ldp, 但序言已 stp x29,x30,[x15,#-0x10]!, 所以 [x15] 指向刚压的帧, ldp 弹出正确—核对栈对称性。\n4. 确认 func+8 = 0xa52928(序言 stp 4字节 + mov x29 4字节, func+8=0xa52928)。\n若栈不对称(func+8 写 ldp 会栈错位)或 x0 在 bl 后被改,判 REFUTED 给正确配方。',
  },
  {
    claim_id: 'V5-blank-mechanism',
    prompt: CTX + '\n\n【对抗验证 V5: entry-null→阅读页空白 的机制推断(推理类,test3最易误判方向)】\n我的推断: 0xa52920 entry-null(返回 null)→reader build 把 null 当 widget 塞进阅读页主 Stack 的 children→Flutter 列表含 null 元素触发非空断言→整个 Stack build 抛异常→阅读页空白。由此我推断【返回任何合法非空 Widget(即使零尺寸如 SizedBox)即可避免空白】。obj91683/obj51369 之所以空白,是因为它们不是 Widget(是组件/数据对象),塞进 widget 槽类型不符。\n请批判性审查:\n1. 0xa52920 返回值真的是被塞进 Stack children 列表吗?还是单个 widget 槽(如 Positioned.child)?静态无法100%确定 reader build,但可从已知证据推断。\n2. "返回任何合法非空 Widget 即可避免空白"是否过度推断?有没有可能返回槽 typed(必须特定 Widget 子类),则 SizedBox 也会类型不符→空白?主控测 obj91683(喵喵块自身组件,cid 可能是0xaf7部件)空白,是否暗示返回槽 typed?\n3. 更保守结论应该是什么?如"返回 obj44988(同为cid0xaf7 const实例,若确认同类)是最可能安全的,因为类型完全匹配"。\n给出批判性评估,指出我推断哪里过度自信,以及最稳妥的静态结论边界。',
  },
  {
    claim_id: 'V6-readerbuild-wall',
    prompt: CTX + '\n\n【对抗验证 V6: reader build 的 pool-间接-caller 墙是否真的不可破(尽力反驳)】\n我的结论: 0xa52920 callers=[](pool 间接), 其入口指针 0xa52920 在 isolate_data 簇区和 pool 区都零命中, 所以无法静态反向定位 reader build。这是 blutter cid84 失败的同一面墙(Code 簇未解析)。\n请尽力反驳此结论:\n1. 全文件(0到16352152)搜 0xa52920 的4字节le32(2029a500)和8字节le64,确认是否真零命中。\n2. 尝试替代法: xref_db.json 里 0xa52920 的 callers 是否真为空?查 1080096(=0xa52920 十进制)。也查 0xa52bb0 的 1081568。\n3. 尝试: 是否有别的函数通过 BL 直接调 0xa52920 或 0xa52bb0?全.text 搜 BL 目标(bl编码94000000~97ffffff, imm26=(addr-src)/4)。写脚本算哪些 bl 指向 0xa52920。\n4. 尝试: 哪个大函数加载了 slot 0x753 obj44988 或喵喵块簇 slot 0x3678-0x368d,从而可能引用喵喵块 Code?用 scan_slot 找这些 slot 的 loader,看有无 reader 区大函数。\n诚实判定: reader build 静态定位是否真的不可行?若你找到任何线索(哪怕 partial),给出。若确认墙不可破,判 CONFIRMED(即我结论"不可破"成立)。',
  },
]

const explorePrompts = [
  {
    claim_id: 'E1-find-const-widget',
    prompt: CTX + '\n\n【深挖 E1: 在 pool 中找一个真正的 const Widget 实例 slot(非 String/符号)】\n目标: 为 0xa52920/0xa52bb0 找一个"返回它就能让喵喵块被零尺寸/空 Widget 替换、且阅读页不崩"的 pool slot。要求该 slot 对象必须是 Widget 实例(cid 是 Flutter Widget 子类如 SizedBox/Container),绝不能是 String(如 slot0x3975=ref1973"SizedBox.shrink"是 String 陷阱)。\n方法(用对象池+静态特征,不依赖 blutter cluster):\n1. pool_deserialized.json entries 里,找 type=0 且 val 不在 unflutter_strings 也不在 unflutter_names 的 OBJECT 条目(候选实例)。\n2. 用 pool_accesses.txt 找"被最多函数加载的 type=0 非String slot"(const widget 会被频繁引用)。特别检查 slot 0x1db(obj51369,724次加载,主控测返回它→空白)是什么。\n3. 关键: 能否确认 obj44988(slot 0x753) 与 0xa52bb0 返回对象【同类】(都是 cid0xaf7)?若是,让 0xa52bb0 返回 obj44988 是类型最安全的(但主控测它渲染不稳—分析为何不稳: 可能寄存器/栈状态未清理)。\n4. 给出让 0xa52bb0【稳定】返回 obj44988 的补丁(在 func+8=0xa52bb8 加载 slot0x753 到 x0: slot0x753 byteoff=0x753*8=0x3a98, page=0x3000, off=0xa98 → add x0,x27,#0x3,lsl12(60734091); ldr x0,[x0,#0xa98](98454009); 然后 mov x15,x29(ef031daa); ldp(fd79c1a8); ret(c0035fd6)。注意此 func 序言只 stp+mov x29(没 sub x15),尾声需 mov x15,x29 复位。用 capstone 验证字节)。\n给出: ① 任何确认的 const-Widget-instance slot(带证据: 为何确认是 Widget 不是 String) ② 若无确认的,最安全候选+风险。诚实标注哪些需主控验证。每个 slot 必须明确 is_string_or_symbol 判定。',
  },
  {
    claim_id: 'E2-find-reader-build',
    prompt: CTX + '\n\n【深挖 E2: 用替代静态方法尽力定位 reader build】\n目标: 找到调用 0xa52920(经 pool 间接)的 reader build 函数。reader build = 构建阅读页主 Stack(含 manga 内容 ImageView + 喵喵块 Button[720,1260][1080,1392] + 页码指示 1/4 WIFI)的大函数。\n已知排除: 0xb799b8(主控null→阅读页正常,块还在,非reader build)、0xa52920 callers=[](pool间接)、0xa52920 入口在 isolate_data+pool 零命中。\n替代方法(尽力):\n1. 喵喵块在阅读页主 Stack 内,与 manga ImageView + 页码指示同级。找【同时加载 manga 内容渲染相关 + 页码指示(调0x91dae0/0x91dd00格式WIFI) + 可能引用喵喵块簇slot】的大函数。用 function_summary.txt 找 reader 区(0xb5-0xbc)或别处的大函数(size>4000字节)。\n2. 喵喵块 builder 0xa52bb0 的返回对象是 cid0xaf7。reader build 把它塞进 Stack.children。reader build 可能加载 slot 0x753(obj44988 同类 const 喵喵块壳)?scan_slot 0x753 看哪些函数加载它(可能有 reader build)。\n3. 用 slot_loader_map 逻辑: 哪个 reader 区函数加载了喵喵块簇的 slot(slot 0x3678-0x368d, obj96447 等)?用 scan_slot 扫 slot 0x3689(obj96447)和 slot 0x753 的 loader。\n4. 0xa52920 建 chrome 后 tail-call。它内部加载的 slot(0x3678-0x3683 等)可能也被 reader build 加载(共享配置)。交叉找。\n给出: 任何 reader build 候选地址(带证据)或"确实静态不可定位"。诚实标注置信度。',
  },
]

const VERDICT2 = {
  type: 'object',
  properties: {
    claim_id: { type: 'string' },
    finding: { type: 'string', description: '核心发现(1-3句)' },
    method: { type: 'string', description: '实际用的命令/脚本/字节' },
    best_candidate: { type: 'string', description: 'E1:最佳const-widget slot候选(slot0x753或别的);E2:reader build地址;或未找到' },
    byte_evidence: { type: 'string', description: '字节级证据' },
    is_string_or_symbol: { type: 'string', enum: ['yes-String/symbol-DO-NOT-USE', 'no-likely-instance', 'uncertain'], description: 'E1专用:该候选是否String/符号陷阱' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    patch_if_any: { type: 'string', description: '若找到可行patch,给地址+原字节+补丁字节+理由。无填无。' },
    caveats: { type: 'string' },
  },
  required: ['claim_id', 'finding', 'method', 'best_candidate', 'byte_evidence', 'confidence', 'patch_if_any', 'caveats'],
}

phase('Verify')
const verifyResults = await parallel(
  verifyPrompts.map(function (p) {
    return function () {
      return agent(p.prompt, { label: p.claim_id, phase: 'Verify', schema: VERDICT_SCHEMA })
    }
  })
)

phase('Explore')
const exploreResults = await parallel(
  explorePrompts.map(function (p) {
    return function () {
      return agent(p.prompt, { label: p.claim_id, phase: 'Explore', schema: VERDICT2 })
    }
  })
)

return {
  verify: verifyResults.filter(Boolean),
  explore: exploreResults.filter(Boolean),
}
