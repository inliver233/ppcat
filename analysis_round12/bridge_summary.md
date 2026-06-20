# 第十二轮协作桥接小结

本目录的目标不是“复制 test3 结论”，而是把 `origin/test3` 的通用分析脚本桥接到 `test1` 当前仓库布局里，形成可复跑、可交叉验证的共享工具层。

## 已桥接并在 test1 复跑成功

- `taskA_deserialize.py`
  - 为 test3 的 `analysis_workdir` 脚本提供兼容接口
  - 输出结构与 test3 脚本预期一致
- `gen_artifacts_test3.py`
  - 已成功生成：
    - [KEY_REFS_MAP_from_test3_scripts.txt](/root/ppcat_repo/analysis_round12/KEY_REFS_MAP_from_test3_scripts.txt)
    - [POPUP_SURVEY_from_test3_scripts.txt](/root/ppcat_repo/analysis_round12/POPUP_SURVEY_from_test3_scripts.txt)
- `master_map_test3.py`
  - 已在 test1 上跑通
  - 输出与 `test1` 现有锚点一致
- `vip_getters_test3.py`
  - 已在 test1 上跑通
  - 能稳定枚举 `expiresDate / expires / gentle.com / 绑定 / 已生效 / 已绑定账号` 等候选
- `find_orchestrators_test3.py`
  - 已在 test1 上跑通
  - 复现了“每日喂喵 title/body 不落同一函数”“故障 title/body 目前也无共同静态 accessor”的结论
- `vip_deep_test3.py`
  - 已在 test1 上跑通
  - 但关键词过宽，当前噪声较大，更适合作为后续二次裁剪基础

## 已确认与 test1 现有结论一致的点

- `27673 -> slot 0x276e -> func 0x920d7c`
- `21707 -> slot 0x59bb -> funcs 0x846b1c / 0xa54178 / 0xae71bc`
- `22466 -> slot 0x9912 -> func 0xb68234`
- `8910 / 13169 -> funcs 0xa54178 / 0xb9fc84`
- `7406 -> 0x8ba3d0`
- `12056 -> 0x67994c`
- `5520 / 23584 / 11225 / 20086` 的更新链落点
- `POPUP_SURVEY` 中 `0xa54178 / 0xb9fc84 / 0x8a0fd4 / 0x85efd4 / 0x913bf8` 的归类方向

## 这层桥接的价值

1. `test1` 现在可以直接复用 `test3` 的对象池/映射脚本思路，而不是每次只参考报告。
2. 新脚本的输出属于 `test1` 本地复跑结果，因此可以安全用于：
   - 报告增补
   - 继续裁剪更窄的 `VIP/noAd` 候选链
   - 和 `test2/test3` 做逐项交叉验证
3. 这也为后续把 `analysis_round12` 再整理成正式共享工具集打下了基础。

## 当前限制

- `vip_deep_test3.py` 的关键词太宽，含大量 `proxy/progress/protocol` 噪声，不能直接当成高信号 `VIP getter` 工具。
- `find_orchestrators_test3.py` 仍只能说明“静态同函数 accessor 不存在”，还不能直接给出每日喂喵或残留故障窗的 show 编排器。
- 这层桥接目前主要解决“工具复用”，还没有直接产出新的 `VIP` 单点 patch。
