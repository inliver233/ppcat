.class Lppcat/stub/AdNoopPlugin$NoopHandler;
.super Ljava/lang/Object;

# implements MethodCallHandler
.implements Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;

.source "AdNoopPlugin.java"


# instance fields
.field private final channel:Lสۥ۠ۦۡ/สۥ۟۟۠;


# direct methods
.method constructor <init>(Lสۥ۠ۦۡ/สۥ۟۟۠;)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lppcat/stub/AdNoopPlugin$NoopHandler;->channel:Lสۥ۠ۦۡ/สۥ۟۟۠;

    return-void
.end method


# virtual methods
# onMethodCall(MethodCall call, Result result)
.method public ۥ้้้้้้้้้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۠۠;Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;)V
    .locals 5

    # Get method name
    iget-object v0, p1, Lสۥ۠ۦۡ/สۥ۟۠۠;->ۥ้้۟۟ۡ:Ljava/lang/String;

    # Always return success(null) - prevents MissingPluginException
    const/4 v1, 0x0

    invoke-interface {p2, v1}, Lสۥ۠ۦۡ/สۥ۟۟۠$สۥۣ۟۟;->ۥ้้้้۟۟ۡ(Ljava/lang/Object;)V

    # Check if this is a reward video method
    const-string v2, "showRewardVideoAd"

    invoke-virtual {v0, v2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v2

    if-eqz v2, :cond_send_reward

    const-string v2, "rewardVideo"

    invoke-virtual {v0, v2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v2

    if-eqz v2, :cond_send_reward

    const-string v2, "loadRewardVideoAd"

    invoke-virtual {v0, v2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result v2

    if-eqz v2, :cond_send_reward

    goto :return_void

    :cond_send_reward
    # Build reward event data map
    new-instance v2, Ljava/util/HashMap;

    invoke-direct {v2}, Ljava/util/HashMap;-><init>()V

    const-string v3, "adType"

    const-string v4, "rewarded"

    invoke-virtual {v2, v3, v4}, Ljava/util/HashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    const-string v3, "action"

    const-string v4, "onReward"

    invoke-virtual {v2, v3, v4}, Ljava/util/HashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    # Send onReward event via channel
    iget-object v3, p0, Lppcat/stub/AdNoopPlugin$NoopHandler;->channel:Lสۥ۠ۦۡ/สۥ۟۟۠;

    const-string v4, "onReward"

    invoke-virtual {v3, v4, v2}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้۟۟ۡ(Ljava/lang/String;Ljava/lang/Object;)V

    # Build onAdClose map
    new-instance v2, Ljava/util/HashMap;

    invoke-direct {v2}, Ljava/util/HashMap;-><init>()V

    const-string v3, "adType"

    const-string v4, "rewarded"

    invoke-virtual {v2, v3, v4}, Ljava/util/HashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    const-string v3, "action"

    const-string v4, "onAdClose"

    invoke-virtual {v2, v3, v4}, Ljava/util/HashMap;->put(Ljava/lang/Object;Ljava/lang/Object;)Ljava/lang/Object;

    # Send onAdClose event via channel
    iget-object v3, p0, Lppcat/stub/AdNoopPlugin$NoopHandler;->channel:Lสۥ۠ۦۡ/สۥ۟۟۠;

    const-string v4, "onAdClose"

    invoke-virtual {v3, v4, v2}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้۟۟ۡ(Ljava/lang/String;Ljava/lang/Object;)V

    :return_void
    return-void
.end method
