# ppcat

Flutter 应用 Dart 代码恢复 —— 静态分析项目。

## 文件结构

```
任务文档.md        ← 必读:完整的分析任务说明(环境、步骤、目标、输出)
已知信息.md        ← 必读:前期已确认的技术细节(字符串偏移、期望值、架构)
lib/
  arm64-v8a/       ← 主分析目标
    libapp.so        Dart AOT 业务逻辑
    libflutter.so    Flutter 引擎(blutter 探测 Dart 版本用)
  armeabi-v7a/     ← 32 位版本(备用)
    libapp.so
    libflutter.so
```

## 快速开始

1. 读 `任务文档.md` 和 `已知信息.md`
2. 按任务文档第二节配置 Linux 环境
3. 用开源工具 blutter(https://github.com/worawit/blutter )反汇编 `lib/arm64-v8a/`
4. 按"重点 1/2/3"定位逻辑,产出 `分析报告.md`

详情见 `任务文档.md`。
