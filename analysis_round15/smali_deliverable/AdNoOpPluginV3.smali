.class public Lcom/gentle/ppcat/AdNoOpPluginV3;
.super Ljava/lang/Object;
.source "AdNoOpPluginV3.java"
.implements Lสۦۣ۟ۡ/สۥ۟۟ۡ;
.implements Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;
.implements Lสۥ۠ۦۡ/สۥ۟۟ۡ$สۥۣ۟۟;
.implements Ljava/lang/Runnable;

# V3: 4 no-op MethodChannels + EventChannel "flutter_pangle_ads_event" reward simulation.
# StreamHandler.onListen stores EventSink; "Reward" method -> Thread sleep 30s ->
# push onRewardArrived/onAdClose maps via EventSink.success (correct EventChannel path).
.field private eventSink:Lสۥ۠ۦۡ/สۥ۟۟ۡ$สۥ۟۟ۤ;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    return-void
.end method

.method public ۥ้้้้้้้้้้้้้้้้้้้้้้۟۟ۡ(Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;)V
    .locals 4
    invoke-virtual {p1}, Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;->ۥ้้้้۟۟ۡ()Lสۥ۠ۦۡ/สۥ۟۠ۢ;
    move-result-object v0
    new-instance v1, Lสۥ۠ۦۡ/สۥ۟۟۠;
    const-string v2, "flutter_pangle_ads"
    invoke-direct {v1, v0, v2}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V
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
    new-instance v1, Lสۥ۠ۦۡ/สۥ۟۟;
    invoke-direct {v1}, Lสۥ۠ۦۡ/สۥ۟۟;-><init>()V
    new-instance v3, Lสۥ۠ۦۡ/สۥ۟۟ۡ;
    const-string v2, "flutter_pangle_ads_event"
    invoke-direct {v3, v0, v2, v1}, Lสۥ۠ۦۡ/สۥ۟۟ۡ;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;Lสۥ۠ۦۡ/สۥ۟۟۟;)V
    invoke-virtual {v3, p0}, Lสۥ۠ۦۡ/สۥ۟۟ۡ;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟ۡ$สۥۣ۟۟;)V
    return-void
.end method

.method public ۥ้้้้้้้้้้้้้้้้۟۟ۡ(Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;)V
    .locals 0
    return-void
.end method

.method public ۥ้้۟۟ۡ(Ljava/lang/Object;Lสۥ۠ۦۡ/สۥ۟۟ۡ$สۥ۟۟ۤ;)V
    .locals 0
    iput-object p2, p0, Lcom/gentle/ppcat/AdNoOpPluginV3;->eventSink:Lสۥ۠ۦۡ/สۥ۟۟ۡ$สۥ۟۟ۤ;
    return-void
.end method

.method public ۥ้้้้้้้้้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۠۠;Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;)V
    .locals 3
    iget-object v0, p1, Lสۥ۠ۦۡ/สۥ۟۠۠;->ۥ้้۟۟ۡ:Ljava/lang/String;
    const/4 v1, 0x0
    invoke-interface {p2, v1}, Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;->ۥ้้้้۟۟ۡ(Ljava/lang/Object;)V
    const-string v2, "Reward"
    invoke-virtual {v0, v2}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z
    move-result v2
    if-eqz v2, :cond_nr
    new-instance v2, Ljava/lang/Thread;
    invoke-direct {v2, p0}, Ljava/lang/Thread;-><init>(Ljava/lang/Runnable;)V
    invoke-virtual {v2}, Ljava/lang/Thread;->start()V
    :cond_nr
    return-void
.end method

.method public run()V
    .locals 5
    :try_start_0
    const-wide/32 v0, 0x7530
    invoke-static {v0, v1}, Ljava/lang/Thread;->sleep(J)V
    :try_end_0
    .catch Ljava/lang/InterruptedException; {:try_start_0 .. :try_end_0} :catch_0
    goto :push0
    :catch_0
    :push0
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV3;->eventSink:Lสۥ۠ۦۡ/สۥ۟۟ۡ$สۥ۟۟ۤ;
    if-eqz v2, :done
    new-instance v3, Ljava/util/HashMap;
    invoke-direct {v3}, Ljava/util/HashMap;-><init>()V
    const-string v4, "action"
    const-string v0, "onRewardArrived"
    invoke-virtual {v3, v4, v0}, Ljava/util/HashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
    invoke-interface {v2, v3}, Lสۥ۠ۦۡ/สۥ۟۟ۡ$สۥ۟۟ۤ;->ۥ้้۟۟ۡ(Ljava/lang/Object;)V
    const-wide/16 v0, 0x1f4
    invoke-static {v0, v1}, Ljava/lang/Thread;->sleep(J)V
    iget-object v2, p0, Lcom/gentle/ppcat/AdNoOpPluginV3;->eventSink:Lสۥ۠ۦۡ/สۥ۟۟ۡ$สۥ۟۟ۤ;
    new-instance v3, Ljava/util/HashMap;
    invoke-direct {v3}, Ljava/util/HashMap;-><init>()V
    const-string v4, "action"
    const-string v0, "onAdClose"
    invoke-virtual {v3, v4, v0}, Ljava/util/HashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;
    invoke-interface {v2, v3}, Lสۥ۠ۦۡ/สۥ۟۟ۡ$สۥ۟۟ۤ;->ۥ้้۟۟ۡ(Ljava/lang/Object;)V
    :done
    return-void
    .catch Ljava/lang/InterruptedException; {:push0 .. :done} :catch_1
    :catch_1
    return-void
.end method
