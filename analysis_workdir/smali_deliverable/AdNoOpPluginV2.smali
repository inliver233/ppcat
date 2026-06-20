.class public Lcom/gentle/ppcat/AdNoOpPluginV2;
.super Ljava/lang/Object;
.source "AdNoOpPluginV2.java"
.implements Lสۦۣ۟ۡ/สۥ۟۟ۡ;
.implements Ljava/lang/Runnable;
.implements Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;

# V2: no-op + reward simulation (delayed onRewardArrived/onAdClose on Pangle).
# Field: the Pangle MethodChannel, used to push events Java->Dart.
.field private pangleChannel:Lสۥ۠ۦۡ/สۥ۟۟۠;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

# onAttachedToEngine
.method public ۥ้้้้้้้้้้้้้้้้้้้้้้۟۟ۡ(Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;)V
    .locals 3
    invoke-virtual {p1}, Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;->ۥ้้้้۟۟ۡ()Lสۥ۠ۦۡ/สۥ۟۠ۢ;
    move-result-object v0
    new-instance v1, Lสۥ۠ۦۡ/สۥ۟۟۠;
    const-string v2, "flutter_pangle_ads"
    invoke-direct {v1, v0, v2}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V
    iput-object v1, p0, Lcom/gentle/ppcat/AdNoOpPluginV2;->pangleChannel:Lสۥ۠ۦۡ/สۥ۟۟۠;
    invoke-virtual {v1, p0}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V
    new-instance v1, Lสۥ۠ۦۡ/สۥ۟۟۠;
    const-string v2, "ksad"
    invoke-direct {v1, v0, v2}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V
    invoke-virtual {v1, p0}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V
    new-instance v1, Lสۥ۠ۦۡ/สۥ۟۟۠;
    const-string v2, "plugins.flutter.io/google_mobile_ads"
    invoke-direct {v1, v0, v2}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V
    invoke-virtual {v1, p0}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V
    new-instance v1, Lสۥ۠ۦۡ/สۥ۟۟۠;
    const-string v2, "plugins.hetian.me/gdt_plugins"
    invoke-direct {v1, v0, v2}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V
    invoke-virtual {v1, p0}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V
    return-void
.end method

# onDetachedFromEngine
.method public ۥ้้้้้้้้้้้้้้้้۟۟ۡ(Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;)V
    .locals 0
    return-void
.end method

# onMethodCall(call, result)
.method public ۥ้้้้้้้้้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۠۠;Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;)V
    .locals 3
    # read method name = call.method
    iget-object v0, p1, Lสۥ۠ۦۡ/สۥ۟۠۠;->ۥ้้۟۟ۡ:Ljava/lang/String;
    # success immediately for ALL methods (baseline no-op)
    const/4 v1, 0x0
    invoke-interface {p2, v1}, Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;->ۥ้้้้۟۟ۡ(Ljava/lang/Object;)V
    # if method contains "Reward" -> arm reward simulation
    const-string v2, "Reward"
    invoke-virtual {v0, v2}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v2
    if-eqz v2, :cond_no_reward
    # ensure pangleChannel != null
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV2;->pangleChannel:Lสۥ۠ۦۡ/สۥ۟۟۠;
    if-eqz v2, :cond_no_reward
    # spawn a Thread(this) to sleep then send events (bypass anti-cheat time threshold)
    new-instance v2, Ljava/lang/Thread;
    invoke-direct {v2, p0}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V
    invoke-virtual {v2}, Ljava/lang/Thread;->start()V
    :cond_no_reward
    return-void
.end method

# Runnable.run: sleep ~30s then push onRewardArrived + onAdClose to Pangle channel.
.method public run()V
    .locals 5
    :try_start_0
    const-wide/32 v0, 0x7530          # 30000 ms = 30s (simulate reward ad watch)
    invoke-static {v0, v1}, Ljava/lang/Thread;->sleep(J)V
    :try_end_0
    .catch Ljava/lang/InterruptedException; {:try_start_0 .. :try_end_0} :catch_0
    goto :send
    :catch_0
    # send reward-arrived event (arg = null; Dart side onRewardArrived)
    :send
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV2;->pangleChannel:Lสۥ۠ۦۡ/สۥ۟۟۠;
    if-eqz v2, :done
    const-string v3, "onRewardArrived"
    const/4 v4, 0x0
    invoke-virtual {v2, v3, v4}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้۟۟ۡ(Ljava/lang/String;Ljava/lang/Object;)V
    const-wide/16 v0, 0x1f4           # 500 ms
    invoke-static {v0, v1}, Ljava/lang/Thread;->sleep(J)V
    const-string v3, "onAdClose"
    invoke-virtual {v2, v3, v4}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้۟۟ۡ(Ljava/lang/String;Ljava/lang/Object;)V
    :done
    return-void
    .catch Ljava/lang/InterruptedException; {:send .. :done} :catch_1
    :catch_1
    return-void
.end method
