# 导入书源 ANR bug 修复记录（第六轮）

## 现象
点"源" → GitHub镜像站(goo.gl短链) → 点导入 → 
"No field 了 of type Ljava/lang/String; in class L了/了;" → ANR卡死

## 根因（两层，逐层揭示）
1. 第一层：classes2.dex MethodChannel内部类构造器(สۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۠ۢ)的<init>
   里 iget-object 读 field@8162（ۥ้้۟۟ۡ:String 假字段，类里不存在）→ NoSuchFieldError
   字段名混淆：ۥ้้۟۟ۡ(2个mark) vs 真channel-name ۥ้้้้۟۟ۡ(4个mark)
2. 修第一层（把field名改成4个mark的真字段）后变成：
   IllegalAccessError: Field ۥ้้้้۟۟ۡ is inaccessible —— 该字段是 private final，
   内部类直接读越权。说明原版Java编译会生成synthetic accessor（父类行68有
   ۥ้้้้۟۟ۡ()静态合成方法），但脱壳重打包丢了accessor、直接读private。

## 最终修复（干净方案）
删掉 bug 文件 <init> 里的诊断日志三行（const-string "MC" + iget private字段 + Log.i），
.locals 2→0。该段纯属打日志诊断、无功能价值，删它绕过private访问+不丢任何功能。
父类synthetic accessor 未改动（留作其他调用点用）。

## 修改文件
work/build/smali_classes2/สۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۠ۢ.smali
备份：work/buggy_innerclass.smali.bak

## 验证
- 0 FATAL / 0 IllegalAccess
- MC_P10: getAll 正常执行（test2报告的P10反射通道工作正常）
- 用户确认：正常订阅导入成功
- 启动流程不受影响（篡改窗patch仍在：0x8e1dd0/0x8ef2b8 = e00316aac0035fd6）

## 教训
test1给的byte级修复(0x4c662e e21f→e41f)只解决"找不到字段"，
但暴露了第二层"private访问性"。最终用删日志方案一劳永逸。
test2报的MC_P10 6处反射NoSuchField其实是误判/已被正常处理。
