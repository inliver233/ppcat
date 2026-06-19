.class public Lcom/gentle/ppcat/hook/Dbg;
.super Ljava/lang/Object;

.method public static log(Ljava/lang/Object;)V
    .locals 2
    :try_start_0
    const-string v0, "GALL"
    invoke-static {p0}, Ljava/lang/String;->valueOf(Ljava/lang/Object;)Ljava/lang/String;
    move-result-object v1
    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0
    return-void
    :catch_0
    move-exception v0
    return-void
.end method

# log output value going back to Dart
.method public static logO(Ljava/lang/Object;)V
    .locals 2
    :try_start_0
    const-string v0, "GOUT"
    invoke-static {p0}, Ljava/lang/String;->valueOf(Ljava/lang/Object;)Ljava/lang/String;
    move-result-object v1
    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0
    return-void
    :catch_0
    move-exception v0
    return-void
.end method

# log the runtime class name of a non-String object (to diagnose Map/Object returns)
.method public static logType(Ljava/lang/Object;)V
    .locals 2
    :try_start_0
    const-string v0, "GTYPE"
    invoke-virtual {p0}, Ljava/lang/Object;->getClass()Ljava/lang/Class;
    move-result-object v1
    invoke-virtual {v1}, Ljava/lang/Class;->getName()Ljava/lang/String;
    move-result-object v1
    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0
    return-void
    :catch_0
    move-exception v0
    return-void
.end method

# Inject the 360 shell lib into the getMaps (/proc/self/maps) string so the Dart
# anti-tamper sees the shell as "loaded" (anti-deshell bypass). Original loads
# /data/data/com.gentle.ppcat/.jiagu/libjiagu_64.so (verified via /proc/<pid>/maps).
# Dart hardcodes the ".jiagu" path check. Only touches the maps listing (has libapp.so, lacks .jiagu).
.method public static injectJiagu(Ljava/lang/String;)Ljava/lang/String;
    .locals 3
    const-string v0, "libapp.so"
    invoke-virtual {p0, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v0
    if-eqz v0, :ret
    const-string v0, ".jiagu"
    invoke-virtual {p0, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v0
    if-nez v0, :ret
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v0, "\n/data/data/com.gentle.ppcat/.jiagu/libjiagu_64.so"
    invoke-virtual {v1, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object p0
    :ret
    return-object p0
.end method

# Normalize probe return values so the Dart-side anti-tamper sees the SAME values
# the original shelled app produces. All result.success callbacks route here.
.method public static sanitize(Ljava/lang/Object;)Ljava/lang/Object;
    .locals 4
    invoke-static {p0}, Lcom/gentle/ppcat/hook/Dbg;->log(Ljava/lang/Object;)V
    instance-of v0, p0, Ljava/lang/String;
    if-eqz v0, :ret_obj
    move-object v1, p0

    # getApplication probe: Dart hardcodes "com.gentle.ppcat.BaseApplication" + "android.app.Application".
    # 360 swaps the runtime Application to the real app's BaseApplication (className stays StubApp from manifest).
    const-string v2, "com.gentle.ppcat.App|com.gentle.ppcat.BaseApplication"
    const-string v3, "com.gentle.ppcat.BaseApplication|android.app.Application"
    invoke-virtual {v1, v2, v3}, Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;
    move-result-object v1

    # getAppInfo probe: ApplicationInfo.className from manifest = com.stub.StubApp (original shell).
    const-string v2, "className：com.gentle.ppcat.App"
    const-string v3, "className：com.stub.StubApp"
    invoke-virtual {v1, v2, v3}, Ljava/lang/String;->replace(Ljava/lang/CharSequence;Ljava/lang/CharSequence;)Ljava/lang/String;
    move-result-object v1

    # getMaps probe: original lacks libjiagu at probe-time too, so NO injection (match exactly).
    # invoke-static {v1}, Lcom/gentle/ppcat/hook/Dbg;->injectJiagu(Ljava/lang/String;)Ljava/lang/String;
    # move-result-object v1

    # getPMProxy probe: hide our java.lang.reflect.Proxy.
    const-string v0, "reflect.Proxy"
    invoke-virtual {v1, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v0
    if-nez v0, :replace_proxy
    const-string v0, "$Proxy"
    invoke-virtual {v1, v0}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v0
    if-eqz v0, :ret_str
    :replace_proxy
    const-string v1, "android.content.pm.IPackageManager$Stub$Proxy|java.lang.Object"
    :ret_str
    invoke-static {v1}, Lcom/gentle/ppcat/hook/Dbg;->logO(Ljava/lang/Object;)V
    return-object v1

    :ret_obj
    invoke-static {p0}, Lcom/gentle/ppcat/hook/Dbg;->logType(Ljava/lang/Object;)V
    return-object p0
.end method
