#!/usr/bin/env python3
# 从原始 libapp_orig.so 打补丁生成目标配置。完全可复现。
# 用法: python patch_libapp.py <config> <out_so>
#   config: testC | testC_master | master_only | ...
import sys

ORIG = "E:/皮皮喵4/work/libapp_orig.so"

# ---- 补丁定义 ----
P_TAMPER = [  # 篡改窗 (反篡改, return null)
    (0x8e1dd0, bytes.fromhex("e00316aac0035fd6")),
    (0x8ef2b8, bytes.fromhex("e00316aac0035fd6")),
]
P_FAULT_GATE = [(0xbc1020, bytes.fromhex("00020054"))]  # 故障门控
P_DIALOG_NOP = [  # dialog-show BL NOP (故障/弹窗显示)
    (0xbc1058, bytes.fromhex("1f2003d5")),
    (0xbc1134, bytes.fromhex("1f2003d5")),
    (0xbc1234, bytes.fromhex("1f2003d5")),
    (0xbd60ac, bytes.fromhex("1f2003d5")),
    (0xbd6264, bytes.fromhex("1f2003d5")),
    (0xbd6300, bytes.fromhex("1f2003d5")),
    (0xbd6130, bytes.fromhex("1f2003d5")),
]
P_MASTER_TRUE = [(0x7e8540, bytes.fromhex("69000014"))]   # isNoAdLock 强制True=全局免广告
P_MASTER_FALSE = [(0x7e8540, bytes.fromhex("6d000014"))]  # 语义反转备用
P_MASTER_ALT = [(0x7e85f4, bytes.fromhex("07000014"))]    # test2 备选点
P_REWARD_SKIP = [(0xba0bbc, bytes.fromhex("7f000014"))]   # reward/喵喵饿了跳过
P_SPLASH_NOP = [  # test2 §5.9 开屏控制器 0x8863e8 内4个 dialog BL NOP (管WebView开屏,验证安全)
    (0x886564, bytes.fromhex("1f2003d5")),
    (0x886638, bytes.fromhex("1f2003d5")),
    (0x8868ec, bytes.fromhex("1f2003d5")),
    (0x8869d4, bytes.fromhex("1f2003d5")),
]


P_FAULT_BODY = [(0x920d90, bytes.fromhex("29000014"))]  # ★test3突破: 截断故障body唯一源0x920d7c入口->null尾声
P_MIAO_NOCIRCLE = [(0xae312c, bytes.fromhex("c10d0014"))]  # test2: 喵喵饿了builder B.NE->B(走PATH_B)




# test3第九轮: 返回const SizedBox.shrink(slot0x3975)配方 - 5word
def _sizedbox_patch(addr):
    return [(addr, bytes.fromhex('60734091')),     # add x0,x27,#0x1c,lsl12
            (addr+4, bytes.fromhex('00d445f9')),    # ldr x0,[x0,#0xba8]=SizedBox.shrink
            (addr+8, bytes.fromhex('ef031daa')),    # mov x15,x29
            (addr+12, bytes.fromhex('fd79c1a8')),   # ldp x29,x30,[x15],#0x10
            (addr+16, bytes.fromhex('c0035fd6'))]   # ret
P_OVERLAY = _sizedbox_patch(0xbd2e24)
P_MIAO_B = [(0xc3def8, bytes.fromhex("e00316aa")),(0xc3defc, bytes.fromhex("fd79c1a8")),(0xc3df00, bytes.fromhex("c0035fd6"))]  # test3候选B: 浮窗选择器0xc3def0 entry-null
  # 首页overlay编排器0xbd2e1c的func+8

P_MIAO_A54178 = [(0xa5418c, bytes.fromhex("e00316aa")), (0xa54190, bytes.fromhex("92090014"))]  # 第八轮实验: 0xa54178 VIP/喵喵页build入口return null(定位喵喵块)

P_MIAO_PATHA = [(0xae312c, bytes.fromhex("1f2003d5"))]  # 第八轮: b.ne->NOP 强制总走PATH_A(配合PATH_A return null=块消失)

P_MIAO_NULL = [(0xae32d4, bytes.fromhex("e00316aa"))]  # test3方案B: 喵喵build return null(0xae32d4 mov x0,x1->mov x0,x22)

P_MIAO_NOCLICK = [(0xbc5dd0, bytes.fromhex("e00316aa")),(0xbc5dd4, bytes.fromhex("fd79c1a8")),(0xbc5dd8, bytes.fromhex("c0035fd6"))]  # test3方案C: reward-prompt不可点击(已验证)

