export const meta = {
  name: 'ppcat-reward-hide-chain',
  description: '深度追喵喵块"看广告→当日隐藏"状态链 + VIP/机器码绑定功能(用户确认隐藏路径真实存在)',
  phases: [
    { title: 'TraceChain', detail: '追onTap→reward→状态写入→reader读取隐藏 的完整链路(4路)' },
    { title: 'VIP', detail: 'VIP授予/校验 + 机器码设备绑定深挖(2路)' },
    { title: 'Verify', detail: '对抗验证最优"强制隐藏"patch:是否真隐藏、是否崩、是否绕开cid墙' },
  ],
}

var CTX = [
  '你在做 Dart AOT (ARM64) 静态逆向，皮皮喵 com.gentle.ppcat 的 libapp.so 代码恢复（中性措辞"代码恢复"）。',
  '基准文件（原始未patch，16352152字节，vaddr==file offset）: /root/ppcat_repo/libapp.so',
  '对象池: /root/ppcat_repo/analysis_workdir/pool_deserialized.json (entries:[{idx,type,val,eb,off}]，by_ref:{refStr:[idx,off]})',
  'xref: /root/ppcat_repo/analysis_workdir/xref_db.json (键是【十进制地址字符串】)',
  '字符串: /root/ppcat_repo/unflutter_strings.txt (格式 [ref=N] (Nb) "...")',
  '符号名: /root/ppcat_repo/unflutter_names.txt',
  '工具(可直接python3): disasm.py (python3 disasm.py <hex> <count>)、scan_slot.py (python3 scan_slot.py <slot_hex>)、func_slots.py (python3 func_slots.py <hex>)，都在 /root/ppcat_repo/analysis_workdir/',
  'function_summary.txt(每行一函数)、pool_accesses.txt、capstone 5.0.7可用。',
  '',
  '调用约定: X15=影子栈,X26=Thread,X27=Pool(PP),X22=null,X28=heap base。',
  '序言: stp x29,x30,[x15,#-0x10]!; mov x29,x15 (fd79bfa9 fd030faa)。',
  '尾声: mov x15,x29(ef031daa); ldp x29,x30,[x15],#0x10(fd79c1a8); ret(c0035fd6)。',
  'bool: add xR,x22,#0x30=True / #0x20=False。tbnz/tbz w0,#4 测bool(bit4)。',
  'PP slot加载: add xR,x27,#page lsl12 + ldr xD,[xR,#off]，slot=(page+off)/8。',
  'Thread全局状态: ldr xR,[x26,#0x80] 取全局状态对象(G)，再读G.field@0xXXX。',
  '对象分配thunk: mov x2,#imm; movk x2,#cid,lsl16; ldr x4,[x26,#0x228]; br x4。',
  '',
  '【已确认背景-必读】',
  '1. 喵喵块=阅读页悬浮Button[720,1260][1080,1392] content-desc="喵喵饿了"。builder=0xa52bb0(返回cid0xaf7 widget)。caller=0xa52920(建内容child后tail-call 0xa52bb0)。0xa52920 callers=[](pool间接)。',
  '2. 0xa52920内部: 读全局G=Thread[x26+0x80]的 +0xed0和+0x1028，按bit4(tbnz/tbz)选slot0xbb8或slot0xbc0(疑似猫饿/猫饱两套内容)，但两条路径都最终构造并返回喵喵块。',
  '3. ★★★ 【用户确认的ground truth】: 点喵喵块→看reward广告→成功后【当天不再显示这个块】。这证明喵喵块有原生隐藏路径(app自己的逻辑)，不是无条件常显。隐藏机制: reward成功→写某"今日已看"状态→reader build(或0xa52920链)读该状态→不再构造/返回空块。',
  '4. obj44988(slot0x753, byteoff 0x3a98, ldr x0,[x27,#0x3a98]=604f5df9): 确定非String，是app在0x546760"尺寸==0"分支返回的"渲染空"const Widget(231加载)。★★【核心待验假设】: 0xa52920或其调用者可能有一个"if(今日已看广告/VIP) 则返回obj44988空块 而非真喵喵块"的分支。若找到这个分支的判断点，强制它=真→app自己隐藏块→完全绕开cid墙。',
  '5. reward相关: 0xbc5dc8(reward-prompt"是否看推荐获取喵粮喂喵？", load slot0x8a37 ref18266)。喂猫逻辑0xb68234(串"每天喂一次喵喵就不来找你了~")读obj.field@0x33(猫饿bool)喂后置FALSE。喂饱toast0xa56be4(串"喵喵喂饱了~")。0xa56e00(callers=4,被0xb68234调用)。',
  '6. 广告免广告时效0x8cf36c(非喵喵块!字符串adNum/已生效剩余X秒/已过期,读G+0xb40/+0x2540/+0x1120)。',
  '7. slot0x3975=ref1973"SizedBox.shrink"=String陷阱(勿当widget用)。reader build不可静态精确定位(pool间接+blutter cid84墙),候选0xbf9be8(31112B)低置信。',
  '',
  '【诚实要求】这是test3第4次误判高风险区。绝不要把"看到状态读取"等同于"找到显示开关"。每结论标注 静态确定/推断/需主控验证。字节级证据+交叉验证(≥2法)。',
].join('\n')

