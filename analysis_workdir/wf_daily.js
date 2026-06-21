export const meta = {
  name: 'ppcat-daily-reward-hide-switch',
  description: '锁定喵喵块隐藏开关:用户确认"每日喂喵"奖励系统完成后块消失。找reward成功→daily状态→块的调用者层隐藏判断(精确patch让app自己隐藏)',
  phases: [
    { title: 'Lock', detail: '5路并行锁定:reward完成回调sink/daily状态字段/块调用者层隐藏门/0x846链与块联动/onTap去向' },
    { title: 'Verify', detail: '对抗验证最优隐藏patch+交叉test1 0x846链' },
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
  'function_summary.txt、pool_accesses.txt、capstone 5.0.7可用。Python3可写脚本。',
  '',
  '调用约定: X15=影子栈,X26=Thread,X27=Pool(PP),X22=null,X28=heap base。',
  '序言: stp x29,x30,[x15,#-0x10]!; mov x29,x15 (fd79bfa9 fd030faa)。',
  '尾声: mov x15,x29(ef031daa); ldp(fd79c1a8); ret(c0035fd6)。func+8=序言后第一条(0x+8)。',
  'bool: add xR,x22,#0x30=True / #0x20=False。tbnz/tbz w0,#4 测bool(bit4)。csel按eq选。',
  'PP slot加载: add xR,x27,#page lsl12 + ldr xD,[xR,#off]，slot=(page+off)/8。',
  'Thread全局状态G=Thread[x26+0x80]，再读G.field@0xXXX。对象分配thunk: mov x2,#imm;movk x2,#cid,lsl16;ldr x4,[x26,#0x228];br x4。',
  '',
  '【★ 用户确认的ground truth(本轮最高优先级事实)】',
  '1. 喵喵块=阅读页悬浮Button[720,1260][1080,1392] content-desc="喵喵饿了"。用户【已实测】: 完成"每日喂喵"投喂奖励流程后,阅读页喵喵块【消失】。这是app原生隐藏路径,真实存在!',
  '2. 【★关键】: 设置页"每日喂喵"按钮 和 阅读页"喵喵饿了"悬浮块 是【同一套奖励系统】(用户原话"设置页和漫画页的喵喵饿了是一个东西")。流程: 点击→"是否看推荐获取喵粮喂喵?获取/取消"→点获取→广告1秒+倒计时29→"我要更快拿奖"跳转外部应用(淘宝/微信小程序)→浏览10秒→手动返回app→"恭喜获得奖励 已完成浏览10秒提前获得奖励"→状态从"饿了喵"变"喵喵喵~"→【阅读页喵喵块消失】。',
  '3. 【★关键区分】: 设置页有5个特权项:喵喵特权/每日特权/每日喂喵/免广告特权/(等)。只有"每日喂喵"与"喵喵饿了"互通。其他3个(VIP特权类)是独立体系,【不】控制这个块。VIP路线是死路(全app无VIP字符串,wf_state S2已证)。',
  '4. 用户机器当前处于"已完成投喂"状态,喵喵块已消失=活的证据。证明隐藏判断真实生效。',
  '',
  '【已知技术背景】',
  'A. 喵喵块builder: 0xa52bb0(返回cid0xaf7 widget, 无隐藏分支,字节铁证)。caller 0xa52920(建内容child cid0xacd后tail-call 0xa52bb0,也无隐藏分支)。0xa52920读G.field@0x1028和G.field@0xed0,但两分支只切猫饿/猫饱内容(slot0xbb8 vs slot0xbc0),都继续建块。【builder层无隐藏开关,隐藏判断必在builder的调用者层】。',
  'B. 0xa52920 callers=[](pool间接,reader build经pool间接调它)。reader build静态不可精确定位(pool间接+blutter cid84墙)。候选0xbf9be8低置信。',
  'C. test1(Ghidra)发现: 0xa56c34(喂饱toast 0xa56be4之后)写G.field@0xee0=True + G.field@0xea0(秒时间戳),有3个caller(0xa56be4/0xa56f60/0xa57010)=reward/完成共用写状态sink。0x846b1c(串"每日喂喵"ref21707)→0x846f30(bool门,读param.field@0x47比较,非读G+0xee0)。',
  'D. slot0x753(obj44988,byteoff0x3a98):app在0x546760"尺寸==0"分支返回的"渲染空"const Widget,231加载,cid!=0xaf7。',
  'E. 喂猫逻辑0xb68234(串"每天喂一次喵喵就不来找你了~"ref22466),读obj.field@0x33(猫饿bool)喂后置FALSE。0xa56e00(callers=4)。reward-prompt 0xbc5dc8(串"是否看推荐获取喵粮喂喵？"ref18266 slot0x8a37)。',
  '',
  '【本轮核心目标】用户思路已确认可行(奖励完成→块消失是原生路径)。任务: 静态锁定这条隐藏判断的精确位置——【谁读daily/reward完成状态后,决定不构造/不挂载喵喵块】,给出"强制该状态=已奖励完成→app自己隐藏块"的patch(绕开cid墙,比动builder干净)。这是整个项目最后一里路。',
  '',
  '【诚实要求】test3已4次误判。绝不要把"看到状态读取"等同于"找到隐藏开关"。每结论标注 静态确定/推断/需主控验证。字节级证据+交叉验证(≥2法)。区分:builder层(已证无开关) vs 调用者层(待找) vs reward回调(写状态)。',
].join('\n')

var SCHEMA = {
  type: 'object',
  properties: {
    agent_id: { type: 'string' },
    core_finding: { type: 'string', description: '核心发现(2-4句)。是否锁定了隐藏判断的精确位置?' },
    locked_switch: { type: 'string', enum: ['yes-exact-patch', 'yes-candidate', 'no-not-found', 'uncertain'], description: '是否锁定"读daily状态→不构造块"的隐藏开关' },
    method: { type: 'string', description: '实际验证(命令/反汇编/脚本)' },
    byte_evidence: { type: 'string', description: '字节级证据:地址+字节+反汇编+推理' },
    switch_location: { type: 'string', description: '若锁定,给精确:隐藏判断在哪(函数@addr 的 tbnz/cbz偏移,或读哪个状态字段G+0xXXX/per-object field@0xXX)。无填未找到。' },
    patch_candidate: { type: 'string', description: '可行patch(强制状态=已奖励完成→app自己隐藏块),地址+原字节+补丁字节+为何app自己逻辑会隐藏+栈平衡。无填无。' },
    confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
    caveats: { type: 'string', description: '不确定性/崩点预判/需主控验证' },
  },
  required: ['agent_id', 'core_finding', 'locked_switch', 'method', 'byte_evidence', 'switch_location', 'patch_candidate', 'confidence', 'caveats'],
}

var locks = [
  {
    agent_id: 'L1-reward-complete-sink',
    prompt: CTX + '\n\n【锁定L1: reward完成→写daily状态的精确sink指令】\n用户确认"完成浏览10秒提前获得奖励"→块消失。找"恭喜获得奖励/完成浏览"后的状态写入。\n方法:\n1. unflutter_strings搜 恭喜获得/已完成浏览/提前获得奖励/获得奖励/10秒/浏览/奖励/reward/success 等串及其ref→loader。\n2. 这些"成功"串的loader函数,在显示toast后一定调一个写状态函数(很可能就是test1说的0xa56c34)。核实0xa56c34的3个caller(0xa56be4/0xa56f60/0xa57010)哪个对应"浏览10秒奖励成功"。反汇编0xa56f60和0xa57010。\n3. ★精确定位写daily状态的那条str/stur指令(写G+0xee0还是别的field)+写入的值。给指令地址+原字节。\n4. 追这个写入的field被谁读(交叉L2/L3)。\n给出: reward完成写daily状态的精确指令地址+字段+值。',
  },
  {
    agent_id: 'L2-block-caller-gate',
    prompt: CTX + '\n\n【锁定L2(最高价值): 喵喵块"调用者层"的隐藏判断门】\nbuilder 0xa52920无隐藏分支(已证),故隐藏判断在调用0xa52920之前。caller是reader build(pool间接不可定位)。换路: 既然0xa52920 callers=[],但它被pool间接调——找reader build加载0xa52920的Code对象slot的位置,看该BL前是否有tbnz/cbz daily状态判断跳过它。\n方法:\n1. 全.text扫描: 哪些pool slot(经scan_slot)指向0xa52920的Code? 用scan_slot找0xa52920相关的Code slot(难,因Code簇未解)。替代: 反汇编reader候选0xbf9be8(31112B),找它体内是否有"读daily状态→tbnz→跳过构造块"的模式,即使pool间接。\n2. 更直接: 既然0xa52920构造块,而0xa52920自己的caller不可见——看0xa52920【本身】的入口前是否就是判断(有时Dart把判断内联在调用者但builder 0xa52920作为独立函数,判断应在更上层)。\n3. ★最有效: 找"喵喵饿了"(ref28525)的const widget在哪个函数被加载进Stack.children——那个函数(可能是块的外层Positioned/Container builder)读daily状态决定是否加。scan_slot喵喵簇slot(0x3678-0x368d)所有loader,找reader区大函数,看它读daily状态(field@0x47或G+0xee0)后是否跳过slot加载。\n4. 验证test1的0x846b1c/0x846f30链:它是否是悬浮块的显示门(而非仅设置页按钮)。反汇编0x8466c0(0x846f30的caller)和0x846690(0x846b1c的caller),看它们是否调0xa52920或加载喵喵簇。\n给出: 调用者层隐藏判断的精确位置(若找到)。',
  },
  {
    agent_id: 'L3-daily-state-field',
    prompt: CTX + '\n\n【锁定L3: daily/reward完成状态的精确字段(区分写与读)】\nreward成功写某状态(L1找的写入点),块隐藏读某状态(L2找的读取点)。确认这俩是【同一字段】(否则patch无效)。test1说写入G+0xee0,但0x846f30读的是per-obj field@0x47——核对到底哪个是真daily字段。\n方法:\n1. 反汇编0xa56c34完整,精确确认它写哪些字段(G+0xee0? G+0xea0? per-obj?)。字节级。\n2. 全.text扫描读G+0xee0的102个点(imm12=0x1dc),逐个看所属函数——哪个函数【同时】加载喵喵簇slot(0x3678-0x368d/0xbb8/0xbc0)或构造块?那个就是块的隐藏门。可写脚本:对每个G+0xee0读取点,反汇编其所属函数,检测是否含喵喵簇slot加载或bl cat模块(0xa5xxxx-0xa54xxxx)。\n3. 同时扫per-object field@0x47(0x846f30读的)的读取点,看是否与喵喵块联动。\n4. 关键结论: daily状态字段是G+0xee0(全局)还是per-obj field@0x47?写点(L1)和读点(L2)是否同字段?\n给出: daily字段精确地址 + 读写一致性判定。',
  },
  {
    agent_id: 'L4-846chain-block-link',
    prompt: CTX + '\n\n【锁定L4: 验证test1的0x846b1c/0x846f30链 与 悬浮块的真实联动关系】\ntest1认为0x846链是"每日喂喵显示门"。用户确认"每日喂喵"和"喵喵饿了"是同一系统。核实0x846链是否直接控制悬浮块。\n方法:\n1. 反汇编0x846690(0x846b1c caller)和0x8466c0(0x846f30 caller)完整。它们是设置页"每日喂喵"按钮的build,还是悬浮块的外层?\n2. ★关键: 这俩caller是否调0xa52920/0xa52bb0(构造悬浮块),或加载喵喵簇slot?若否→0x846链是设置页按钮,与悬浮块间接联动(共享daily状态)而非直接构造悬浮块。\n3. 追0x846f30读的per-obj field@0x47状态对象从哪来(param链)。它和悬浮块构造链(0xa52920读G+0xed0)是否共享状态对象?\n4. 反汇编0x846b1c完整,确认它return null(false分支)时,这个null是给谁用(设置页按钮列表的某项?还是悬浮块容器?)。\n给出: 0x846链与悬浮块是直接构造关系还是间接(共享状态)。决定能否直接patch 0x846链隐藏悬浮块。',
  },
  {
    agent_id: 'L5-ontap-reward-path',
    prompt: CTX + '\n\n【锁定L5: 悬浮块onTap→reward回调→写daily状态 的完整路径】\n用户:点悬浮块→同样跳转流程→奖励→块消失。追悬浮块onTap回调链到reward成功写daily状态。\n方法:\n1. 悬浮块onTap在builder 0xa52bb0的field@0xb(CALL_F 0xa52c90建的回调集合)。反汇编0xa52c90完整,找回调指向哪个函数。\n2. 更直接: reward-prompt 0xbc5dc8(串"是否看推荐获取喵粮喂喵?获取/取消"ref18266)。反汇编0xbc5dc8+"获取"按钮的onSuccess回调。点"获取"→跳转外部→返回→"恭喜获得奖励"→写状态。\n3. 找"恭喜获得奖励"(搜串)的loader→它所在的回调函数→该回调末尾一定写daily状态(bl 0xa56c34或类似)。这就是L1的sink来源,从onTap侧验证。\n4. 确认: 悬浮块onTap和设置页"每日喂喵"onTap【汇合到同一个reward完成回调】(用户说两入口行为一样)。字节证据。\n给出: onTap→reward→写状态的完整链 + 是否两入口汇合。',
  },
]

phase('Lock')
var lockResults = await parallel(
  locks.map(function (l) {
    return function () {
      return agent(l.prompt, { label: l.agent_id, phase: 'Lock', schema: SCHEMA })
    }
  })
)

var found = lockResults.filter(Boolean)
log('5路锁定完成: ' + found.map(function (r) { return r.agent_id + '=' + r.locked_switch; }).join(', '))

phase('Verify')
var verify = await agent(
  CTX + '\n\n【对抗验证: 综合5路锁定, 给最优"让app自己隐藏块"patch + 交叉test1】\n5路锁定发现:\n' +
  JSON.stringify(found, null, 1) +
  '\n\n对抗验证(默认存疑,字节级):\n1. 【字段一致性命门】L1写的daily字段 vs L2/L3读的字段,是否同一?(不统一则patch无效,这是第4次误判防线)\n2. 是否真锁定了"读daily状态→不构造悬浮块"的精确指令?给最可信patch(强制daily=已奖励完成)。字节+栈平衡+崩点预判。\n3. 对比方案: 状态法(app自己隐藏) vs Patch D(0xa52c68 field-null,动builder) vs obj44988返回。哪个最优?主控推荐顺序。\n4. 与test1对账:0x846链到底管不管悬浮块?test1的乐观是否成立?\n5. 诚实区分:静态确定可行 / 需主控patch-and-test。reader build不可定位是否致命?',
  { label: 'verify', phase: 'Verify', schema: {
    type: 'object',
    properties: {
      switch_locked: { type: 'string', enum: ['yes-exact', 'yes-candidate', 'no', 'uncertain'] },
      best_state_patch: { type: 'string', description: '最优"app自己隐藏"patch:地址+原字节+补丁字节+为何会隐藏' },
      field_consistency: { type: 'string', description: '读写daily字段是否一致(命门)' },
      test1_846_chain: { type: 'string', description: 'test1的0x846链与悬浮块真实关系' },
      recommendation: { type: 'string', description: '主控推荐测试顺序' },
      confidence: { type: 'string', enum: ['high', 'medium', 'low'] },
      caveats: { type: 'string' },
    },
    required: ['switch_locked', 'best_state_patch', 'field_consistency', 'test1_846_chain', 'recommendation', 'confidence', 'caveats'],
  } }
)

return { locks: found, verify: verify }