P_ADFAIL_NOP = [
    (0x883d18, bytes.fromhex("1f2003d5")),
    (0x883dd8, bytes.fromhex("1f2003d5")),
    (0x883e2c, bytes.fromhex("1f2003d5")),
    (0x87b818, bytes.fromhex("1f2003d5")),
    (0x87b8d0, bytes.fromhex("1f2003d5")),
    (0x87ba84, bytes.fromhex("1f2003d5")),
    (0x87bad8, bytes.fromhex("1f2003d5")),
    (0x87b224, bytes.fromhex("1f2003d5")),
    (0x87b2e4, bytes.fromhex("1f2003d5")),
    (0x87b504, bytes.fromhex("1f2003d5")),
    (0x87b558, bytes.fromhex("1f2003d5")),
    (0x878b68, bytes.fromhex("1f2003d5")),
    (0x878bec, bytes.fromhex("1f2003d5")),
    (0x878c40, bytes.fromhex("1f2003d5")),
    (0x87ce10, bytes.fromhex("1f2003d5")),
    (0x87ce7c, bytes.fromhex("1f2003d5")),
    (0x87ced0, bytes.fromhex("1f2003d5")),
    (0x881a68, bytes.fromhex("1f2003d5")),
    (0x881b00, bytes.fromhex("1f2003d5")),
    (0x881bdc, bytes.fromhex("1f2003d5")),
    (0x881c68, bytes.fromhex("1f2003d5")),
    (0x881cbc, bytes.fromhex("1f2003d5")),
]
P_FAULT3_NOP = [  # ★第八轮发现: 故障弹窗第三源 0xc4cb30 (调0x920d7c故障body) 的4个showDialog BL
    (0xc4cc2c, bytes.fromhex("1f2003d5")),
    (0xc4ccac, bytes.fromhex("1f2003d5")),
    (0xc4ce0c, bytes.fromhex("1f2003d5")),
    (0xc4ce60, bytes.fromhex("1f2003d5")),
]
P_UPDATE_NOP = [(0x8667a8, bytes.fromhex("1f2003d5")),
                (0x8675bc, bytes.fromhex("1f2003d5"))]    # 更新窗 NOP

CONFIGS = {
    "testC":        P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP,
    "testC_fault3": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT3_NOP,
    "testC_faultbody": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT_BODY,  # ★test3故障弹窗根治
    "testC_faultbody_miao": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT_BODY + P_MIAO_NOCLICK,
    "testC_miao_all": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT_BODY + P_MIAO_NULL + P_MIAO_NOCLICK,
    "testC_miao_hide": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT_BODY + P_MIAO_PATHA + P_MIAO_NULL,
    "testC_miao_a54178": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT_BODY + P_MIAO_A54178,
    "testC_overlay": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT_BODY + P_OVERLAY,
    "testC_miaoB": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT_BODY + P_MIAO_B,  # 故障根治+喵喵块候选B(0xc3def0 entry-null)  # ★test3: 故障根治+首页overlay(SizedBox.shrink)  # ★实验: 故障根治+0xa54178 return null  # 故障根治+强制PATH_A+return null=喵喵块消失  # 故障根治+喵喵B(return null)+C(不可点击)  # 故障根治+喵喵不可点击
    "testC_adfail": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_FAULT3_NOP + P_ADFAIL_NOP,
    "testC_master": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_MASTER_TRUE,
    "master_only":  P_TAMPER + P_FAULT_GATE + P_MASTER_TRUE,
    "testC_masterF":P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_MASTER_FALSE,
    "testC_masteralt": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_MASTER_ALT,
    "testC_master_reward": P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_MASTER_TRUE + P_REWARD_SKIP,
    "testC_splash":     P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_SPLASH_NOP,        # 只加开屏NOP(隔离测开屏)
    "testC_reward":     P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_REWARD_SKIP,      # 只加reward跳过(隔离测喵喵饿了)
    "testC_all":        P_TAMPER + P_FAULT_GATE + P_DIALOG_NOP + P_SPLASH_NOP + P_MASTER_TRUE + P_REWARD_SKIP + P_UPDATE_NOP,
}

def main():
    cfg = sys.argv[1]
    out = sys.argv[2]
    if cfg not in CONFIGS:
        print(f"未知配置: {cfg}; 可用: {list(CONFIGS)}"); sys.exit(1)
    patches = CONFIGS[cfg]
    d = bytearray(open(ORIG, "rb").read())
    print(f"配置 [{cfg}]: 从原始({len(d)}字节)打 {len(patches)} 处补丁")
    for off, b in patches:
        old = d[off:off+len(b)].hex()
        d[off:off+len(b)] = b
        print(f"  0x{off:07x}: {old} -> {b.hex()}")
    open(out, "wb").write(d)
    print(f"写出 {out} ({len(d)} 字节)")

if __name__ == "__main__":
    main()