var SCHEMA = {
  type: 'object',
  properties: {
    agent_id: { type: 'string' },
    core_finding: { type: 'string', description: '核心发现(2-4句)。最重要: 找到隐藏路径的状态字段/分支了吗?' },
    found_hide_branch: { type: 'string', enum: ['yes-exact', 'yes-candidate', 'no', 'uncertain'], description: '是否找到喵喵块的隐藏分支(判断点)' },
    method: { type: 'string', description: '实际做的验证(命令/反汇编/字节)' },
    byte_evidence: { type: 'string', description: '字节级证据:地址+字节+反汇编+推理' },
    state_field_or_branch: { type: 'string', description: '若找到控制块可见性的状态字段(G.field@0xXXX)或判断分支(函数@addr的if偏移),给精确地址+偏移。无填未找到。' },
    patch_candidate: { type: 'string', description: '可行patch(强制状态/反转分支让app自己隐藏块),地址+原字节+补丁字节+为何app自己逻辑会隐藏。无填无。' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    caveats: { type: 'string', description: '不确定性/崩点预判/需主控验证' },
  },
  required: ['agent_id', 'core_finding', 'found_hide_branch', 'method', 'byte_evidence', 'state_field_or_branch', 'patch_candidate', 'confidence', 'caveats'],
}

var chainAgents = [
  {
    agent_id: 'C1-onTap-reward-callback',
    prompt: CTX + '\n\n【深度追链C1: 喵喵块onTap → reward广告 → 成功回调 → 状态写入】\n用户确认"点块看广告后当天块消失"。找reward成功后写入的"今日已看"状态。\n方法:\n1. 喵喵块onTap回调在builder 0xa52bb0的field@0xb(CALL_F 0xa52c90建的回调集合)。但更直接: reward-prompt 0xbc5dc8及其链。反汇编0xbc5dc8全函数,找它调用什么(reward SDK调用 + 成功分支)。\n2. xref查0xbc5dc8 callers,找喵喵块onTap如何触发它(经pool间接)。找reward成功回调函数(通常含"成功/success/onRewardVerify/关闭"串)。\n3. ★关键: reward成功回调里一定有"写状态"——它把"今日已看广告"写入全局G=Thread[x26+0x80]某field,或写某对象field。找这个strur/store点(写G或写state对象)。精确地址+字段偏移+写入的值(True/日期/计数)。\n4. 这个写入的field,与0xa52920(喵喵块caller)读取的G+0xed0/+0x1028是否同字段?若是→0xa52920的分支可能就是"看过/没看过"而非"猫饿/猫饱"!\n给出: reward成功写状态的精确点(地址+字段+值)。',
  },
  {
    agent_id: 'C2-obj44988-hide-branch',
    prompt: CTX + '\n\n【深度追链C2: 验证核心假设——0xa52920链是否有"if看过/VIP return obj44988空块"分支】\n这是最高价值假设。obj44988是"渲染空"const widget。如果喵喵块caller链在"今日已看/VIP"条件下返回obj44988而非真块,则强制该条件=app自己隐藏块。\n方法:\n1. 反汇编0xa52920完整(672B)。重点找: 是否有分支(tbnz/tbz/b.eq/cbz)在构造0xa52bb0之前,条件为真时跳转到"加载slot0x753 obj44988并返回"(ldr x0,[x27,#0x3a98]=604f5df9; mov x15,x29; ldp; ret)。\n2. scan_slot 0x753(obj44988)的231个loader中,是否有cat模块(0xa5xxxx)或reader区函数加载它做条件返回?重点看0xa52920附近函数(0xa52xxx-0xa54xxx)是否load slot0x753。\n3. 反汇编0xa52920开头: 它先读G+0xed0/+0x1028做tbnz判断——这两个field是否可能=今日已看广告/VIP状态(而非猫饿图标)?如果是,那这个判断就是隐藏开关,改tbnz→无条件跳空分支。\n4. 检查caller: 0xa52920是被reader build经pool间接调,reader build是否先判断状态再决定调0xa52920(构造块)还是直接用obj44988?因reader build不可定位,转而从0xa52920入口的判断入手。\n5. 若0xa52920确有"条件return obj44988"分支,给精确分支地址+tbnz偏移+强制跳该分支的patch(改tbnz为b无条件,或改判断寄存器为常True)。\n给出: 隐藏分支是否存在+精确地址+patch。',
  },
  {
    agent_id: 'C3-today-date-logic',
    prompt: CTX + '\n\n【深度追链C3: "当日"逻辑——今日日期/最后看广告日期字段】\n块"当天"消失=有日期比较(今天 vs 最后看广告日)。找日期/时间相关状态。\n方法:\n1. unflutter_strings搜 today/now/date/lastDate/喂/日/date/days/hours/秒/分 等时间串及其ref,scan_slot找loader。\n2. 找读取系统时间/日期的函数(DateTime.now相关)。看哪些函数调用它,其中一个可能是"判断今日是否已看广告"。\n3. 找"最后看广告时间戳/日期"字段——reward成功回调(C1追的)写入的可能是时间戳而非bool。reader build读它判断"是否今天"。\n4. 0xa52920读的G+0xed0/+0x1028,反汇编它们怎么用(纯bool的tbnz?还是和当前时间cmp?)。若cmp→是日期判断→隐藏逻辑。\n5. 若找到"今日已看"判断,强制它=今天已看(写当前日期或patch比较)→块当天隐藏。\n给出: 日期逻辑的精确字段+判断点。',
  },
  {
    agent_id: 'C4-reward-success-state-write',
    prompt: CTX + '\n\n【深度追链C4: 精确定位reward成功→隐藏状态的"写入"指令并设计强制patch】\n承接C1。目标: 找到reward成功后写"已看"状态的那条store指令,设计patch让它无条件写"已看"(永久隐藏)。\n方法:\n1. 从0xbc5dc8(reward-prompt)出发,反汇编它+它调用的reward相关函数,找reward成功分支(通常tbnz判断成功后写状态+隐藏块/发奖励)。\n2. 找到写"今日已看/VIP"状态的strur/store点后,设计两条patch:\n   (a) 在app启动/进阅读页时强制写该状态(若能定位写入点,把写入值固定为True/今天)。\n   (b) 更优: 找读取该状态的点(reader build或0xa52920的判断),反转判断让它总认为"已看"。\n3. 交叉: 写入的field必须与读取点(C2)的field一致才能生效。核对C2读的G+0xed0/+0x1028 vs C1/C4写的field。\n4. 字节级给patch(地址+原字节+补丁字节+栈平衡)。\n给出: 写入点精确地址 + 强制已看patch(两条) + 为何app自己逻辑会因此隐藏块。',
  },
]

var vipAgents = [
  {
    agent_id: 'V1-vip-grant-check',
    prompt: CTX + '\n\n【VIP深挖V1: VIP会员校验/授予函数 + VIP隐藏块】\n用户提VIP可能也去除块。找VIP相关全链。\n方法:\n1. unflutter_strings搜 VIP/vip/会员/永久/开通/去广告/免广告/永久免广告/尊享/激活/订阅/premium/membership/subscribe/adVip/noAds/removeAds/恢复购买 等关键词及其ref。\n2. scan_slot这些VIP串的loader→这些函数。找"是否有VIP"判断函数(读VIP状态bool)和"授予VIP"函数(写VIP状态)。\n3. ★关键: VIP状态字段在哪(全局G=Thread[x26+0x80]的哪个field?或某对象field)?它和喵喵块caller 0xa52920读的G+0xed0/+0x1028是否相关?是否VIP=true时0xa52920返回obj44988空块(C2假设)?\n4. 反汇编"是否有VIP"判断函数,找它读取的精确field。设计强制VIP=true的patch(改判断为常True,或写VIP field)。\n5. 区分: 首页overlay的VIP(0xbd2e1c已根治)用的VIP字段 vs 喵喵块的VIP字段——同一字段还是不同?若是同一,overlay根治已间接说明VIP字段位置,可复用。\n给出: VIP字段精确地址 + 强制VIP patch + 是否能隐藏喵喵块。',
  },
  {
    agent_id: 'V2-device-binding',
    prompt: CTX + '\n\n【机器码绑定深挖V2: 设备ID/机器码读取 + 绑定验证】\n用户提到VIP涉及"绑定机器码"。找设备绑定逻辑(可能VIP授权绑定设备)。\n方法:\n1. unflutter_strings搜 机器码/设备/device/deviceId/androidId/uuid/绑定/解绑/授权/激活码/恢复/transfer/limit/超限/绑定设备 等及其ref。\n2. 找读取设备唯一标识的函数(android_id/uuid/序列号)。这通常是VIP授权绑定的依据。\n3. 找绑定验证逻辑(本地校验设备是否已授权VIP)。是否有本地VIP缓存(SharedPreferences相关,像首启已用的flutter.ensureDeclare)?\n4. 若VIP是本地缓存校验(非纯服务端),强制本地"已授权VIP"可能可行(类似首启SP预写)。找VIP本地缓存key/字段。\n5. 评估: 机器码绑定是本地校验还是必须服务端?若纯本地→强制可行;若服务端→静态patch无效(需hook网络,但frida不可用)。诚实区分。\n给出: 设备绑定逻辑位置 + VIP校验是本地还是服务端 + 若本地则强制授权patch。',
  },
]

phase('TraceChain')
var chainResults = await parallel(
  chainAgents.map(function (a) {
    return function () {
      return agent(a.prompt, { label: a.agent_id, phase: 'TraceChain', schema: SCHEMA })
    }
  })
)

phase('VIP')
var vipResults = await parallel(
  vipAgents.map(function (a) {
    return function () {
      return agent(a.prompt, { label: a.agent_id, phase: 'VIP', schema: SCHEMA })
    }
  })
)

var allFound = chainResults.filter(Boolean).concat(vipResults.filter(Boolean))
log('追链+VIP完成: hide分支判定 ' + allFound.map(function (r) { return r.agent_id + '=' + r.found_hide_branch; }).join(', '))

// Collect best hide-branch patches for adversarial verification
var hidePatches = allFound.filter(function (r) { return r.patch_candidate && r.patch_candidate !== '无'; })

phase('Verify')
var verify = await agent(
  CTX + '\n\n【对抗验证: 最优"让app自己隐藏块"patch的可行性与安全性】\n下面是追链+VIP的结构化发现:\n' +
  JSON.stringify(allFound, null, 1) +
  '\n\n请对抗验证(默认存疑,字节级):\n1. 这些找到的"隐藏分支/状态字段"中,哪个最可信(字节证据最硬)?交叉核对C1写入field vs C2读取field是否一致(不一致则patch无效)。\n2. ★最关键验证: C2假设"0xa52920有if看过return obj44988分支"——反汇编0xa52920核实到底有没有这个分支。若有,精确给分支地址+tbnz指令+强制跳空分支的字节patch。若没有,诚实说明0xa52920两分支只是猫饿/猫饱图标(块常显)。\n3. 任何"强制状态/反转判断"patch的栈平衡、副作用、崩点预判(强制VIP/已看会不会导致别的地方崩,如广告计数乱)。\n4. 对比: 状态法(app自己隐藏,绕开cid墙) vs Patch D(0xa52c68 field-null,动块本身)——哪个更优?给出主控推荐顺序。\n5. 区分: 哪些是"静态确定可行",哪些"需主控patch-and-test"。',
  { label: 'verify', phase: 'Verify', schema: {
    type: 'object',
    properties: {
      best_state_approach: { type: 'string', description: '最可信的状态法方案(若C2分支存在则给精确patch;若无则说明块常显状态法落空)' },
      c2_branch_verified: { type: 'string', enum: ['exists-exact', 'exists-candidate', 'does-not-exist', 'uncertain'], description: 'C2核心假设(0xa52920有隐藏分支)验证结果' },
      field_consistency: { type: 'string', description: 'C1写入field与C2读取field是否一致(决定状态法patch是否有效)' },
      recommendation: { type: 'string', description: '主控推荐测试顺序: 状态法 vs Patch D vs obj44988 vs 兜底' },
      crash_risks: { type: 'string', description: '强制状态/VIP的副作用崩点预判' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    },
    required: ['best_state_approach', 'c2_branch_verified', 'field_consistency', 'recommendation', 'crash_risks', 'confidence'],
  } }
)

return { chain: chainResults.filter(Boolean), vip: vipResults.filter(Boolean), verify: verify, hidePatchesCount: hidePatches.length }
