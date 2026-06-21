export const meta = {
  name: 'ppcat-miao-state-deepdive',
  description: '深挖喵喵块"可见性状态"——验证VIP/喂猫思路：块是否有原生不显示路径，找控制字段（绕开cid墙）',
  phases: [
    { title: 'Scout', detail: '5路并行侦察：reader显示判断/VIP字段/喂猫全局态/状态对象全景/常显否证' },
    { title: 'Synthesize', detail: '综合：是否找到让app自己隐藏块的状态字段，给patch候选' },
  ],
}

const CTX = [
  '你在做 Dart AOT (ARM64) 静态逆向，皮皮喵 com.gentle.ppcat 的 libapp.so 代码恢复（中性措辞）。',
  '基准文件（原始未patch，16352152字节，vaddr==file offset）: /root/ppcat_repo/libapp.so',
  '对象池: /root/ppcat_repo/analysis_workdir/pool_deserialized.json (entries:[{idx,type,val,eb,off}]，by_ref:{refStr:[idx,off]})',
  'xref: /root/ppcat_repo/analysis_workdir/xref_db.json (键是【十进制地址字符串】)',
  '字符串: /root/ppcat_repo/unflutter_strings.txt (格式 [ref=N] (Nb) "...")',
  '符号名: /root/ppcat_repo/unflutter_names.txt',
  '工具(可直接python3): disasm.py (python3 disasm.py <hex> <count> 或 func <hex>)、scan_slot.py (python3 scan_slot.py <slot_hex>)、func_slots.py (python3 func_slots.py <hex>)，都在 /root/ppcat_repo/analysis_workdir/',
  'function_summary.txt: 每行一个函数(addr,size,instrs,...)。pool_accesses.txt: pool访问记录。capstone 5.0.7可用。',
  '',
  '调用约定: X15=影子栈,X26=Thread,X27=Pool(PP),X22=null,X28=heap base。',
  '序言: stp x29,x30,[x15,#-0x10]!; mov x29,x15 (fd79bfa9 fd030faa)。',
  '尾声: mov x15,x29(ef031daa); ldp x29,x30,[x15],#0x10(fd79c1a8); ret(c0035fd6)。',
  'bool: add xR,x22,#0x30=True / #0x20=False。tbnz/tbz w0,#4 测bool(bit4)。',
  'PP slot加载: add xR,x27,#page lsl12 + ldr xD,[xR,#off]，slot=(page+off)/8。',
  'Thread全局状态: ldr xR,[x26,#0x80] 取全局状态对象(G)，再 ldr/ldur xR,[xR,#fieldoff] 读G的各字段。',
  '',
  '【背景-必读】喵喵块=阅读页悬浮Button[720,1260][1080,1392] content-desc="喵喵饿了"。builder=0xa52bb0(返回cid0xaf7 widget)，caller=0xa52920(建内容child后tail-call 0xa52bb0)。0xa52920 callers=[](pool间接，reader build经pool间接调它)。',
  '已知: 0xa52920内部读全局状态G=Thread[x26+0x80]的 +0xed0和+0x1028(根据bit4选猫饿/猫饱不同内容slot0xbb8/0xbc0)，但无论哪条路径都最终构造并返回喵喵块(无条件)。',
  '喂猫逻辑0xb68234: 读某状态对象.field@0x33(bool),若TRUE(猫饿)执行喂并置FALSE，若FALSE早退返回null。串含"每天喂一次喵喵就不来找你了~"。',
  '广告免广告时效0x8cf36c(非喵喵块相关!): 字符串adNum/已生效剩余X秒/已过期。读G=Thread[x26+0x80]的+0xb40/+0x2540/+0x1120。',
  'reader build不可静态精确定位(pool间接+blutter cid84墙)。E2找到候选0xbf9be8(31112B,reader模式标志齐全)但喵喵链不可证。',
  '',
  '【本任务核心目标】用户提出新思路: 不去动喵喵块builder本身(撞cid墙)，而是让app自己走"不显示块"的原生路径——即让app认为用户已喂猫/有VIP，reader build自然不构造块。任务: 验证这个思路是否可行——【喵喵块到底有没有原生的不显示代码路径】，如果有，找到控制它的状态字段或判断分支，给出强制该状态让app自己隐藏块的patch。',
  '',
  '【诚实要求】这是test3第4次误判的高风险区。绝不要把"看到了状态读取"就等同于"找到了显示开关"。喵喵块可能本就是无条件常显(喂猫只是当日不再弹喂猫prompt，块本身一直在)。必须用字节证据区分这两种情况。每个结论标注静态确定/推断/需主控验证。',
].join('\n')

