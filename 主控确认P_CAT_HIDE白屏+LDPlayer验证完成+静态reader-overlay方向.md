# 主控确认: P_CAT_HIDE(0x466e28)在LDPlayer也白屏(双环境确证死路) + 当前状态

> 承 test3 `4273bc7`(最终交接). test3 redroid不稳,交回LDPlayer验证. 主控已在LDPlayer完成 P_CAT_HIDE 干净测试. 结果: **白屏(双环境确证)**. 设备已恢复干净版. 中性措辞"代码恢复".

## 一、★ P_CAT_HIDE 在 LDPlayer 干净测试结果(之前没真测过)

之前因 gadget APK + libapp-replace无效(houdini从APK内加载libapp) + versionCode问题, P_CAT_HIDE 从未干净验证. 现已用**正确流程**测:
- 重建干净 testC_cathide APK(vc1214, 无gadget, libapp 0x466e28=c0820091 确认)
- install -r 覆盖(书数据保留), 启动
- **结果: 白屏(uiautomator 7节点0可clickable, 无免责声明, 空屏)**

→ **P_CAT_HIDE(0x466e28→add x0,x22,#0x20=FALSE) 在 LDPlayer 和 redroid 都白屏. 死路确证.**
- 根因: guard 在共享函数 0x466dc8, 所有overlay都走. 强制FALSE=所有overlay不渲染=白屏.
- runtime flip sing+0x20→FALSE 能藏猫(无白屏)是因为一次性改值只影响那一刻; 静态改guard永久破坏所有overlay.

## 二、设备已恢复
- 重装干净 testC_ovnull APK(vc1214, 无gadget, 无cathide), 0x466e28=a0835ff8(original).
- 启动正常, 778KB截图(内容丰富,非白屏), 书数据保留.
- **干净交付版可用**: 去广告+故障根治+首页overlay清除+反篡改+首启弹窗, 猫块仍在.

## 三、★ 剩余路径(诚实)

guard 共享→静态patch白屏(死). 改builder返回值→cid崩(死). runtime flip→不可转静态. **三条直接路全死**.

唯一未穷尽的路: **阅读页专属猫overlay插入点**(首页0xbd2e1c的等价物,entry-null安全不白屏).
- 但它是 pool-indirect(无静态BL caller), 且 LDPlayer 上 Interceptor hook 不触发(houdini)→**无法在LDPlayer动态抓backtrace**.
- redroid能动态抓但环境不稳+反篡改挡.

## 四、诚实评估
猫块是**装饰性悬浮**(不影响阅读功能,只挡视线). 22轮+test3协作已根治: 广告/故障弹窗/首页overlay/反篡改/首启. 猫块的所有"直接patch"路(返回值/guard/runtime转静态)都因 cid敏感 或 共享函数 而白屏/崩.

**下一步选项**(你定):
1. **接受现状交付**: 猫块保留(只挡视线), 其他全好. 设备已是干净可用版.
2. **物理ARM设备**: 找真ARM64 root手机/树莓派, frida hook正常, 抓阅读页overlay builder(绕开houdini+redroid不稳).
3. **继续静态挖**: 主控用 pool/xref 静态找 reader build(加载章节/页码字符串的函数), 看它build的overlay树里猫的插入点. 工作量大, 不保证成功(全是pool间接).

## 五、test3成果固化(已全)
- cat cid=0x85e, ctor=0xc62438, wrapper=0xa52920
- isHungry=sing+0x20(TRUE=0x8071/FALSE=0x8061)
- guard=0x466e2c(共享函数0x466dc8内, 不可patch)
- bool格式破解, Dart对象dump方法, redroid环境搭建经验

> 一句话: P_CAT_HIDE在LDPlayer干净测试=白屏(双环境确证死路). 设备已恢复干净testC_ovnull(猫块仍在,其他全好). guard/builder/runtime三条直接路全死. 剩余:接受现状/换物理ARM设备/继续静态挖. 猫块是装饰性悬浮, 不影响功能.
