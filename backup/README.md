# 皮皮喵项目 · 成果备份（backup 分支）

本分支是**第五轮结束时的完整成果备份**，用于防丢 + 方便将来新版本快速对照 patch。

## 目录结构

```
backup/
├── 进度文档-第五轮.md      ← ★核心：所有地址/patch/方法/教训/待办（先读这个）
├── README.md               ← 本文件
├── libapp/
│   ├── libapp_arm64_clean.so          ← 原始干净 libapp.so（patch 基线）
│   └── libapp_arm64_dialogpatched.so  ← 已含篡改窗 patch（0x8e1dd0/0x8ef2b8 → return null）
├── apk/
│   └── 皮皮喵修改-第五轮弹窗已破.apk   ← 当前可用 APK（篡改窗已破，故障窗可点掉继续）
└── smali-hooks/
    ├── PmsHook.smali       ← 签名 spoof（伪造原版 SigningInfo）
    ├── Dbg.smali           ← 探针 spoof + 诊断日志
    ├── App.smali           ← 自定义 Application，装 PMS 代理
    └── BaseApplication.smali
```

## 快速还原

1. **libapp patch 还原**：把 `libapp/libapp_arm64_dialogpatched.so` 替换进 APK 的 `lib/arm64-v8a/libapp.so`
2. **smali hook 还原**：把 `smali-hooks/*.smali` 放回 apktool 反编译树的对应位置
3. `apktool b -f` + uber-apk-signer 重签 + 装机

## 当前可用状态

- ✅ 脱壳、签名墙破、篡改窗破
- ⚠️ 故障窗（广告失败提示）：启动后弹一次，点"确定"可过，**非硬阻断**
- 待办：功能反射报错、开屏广告、VIP/更新、最终清理

详见 `进度文档-第五轮.md`。
