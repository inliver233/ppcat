# 第十四轮 `ppcat-prepool` VM lookup 实验

目标：验证 `unflutter ppcat-prepool` 是否能通过引入 `VM snapshot` lookups，提升 `NamedObject / Code` 的名字恢复率。

## 输入

- 原始样本：`lib/arm64-v8a/libapp.so`
- 旧产物：`lib/arm64-v8a/libapp.unflutter/ppcat-prepool/`
- 本轮导出的 patch：
  - `analysis_round14/unflutter_ppcat_prepool_vm_lookup.patch`

## 实验改动

1. `internal/pipeline/helpers.go`
   - `ResolveName()` 增加 `VmRefToStr` 回退
   - `ResolveOwnerName()` 增加 `VmRefToNamed` 回退
2. `cmd/unflutter/cmd_ppcat_prepool.go`
   - 额外构建 `vmResult`
   - `ppcat-prepool` 导出时走 `buildPoolLookups(..., vmResult)`

## 本地验证命令

```bash
cd unflutter
go test ./cmd/unflutter ./internal/pipeline ./internal/cluster
go run ./cmd/unflutter ppcat-prepool ../lib/arm64-v8a/libapp.so --out /tmp/ppcat-prepool-vm2

python3 /root/ppcat_repo/analysis_round14/compare_prepool_outputs.py \
  /root/ppcat_repo/lib/arm64-v8a/libapp.unflutter/ppcat-prepool \
  /tmp/ppcat-prepool-vm2
```

## 量化结果

```text
metric                    old   new   delta
named.name_nonempty      4763  6576  +1813
named.owner_name_nonempty 455   560   +105
codes.name_nonempty         0     0     +0
codes.owner_name_nonempty   0     1     +1
codes.full_name_nonempty    0     0     +0
```

## 当前结论

- 这条增强对 `NamedObject` 层**确实有效**
- 它证明 `VM/base refs` 是当前名字恢复缺失的一部分根因
- 但它**还没有**把 `Code -> owner -> full_name` 真正打通
- 当前更适合把这条路线视为 `test1` 的工具层增量，而不是已经完成的业务函数名恢复

## 典型新增样本

- `owner_name = "opaque"`
- `owner_name = "floatingActionButton"`
- `owner_name = "Uint8List"`
- `name = "皮皮喵"`

## 仍未覆盖的业务层关键名

以下目标在这轮增强后仍未直接恢复进 `named.json`：

- `remoteConfigSign`
- `rewardTime`
- `showSplashAd`
- `onReward`
- `expiresDate`

这说明下一步还需要继续处理：

- `owner_ref_id` 大量落在 `res.Named` 之外的问题
- `Code.owner_ref` 与 `NamedObject` 之间的跨快照/跨对象桥接
