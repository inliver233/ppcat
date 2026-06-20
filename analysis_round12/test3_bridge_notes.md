# test3 -> test1 协作桥接说明

目的：

- 把 `origin/test3:analysis_workdir/` 里更完整的对象池/函数映射脚本，当作 `test1` 的协作资源使用
- 但不直接照抄结论，而是在 `test1` 当前工作树里复跑、复核、产出自己的结果

当前处理方式：

1. 从 `origin/test3` 抽取这些脚本到 `analysis_round12/`
   - `master_map_test3.py`
   - `find_orchestrators_test3.py`
   - `gen_artifacts_test3.py`
   - `taskB_precise_test3.py`
   - `taskC_vip_test3.py`
   - `vip_getters_test3.py`
   - `vip_deep_test3.py`
2. 在 `analysis_round12/taskA_deserialize.py` 提供兼容层：
   - 暴露 `data`
   - 暴露 `parse_pool(0x2e7043, 51140)`
   - 返回 `test3` 脚本所需的 entry tuple 结构
3. 脚本路径已改成适配 `test1` 的仓库布局：
   - `analysis_round6/pool_accesses.txt`
   - `libapp.so`
   - `unflutter_strings.txt`

注意：

- 这些脚本来自 `test3`，但在 `test1` 上复跑之前，不应把它们的结论直接写入主报告
- 只有 `test1` 本地成功跑通并与现有锚点/报告一致的部分，才应转成正式产物或报告增补
