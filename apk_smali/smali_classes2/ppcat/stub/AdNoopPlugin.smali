.class public Lppcat/stub/AdNoopPlugin;
.super Ljava/lang/Object;

# implements FlutterPlugin
.implements Lสۦۣ۟ۡ/สۥ۟۟ۡ;

.source "AdNoopPlugin.java"

# annotations
.annotation system Ldalvik/annotation/MemberClasses;
    value = {
        Lppcat/stub/AdNoopPlugin$NoopHandler;
    }
.end annotation


# instance fields
.field private channels:Ljava/util/ArrayList;
    .annotation system Ldalvik/annotation/Signature;
        value = {
            "Ljava/util/ArrayList<",
            "Lio/flutter/embedding/engine/สۥ۟۟ۢ$สۥ۟۟ۡ;",
            ">;"
        }
    .end annotation
.end field


# direct methods
.method public constructor <init>()V
    .locals 1

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    new-instance v0, Ljava/util/ArrayList;

    invoke-direct {v0}, Ljava/util/ArrayList;-><init>()V

    iput-object v0, p0, Lppcat/stub/AdNoopPlugin;->channels:Ljava/util/ArrayList;

    return-void
.end method


# virtual methods
# onAttachedToEngine(FlutterPluginBinding binding)
.method public ۥ้้้้้้้้้้้้้้้้้้้้้้۟۟ۡ(Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;)V
    .locals 3

    # binding = p1
    # Get binary messenger: binding.getBinaryMessenger()
    invoke-virtual {p1}, Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;->ۥ้้้้۟۟ۡ()Lสۥ۠ۦۡ/สۥ۟۠ۢ;

    move-result-object v0
    # v0 = BinaryMessenger

    # --- Channel 1: flutter_pangle_ads ---
    const-string v1, "flutter_pangle_ads"

    new-instance v2, Lสۥ۠ۦۡ/สۥ۟۟۠;

    invoke-direct {v2, v0, v1}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V

    new-instance v3, Lppcat/stub/AdNoopPlugin$NoopHandler;

    invoke-direct {v3, v2}, Lppcat/stub/AdNoopPlugin$NoopHandler;-><init>(Lสۥ۠ۦۡ/สۥ۟۟۠;)V

    invoke-virtual {v2, v3}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V

    iget-object v3, p0, Lppcat/stub/AdNoopPlugin;->channels:Ljava/util/ArrayList;

    invoke-virtual {v3, v2}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    # --- Channel 2: flutter_pangle_ads_event ---
    const-string v1, "flutter_pangle_ads_event"

    new-instance v2, Lสۥ۠ۦۡ/สۥ۟۟۠;

    invoke-direct {v2, v0, v1}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V

    new-instance v3, Lppcat/stub/AdNoopPlugin$NoopHandler;

    invoke-direct {v3, v2}, Lppcat/stub/AdNoopPlugin$NoopHandler;-><init>(Lสۥ۠ۦۡ/สۥ۟۟۠;)V

    invoke-virtual {v2, v3}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V

    iget-object v3, p0, Lppcat/stub/AdNoopPlugin;->channels:Ljava/util/ArrayList;

    invoke-virtual {v3, v2}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    # --- Channel 3: plugins.hetian.me/gdt_plugins ---
    const-string v1, "plugins.hetian.me/gdt_plugins"

    new-instance v2, Lสۥ۠ۦۡ/สۥ۟۟۠;

    invoke-direct {v2, v0, v1}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V

    new-instance v3, Lppcat/stub/AdNoopPlugin$NoopHandler;

    invoke-direct {v3, v2}, Lppcat/stub/AdNoopPlugin$NoopHandler;-><init>(Lสۥ۠ۦۡ/สۥ۟۟۠;)V

    invoke-virtual {v2, v3}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V

    iget-object v3, p0, Lppcat/stub/AdNoopPlugin;->channels:Ljava/util/ArrayList;

    invoke-virtual {v3, v2}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    # --- Channel 4: ksad ---
    const-string v1, "ksad"

    new-instance v2, Lสۥ۠ۦۡ/สۥ۟۟۠;

    invoke-direct {v2, v0, v1}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V

    new-instance v3, Lppcat/stub/AdNoopPlugin$NoopHandler;

    invoke-direct {v3, v2}, Lppcat/stub/AdNoopPlugin$NoopHandler;-><init>(Lสۥ۠ۦۡ/สۥ۟۟۠;)V

    invoke-virtual {v2, v3}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V

    iget-object v3, p0, Lppcat/stub/AdNoopPlugin;->channels:Ljava/util/ArrayList;

    invoke-virtual {v3, v2}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    # --- Channel 5: plugins.flutter.io/google_mobile_ads ---
    const-string v1, "plugins.flutter.io/google_mobile_ads"

    new-instance v2, Lสۥ۠ۦۡ/สۥ۟۟۠;

    invoke-direct {v2, v0, v1}, Lสۥ۠ۦۡ/สۥ۟۟۠;-><init>(Lสۥ۠ۦۡ/สۥ۟۠ۢ;Ljava/lang/String;)V

    new-instance v3, Lppcat/stub/AdNoopPlugin$NoopHandler;

    invoke-direct {v3, v2}, Lppcat/stub/AdNoopPlugin$NoopHandler;-><init>(Lสۥ۠ۦۡ/สۥ۟۟۠;)V

    invoke-virtual {v2, v3}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V

    iget-object v3, p0, Lppcat/stub/AdNoopPlugin;->channels:Ljava/util/ArrayList;

    invoke-virtual {v3, v2}, Ljava/util/ArrayList;->add(Ljava/lang/Object;)Z

    return-void
.end method

# onDetachedFromEngine(FlutterPluginBinding binding)
.method public ۥ้้้้้้้้้้้้้้้้۟۟ۡ(Lสۦۣ۟ۡ/สۥ۟۟ۡ$สۥ۟۠ۢ;)V
    .locals 2

    iget-object v0, p0, Lppcat/stub/AdNoopPlugin;->channels:Ljava/util/ArrayList;

    invoke-virtual {v0}, Ljava/util/ArrayList;->iterator()Ljava/util/Iterator;

    move-result-object v0

    :goto_0
    invoke-interface {v0}, Ljava/util/Iterator;->hasNext()Z

    move-result v1

    if-eqz v1, :cond_0

    invoke-interface {v0}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v1

    check-cast v1, Lสۥ۠ۦۡ/สۥ۟۟۠;

    const/4 v2, 0x0

    invoke-virtual {v1, v2}, Lสۥ۠ۦۡ/สۥ۟۟۠;->ۥ้้้้้้้้้้۟۟ۡ(Lสۥ۠ۦۡ/สۥ۟۟۠$สۥ۟۟ۢ;)V

    goto :goto_0

    :cond_0
    iget-object v0, p0, Lppcat/stub/AdNoopPlugin;->channels:Ljava/util/ArrayList;

    invoke-virtual {v0}, Ljava/util/ArrayList;->clear()V

    return-void
.end method
