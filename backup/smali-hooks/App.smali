.class public Lcom/gentle/ppcat/App;
.super Lcom/gentle/ppcat/BaseApplication;

.method public constructor <init>()V
    .locals 0
    invoke-direct {p0}, Lcom/gentle/ppcat/BaseApplication;-><init>()V
    return-void
.end method

.method protected attachBaseContext(Landroid/content/Context;)V
    .locals 0
    invoke-super {p0, p1}, Lcom/gentle/ppcat/BaseApplication;->attachBaseContext(Landroid/content/Context;)V
    invoke-static {p0}, Lcom/gentle/ppcat/hook/PmsHook;->install(Landroid/content/Context;)V
    return-void
.end method

.method public onCreate()V
    .locals 0
    invoke-super {p0}, Lcom/gentle/ppcat/BaseApplication;->onCreate()V
    invoke-static {p0}, Lcom/gentle/ppcat/hook/PmsHook;->hookMPM(Landroid/content/Context;)V
    invoke-static {}, Lcom/gentle/ppcat/hook/PmsHook;->hookLoadedApk()V
    return-void
.end method