const SCHEMA = {
  type: 'object',
  properties: {
    scout_id: { type: 'string' },
    core_answer: { type: 'string', description: '回答本路侦察的核心问题(2-4句)。最重要的: 喵喵块是否有原生不显示路径?控制字段是什么?' },
    has_hide_path: { type: 'string', enum: ['yes-found-condition', 'no-likely-unconditional', 'uncertain'], description: '喵喵块是否有原生不显示路径' },
    method: { type: 'string', description: '实际做的验证(命令/反汇编/字节)' },
    byte_evidence: { type: 'string', description: '字节级证据:地址+字节+反汇编+推理' },
    state_field_or_branch: { type: 'string', description: '若找到控制块可见性的状态字段(如G.field@0xXXX或某bool)或判断分支(某函数的if),给精确地址+字段偏移。无填未找到。' },
    patch_candidate: { type: 'string', description: '若找到可行的让app自己隐藏块的patch思路(强制状态/反转分支),给地址+字节。无填无。' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    caveats: { type: 'string', description: '不确定性/需主控验证项/可能崩的原因' },
  },
  required: ['scout_id', 'core_answer', 'has_hide_path', 'method', 'byte_evidence', 'state_field_or_branch', 'patch_candidate', 'confidence', 'caveats'],
}

const scouts = [
  {
    scout_id: 'S1-reader-show-gate',
    prompt: CTX + '\n\n【侦察S1: reader build 是否"条件化"显示喵喵块?】\n这是回答根本问题的关键。喵喵块由reader build(经pool间接)调0xa52920构造。如果reader build有 if(某条件) children.add(喵喵块) 的判断，那找到条件=找到隐藏开关。\n方法:\n1. 深入分析reader候选0xbf9be8(31112B,0xbf9be8-0xc01020)。反汇编它的关键部分(尤其加载slot0x753 obj44988的位置，或任何构造widget列表/Stack.children的地方)。它是否调0xa52920或加载喵喵块簇slot?\n2. 既然0xa52920 callers=[](pool间接)，找reader build内通过t3(switchable-call)间接调用0xa52920 Code对象的痕迹——即reader build加载某个pool slot(指向0xa52920的Code)，那个slot的加载点附近是否有条件判断(tbnz/tbz/b.eq)跳过它。\n3. scan_slot喵喵块簇slot 0x3689-0x368d(obj96447等)和slot0x753(obj44988)的所有loader，看是否有reader区(0xb5-0xc0)大函数加载它们=候选reader build。\n4. 关键: 即使找不到reader build，也要判断——喵喵块的"猫饿/猫饱"分支(0xa52920读G.field@0x1028的bit4)是否可能就是"显示饿猫块/显示饱猫块"，而非"显示/不显示"。区分清楚。\n诚实判定has_hide_path。',
  },
  {
    scout_id: 'S2-vip-field',
    prompt: CTX + '\n\n【侦察S2: VIP/会员特权字段在哪?(与广告特权0x8cf36c区分)】\n用户说"喵喵块也能通过VIP去除"。VIP特权和广告免广告时效(0x8cf36c)是两回事。找VIP/会员相关的状态字段。\n方法:\n1. 在unflutter_strings.txt搜VIP/会员/vip/永久/开通/开通会员/去广告/免广告/永久免广告/adVip/premium/membership等关键词及其ref。\n2. 找到的VIP相关串的loader(scan_slot)→这些函数读/写什么状态(尤其全局G=Thread[x26+0x80]的哪个field)。\n3. 区分: 哪些VIP状态字段被喵喵块相关函数(0xa52920/0xa52bb0/0xb68234/reader区)读取?这暗示喵喵块可见性绑VIP。\n4. 反汇编喵喵块caller链(0xa52920)里读G的+0xed0/+0x1028，确认这俩字段是否可能是VIP/特权(而非仅猫饿/猫饱图标)。\n5. 若找到独立VIP字段，能否强制它=有VIP让reader build跳过喵喵块?\n诚实判定has_hide_path。',
  },
  {
    scout_id: 'S3-feedcat-global-state',
    prompt: CTX + '\n\n【侦察S3: 喂猫成功后写入的全局状态?(猫饿bool的来源)】\n喂猫逻辑0xb68234读/写某对象的field@0x33(猫饿bool)。但这个对象在哪?喂猫成功后是否更新全局G=Thread[x26+0x80]的状态(今日已喂/猫饱)?\n方法:\n1. 反汇编0xb68234完整，追踪它操作的对象(param.field@0x17.field@0xf)是什么——是否来自全局G?\n2. 反汇编0xb68234的callers(查xref)，找喂猫的触发点(reward成功回调)。喂猫成功后是否有"更新全局今日喂猫计数/猫状态"的写入到G?\n3. 反汇编0xa56e00(0xb68234调用,callers=4)和0xa56be4(喂饱toast"喵喵喂饱了~")，找猫状态的全局写入。\n4. 关键问题: reader build决定显示喵喵块时，读的"猫饿"状态来自哪——是喂猫写的那个field@0x33，还是G上某字段?如果是G字段，scan哪些函数读它→其中一个可能是reader build的显示判断。\n5. 0xa52920读G.field@0xed0/+0x1028，这俩是不是喂猫相关状态(猫饿/今日已喂)?\n诚实判定。',
  },
  {
    scout_id: 'S4-global-state-object-map',
    prompt: CTX + '\n\n【侦察S4: 全局状态对象G=Thread[x26+0x80]的字段全景】\nG是核心枢纽: 喵喵块读G+0xed0/+0x1028，广告特权读G+0xb40/+0x2540/+0x1120。把G的所有字段语义摸清，尤其哪个字段控制喵喵块可见性。\n方法:\n1. 全.text搜 "ldr xR,[x26,#0x80]" 模式，找所有读G=Thread[x26+0x80]的函数。统计G的哪些fieldoffset被频繁读取(+0xed0,+0x1028,+0xb40,+0x2540,+0x1120,...)。\n2. 对每个G.fieldoffset，找读取它的函数，看那些函数的字符串/语义(用xref_db.json的strs字段)推断字段含义。\n3. 重点: G+0xed0和G+0x1028(喵喵块读的)分别被哪些函数读?除了0xa52920，还有谁读?那些函数的语义能揭示这俩字段是不是VIP/猫状态/可见性开关。\n4. 找有没有一个G字段是"显示喵喵块"的开关——被reader build读取决定是否构造块。\n诚实判定has_hide_path。',
  },
  {
    scout_id: 'S5-unconditional-disprove',
    prompt: CTX + '\n\n【侦察S5: 尽力证伪——喵喵块是否本就无条件常显?】\n这是批判性视角(对抗盲目乐观)。尽力证明"喵喵块无原生不显示路径，喂猫/VIP只是当日不再弹提示，块本身永远显示"，从而使VIP思路落空。\n方法:\n1. 用户说"看广告去除/VIP去除"——核实这个说法。在unflutter_strings里搜"喵喵"相关串，看有没有"去除/隐藏/关闭"喵喵块的串，或喂猫后"喵喵块消失"的承诺。如果只有"每天喂一次就不来找你"(0xb68234)这类，它可能指弹窗而非悬浮块。\n2. 喂猫逻辑0xb68234和0xa52920是两个独立函数——0xb68234处理喂猫动作，0xa52920构造悬浮块。它们可能完全不共享状态(悬浮块常显，喂猫只管计数/弹窗)。检查0xa52920是否读任何"今日已喂/猫饱"状态来决定显示——如果0xa52920只读G+0xed0/+0x1028且这俩只是图标选择(猫饿图标vs猫饱图标)而非显示开关，则块常显。\n3. a11y显示块content-desc="喵喵饿了"——这是块的固定标签还是动态?如果固定，块永远是"喵喵饿了"入口(常显)。\n4. 找任何证据支持"块条件显示"或"块常显"，给出天平两侧证据。\n诚实判定has_hide_path(这路如果判no-likely-unconditional，是对整个VIP思路的最重要证伪)。',
  },
]

phase('Scout')
const scoutResults = await parallel(
  scouts.map(function (s) {
    return function () {
      return agent(s.prompt, { label: s.scout_id, phase: 'Scout', schema: SCHEMA })
    }
  })
)

const found = scoutResults.filter(Boolean)
log('5路侦察完成: ' + found.map(function (r) { return r.scout_id + '=' + r.has_hide_path; }).join(', '))

phase('Synthesize')
// synthesis reads all scout findings + the libapp, judges whether a state-based hide patch exists
const synth = await agent(
  CTX + '\n\n【综合判断】下面是5路侦察的结构化发现。请综合判断:\n' +
  JSON.stringify(found, null, 1) +
  '\n\n回答:\n1. 【喵喵块是否有原生不显示路径?】综合5路证据，给最终判定(yes/no/uncertain)及置信度。\n2. 【若yes】控制块可见性的状态字段/分支是什么(精确地址+字段)?给出"强制状态让app自己隐藏块"的patch候选(地址+原字节+补丁字节+为何app自己逻辑会隐藏)。标注崩点。\n3. 【若no】诚实说明VIP/喂猫思路为何落空(块常显)，并确认当前最佳方案仍是Patch D(0xa52c68 field-null)。\n4. 区分: 首页overlay(已根治)的VIP vs 喵喵块的VIP(如果有)是同一字段还是不同。\n5. 交叉验证各路一致性(尤其S1/S5的张力)。',
  { label: 'synthesize', phase: 'Synthesize', schema: {
    type: 'object',
    properties: {
      final_verdict: { type: 'string', enum: ['has-hide-path', 'no-unconditional', 'uncertain'] },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
      reasoning: { type: 'string' },
      state_field_or_branch: { type: 'string' },
      patch_candidate: { type: 'string' },
      best_overall_approach: { type: 'string', description: '综合后当前最推荐的主控测试方案(Patch D? 状态强制? 其他?)' },
      caveats: { type: 'string' },
    },
    required: ['final_verdict', 'confidence', 'reasoning', 'state_field_or_branch', 'patch_candidate', 'best_overall_approach', 'caveats'],
  } }
)

return { scouts: found, synthesis: synth }
