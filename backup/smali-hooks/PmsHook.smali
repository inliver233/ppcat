.class public Lcom/gentle/ppcat/hook/PmsHook;
.super Ljava/lang/Object;
.implements Ljava/lang/reflect/InvocationHandler;

.field private realPms:Ljava/lang/Object;
.field private origSig:Landroid/content/pm/Signature;
.field public static proxyPm:Ljava/lang/Object;
.field public static origSigHolder:Landroid/content/pm/Signature;

.method public constructor <init>(Ljava/lang/Object;Landroid/content/pm/Signature;)V
    .locals 0
    invoke-direct {p0}, Ljava/lang/Object;-><init>()V
    iput-object p1, p0, Lcom/gentle/ppcat/hook/PmsHook;->realPms:Ljava/lang/Object;
    iput-object p2, p0, Lcom/gentle/ppcat/hook/PmsHook;->origSig:Landroid/content/pm/Signature;
    return-void
.end method

.method public invoke(Ljava/lang/Object;Ljava/lang/reflect/Method;[Ljava/lang/Object;)Ljava/lang/Object;
    .locals 4
    iget-object v0, p0, Lcom/gentle/ppcat/hook/PmsHook;->realPms:Ljava/lang/Object;
    invoke-virtual {p2, v0, p3}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v0
    invoke-virtual {p2}, Ljava/lang/reflect/Method;->getName()Ljava/lang/String;
    move-result-object v1
    # Match ALL signature-reading PM methods (getPackageInfo, getPackageInfoAsUser, ...),
    # not just getPackageInfo — the GDT SDK & anti-tamper may use the AsUser variant which
    # bypassed the previous exact-match hook and leaked the real debug certificate.
    const-string v2, "getPackageInfo"
    invoke-virtual {v1, v2}, Ljava/lang/String;->startsWith(Ljava/lang/String;)Z
    move-result v1
    if-eqz v1, :done
    if-nez v0, :do_chkpkg
    :done
    return-object v0
    :do_chkpkg
    # Only spoof OUR package. Leave WebView/Chrome/GMS at their real signature
    # so WebViewFactory.verifyPackageInfo, GMS, AdMob all work normally.
    const/4 v1, 0x0
    aget-object v1, p3, v1
    instance-of v2, v1, Ljava/lang/String;
    if-eqz v2, :done
    const-string v2, "com.gentle.ppcat"
    invoke-virtual {v1, v2}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z
    move-result v1
    if-eqz v1, :done
    :do_modify
    check-cast v0, Landroid/content/pm/PackageInfo;
    const/4 v1, 0x1
    new-array v1, v1, [Landroid/content/pm/Signature;
    iget-object v2, p0, Lcom/gentle/ppcat/hook/PmsHook;->origSig:Landroid/content/pm/Signature;
    const/4 v3, 0x0
    aput-object v2, v1, v3
    iput-object v1, v0, Landroid/content/pm/PackageInfo;->signatures:[Landroid/content/pm/Signature;
    # signingInfo must hold the ORIGINAL cert (not null): the anti-tamper reads
    # signingInfo.getApkContentsSigners() reflectively; null -> NPE -> "tampered".
    iget-object v1, p0, Lcom/gentle/ppcat/hook/PmsHook;->origSig:Landroid/content/pm/Signature;
    invoke-static {v1}, Lcom/gentle/ppcat/hook/PmsHook;->makeSigningInfo(Landroid/content/pm/Signature;)Landroid/content/pm/SigningInfo;
    move-result-object v1
    iput-object v1, v0, Landroid/content/pm/PackageInfo;->signingInfo:Landroid/content/pm/SigningInfo;
    goto :done
.end method

# Build a real android.content.pm.SigningInfo whose getApkContentsSigners()
# returns [origSig]. Done reflectively via PackageParser.SigningDetails (Android 9).
.method public static makeSigningInfo(Landroid/content/pm/Signature;)Landroid/content/pm/SigningInfo;
    .locals 8
    :try_start_0
    # v0 = new Signature[]{ origSig }
    const/4 v0, 0x1
    new-array v0, v0, [Landroid/content/pm/Signature;
    const/4 v1, 0x0
    aput-object p0, v0, v1

    # v1 = Class.forName("android.content.pm.PackageParser$SigningDetails")
    const-string v2, "android.content.pm.PackageParser$SigningDetails"
    invoke-static {v2}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;
    move-result-object v1

    # v2 = new Class[]{ Signature[].class, int.class }
    const/4 v2, 0x2
    new-array v2, v2, [Ljava/lang/Class;
    const/4 v3, 0x0
    const-class v4, [Landroid/content/pm/Signature;
    aput-object v4, v2, v3
    const/4 v3, 0x1
    sget-object v4, Ljava/lang/Integer;->TYPE:Ljava/lang/Class;
    aput-object v4, v2, v3

    # v3 = sdClass.getDeclaredConstructor(v2); setAccessible(true)
    invoke-virtual {v1, v2}, Ljava/lang/Class;->getDeclaredConstructor([Ljava/lang/Class;)Ljava/lang/reflect/Constructor;
    move-result-object v3
    const/4 v4, 0x1
    invoke-virtual {v3, v4}, Ljava/lang/reflect/Constructor;->setAccessible(Z)V

    # v4 = new Object[]{ v0, Integer.valueOf(2) }
    const/4 v4, 0x2
    new-array v4, v4, [Ljava/lang/Object;
    const/4 v5, 0x0
    aput-object v0, v4, v5
    const/4 v5, 0x1
    const/4 v6, 0x2
    invoke-static {v6}, Ljava/lang/Integer;->valueOf(I)Ljava/lang/Integer;
    move-result-object v6
    aput-object v6, v4, v5

    # v2 = sdCtor.newInstance(v4)  -> SigningDetails
    invoke-virtual {v3, v4}, Ljava/lang/reflect/Constructor;->newInstance([Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v2

    # v3 = Class.forName("android.content.pm.SigningInfo")
    const-string v4, "android.content.pm.SigningInfo"
    invoke-static {v4}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;
    move-result-object v3

    # siCtor = siClass.getDeclaredConstructor(SigningDetails.class)
    const/4 v5, 0x1
    new-array v5, v5, [Ljava/lang/Class;
    const/4 v6, 0x0
    aput-object v1, v5, v6
    invoke-virtual {v3, v5}, Ljava/lang/Class;->getDeclaredConstructor([Ljava/lang/Class;)Ljava/lang/reflect/Constructor;
    move-result-object v4
    const/4 v5, 0x1
    invoke-virtual {v4, v5}, Ljava/lang/reflect/Constructor;->setAccessible(Z)V

    # v4 = siCtor.newInstance(new Object[]{ v2 })
    const/4 v6, 0x1
    new-array v6, v6, [Ljava/lang/Object;
    const/4 v7, 0x0
    aput-object v2, v6, v7
    invoke-virtual {v4, v6}, Ljava/lang/reflect/Constructor;->newInstance([Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v4
    check-cast v4, Landroid/content/pm/SigningInfo;
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0
    return-object v4

    :catch_0
    move-exception v0
    const-string v1, "PmsHook"
    new-instance v2, Ljava/lang/StringBuilder;
    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V
    const-string v3, "makeSigningInfo FAILED: "
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/Throwable;->getMessage()Ljava/lang/String;
    move-result-object v3
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v2
    invoke-static {v1, v2}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I
    const/4 v0, 0x0
    return-object v0
.end method

.method public static install(Landroid/content/Context;)V
    .locals 8
    const-string v0, "MIIDhzCCAm+gAwIBAgIEOgyCdDANBgkqhkiG9w0BAQsFADB0MQ4wDAYDVQQGEwVaSC1DTjESMBAGA1UECBMJR3VhbmdEb25nMRIwEAYDVQQHEwlHdWFuZ1pob3UxETAPBgNVBAoTCFBlcnNvbmFsMREwDwYDVQQLEwhQZXJzb25hbDEUMBIGA1UEAxMLR2VudGxlIEt3YW4wHhcNMTkwNjA1MDY0NTI4WhcNNDYxMDIxMDY0NTI4WjB0MQ4wDAYDVQQGEwVaSC1DTjESMBAGA1UECBMJR3VhbmdEb25nMRIwEAYDVQQHEwlHdWFuZ1pob3UxETAPBgNVBAoTCFBlcnNvbmFsMREwDwYDVQQLEwhQZXJzb25hbDEUMBIGA1UEAxMLR2VudGxlIEt3YW4wggEiMA0GCSqGSIb3DQEBAQUAA4IBDwAwggEKAoIBAQDMRAlmKrETqueBlOwqpwt1cKCjfgDCe1/zwqTjVf/QE3OmW4D2Pvij5jbWx3jES/pvMhhfDsX+rZITAqEbvX5olyCfuB0tI3za5fXcIeiB05ZpnKP0s1TF3kQI9j08JaUIHqKtomQytSvzdV3h1f4mlCPblSgQod7oF7IzMbAXbklfrb925T8GC5hz/wWzHSNLVEblBAyPspolXQxElcLBBKh5+kLJUJ5k40ut7DbO6jdk4Mn6sbar4VSDXQVBGQlYGcqGJNK0rEiOTVKvhJEsBXBLWEnQzcUKlAs3IcWTkOuYjZT3A9j7gjSbotx2/16H69ADP9GpeYBcMsUcZj4dAgMBAAGjITAfMB0GA1UdDgQWBBQRNtYVOJXsxV3IxuqFqH5iXHGoFDANBgkqhkiG9w0BAQsFAAOCAQEAJPSAmI7qrW/aDLFMRJtRjcmfXJqEFQ3JON+VX3UvKS/cO4AgAI+AkdFfXV14nGGv1MHb0XYPXqgr0gsQRgOLo4pNp28CwwAgnvuPZFAkFHojleNxoFlKG2XyCWP7Iy1EWi4KrUxs6nx3eSOjeEo574r3kW/R/U3BOn5WCGE3iAOO2XzPIDXtXrkWNOKHBAY3RhYirXDtuvSLUpVuJ0B5g+/nhpTeTloxNWE1qPhsIKKNLflTWILe1tOCCkKXfCNtYO0sgqsS+x2Au8AARrj7cBKu45XifsHRkedfrycylmlGvu31YbbUa5rp7JsY1CVUrOGYtZCNsOuj71bhRkLYyg=="
    const/4 v1, 0x0
    invoke-static {v0, v1}, Landroid/util/Base64;->decode(Ljava/lang/String;I)[B
    move-result-object v1
    new-instance v2, Landroid/content/pm/Signature;
    invoke-direct {v2, v1}, Landroid/content/pm/Signature;-><init>([B)V
    const-string v3, "android.app.ActivityThread"
    invoke-static {v3}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;
    move-result-object v3
    const-string v4, "sPackageManager"
    invoke-virtual {v3, v4}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;
    move-result-object v4
    const/4 v5, 0x1
    invoke-virtual {v4, v5}, Ljava/lang/reflect/Field;->setAccessible(Z)V
    const/4 v5, 0x0
    invoke-virtual {v4, v5}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v5
    const-string v6, "android.content.pm.IPackageManager"
    invoke-static {v6}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;
    move-result-object v6
    new-instance v7, Lcom/gentle/ppcat/hook/PmsHook;
    invoke-direct {v7, v5, v2}, Lcom/gentle/ppcat/hook/PmsHook;-><init>(Ljava/lang/Object;Landroid/content/pm/Signature;)V
    const/4 v0, 0x1
    new-array v0, v0, [Ljava/lang/Class;
    const/4 v1, 0x0
    aput-object v6, v0, v1
    invoke-virtual {p0}, Landroid/content/Context;->getClassLoader()Ljava/lang/ClassLoader;
    move-result-object v1
    invoke-static {v1, v0, v7}, Ljava/lang/reflect/Proxy;->newProxyInstance(Ljava/lang/ClassLoader;[Ljava/lang/Class;Ljava/lang/reflect/InvocationHandler;)Ljava/lang/Object;
    move-result-object v0
    sput-object v0, Lcom/gentle/ppcat/hook/PmsHook;->proxyPm:Ljava/lang/Object;
    sput-object v2, Lcom/gentle/ppcat/hook/PmsHook;->origSigHolder:Landroid/content/pm/Signature;
    invoke-virtual {v4, v5, v0}, Ljava/lang/reflect/Field;->set(Ljava/lang/Object;Ljava/lang/Object;)V
    const-string v1, "PmsHook"
    const-string v2, "signature spoof installed"
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    return-void
.end method

.method public static hookMPM(Landroid/content/Context;)V
    .locals 5
    :try_start_0
    sget-object v4, Lcom/gentle/ppcat/hook/PmsHook;->proxyPm:Ljava/lang/Object;
    invoke-virtual {p0}, Landroid/content/Context;->getPackageManager()Landroid/content/pm/PackageManager;
    move-result-object v0
    invoke-virtual {p0}, Landroid/content/Context;->getApplicationContext()Landroid/content/Context;
    move-result-object v1
    invoke-virtual {v1}, Landroid/content/Context;->getPackageManager()Landroid/content/pm/PackageManager;
    move-result-object v1
    const-string v2, "android.app.ApplicationPackageManager"
    invoke-static {v2}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;
    move-result-object v2
    const-string v3, "mPM"
    invoke-virtual {v2, v3}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;
    move-result-object v2
    const/4 v3, 0x1
    invoke-virtual {v2, v3}, Ljava/lang/reflect/Field;->setAccessible(Z)V
    invoke-virtual {v2, v0, v4}, Ljava/lang/reflect/Field;->set(Ljava/lang/Object;Ljava/lang/Object;)V
    invoke-virtual {v2, v1, v4}, Ljava/lang/reflect/Field;->set(Ljava/lang/Object;Ljava/lang/Object;)V
    const-string v3, "PmsHook"
    const-string v4, "mPM hooked"
    invoke-static {v3, v4}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0
    return-void
    :catch_0
    move-exception v0
    const-string v1, "PmsHook"
    new-instance v2, Ljava/lang/StringBuilder;
    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V
    const-string v3, "mPM hook failed: "
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/Throwable;->getMessage()Ljava/lang/String;
    move-result-object v0
    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v1, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    return-void
.end method

# Patch the app's cached PackageInfo (LoadedApk.mPackageInfo) so signature reads that
# bypass the IPackageManager proxy (e.g. via LoadedApk / some SDKs) also see the original cert.
.method public static hookLoadedApk()V
    .locals 8
    :try_start_0
    # app = ActivityThread.currentApplication()
    const-string v0, "android.app.ActivityThread"
    invoke-static {v0}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;
    move-result-object v0
    const/4 v1, 0x0
    new-array v2, v1, [Ljava/lang/Class;
    const-string v3, "currentApplication"
    invoke-virtual {v0, v3, v2}, Ljava/lang/Class;->getDeclaredMethod(Ljava/lang/String;[Ljava/lang/Class;)Ljava/lang/reflect/Method;
    move-result-object v3
    new-array v4, v1, [Ljava/lang/Object;
    invoke-virtual {v3, v0, v4}, Ljava/lang/reflect/Method;->invoke(Ljava/lang/Object;[Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v0
    check-cast v0, Landroid/app/Application;

    # loadedApk = Application.class.getDeclaredField("mLoadedApk").get(app)
    const-string v1, "android.app.Application"
    invoke-static {v1}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;
    move-result-object v1
    const-string v2, "mLoadedApk"
    invoke-virtual {v1, v2}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;
    move-result-object v1
    const/4 v2, 0x1
    invoke-virtual {v1, v2}, Ljava/lang/reflect/Field;->setAccessible(Z)V
    invoke-virtual {v1, v0}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v0

    # pi = LoadedApk.class.getDeclaredField("mPackageInfo").get(loadedApk)
    const-string v1, "android.app.LoadedApk"
    invoke-static {v1}, Ljava/lang/Class;->forName(Ljava/lang/String;)Ljava/lang/Class;
    move-result-object v1
    const-string v2, "mPackageInfo"
    invoke-virtual {v1, v2}, Ljava/lang/Class;->getDeclaredField(Ljava/lang/String;)Ljava/lang/reflect/Field;
    move-result-object v1
    const/4 v2, 0x1
    invoke-virtual {v1, v2}, Ljava/lang/reflect/Field;->setAccessible(Z)V
    invoke-virtual {v1, v0}, Ljava/lang/reflect/Field;->get(Ljava/lang/Object;)Ljava/lang/Object;
    move-result-object v0
    check-cast v0, Landroid/content/pm/PackageInfo;

    # pi.signatures = [origSig]
    sget-object v5, Lcom/gentle/ppcat/hook/PmsHook;->origSigHolder:Landroid/content/pm/Signature;
    const/4 v6, 0x1
    new-array v6, v6, [Landroid/content/pm/Signature;
    const/4 v7, 0x0
    aput-object v5, v6, v7
    iput-object v6, v0, Landroid/content/pm/PackageInfo;->signatures:[Landroid/content/pm/Signature;
    # pi.signingInfo = makeSigningInfo(origSig)
    invoke-static {v5}, Lcom/gentle/ppcat/hook/PmsHook;->makeSigningInfo(Landroid/content/pm/Signature;)Landroid/content/pm/SigningInfo;
    move-result-object v5
    iput-object v5, v0, Landroid/content/pm/PackageInfo;->signingInfo:Landroid/content/pm/SigningInfo;
    const-string v1, "PmsHook"
    const-string v2, "LoadedApk.mPackageInfo patched"
    invoke-static {v1, v2}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0
    return-void
    :catch_0
    move-exception v0
    const-string v1, "PmsHook"
    new-instance v2, Ljava/lang/StringBuilder;
    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V
    const-string v3, "hookLoadedApk failed: "
    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v0}, Ljava/lang/Throwable;->getMessage()Ljava/lang/String;
    move-result-object v0
    invoke-virtual {v2, v0}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v0
    invoke-static {v1, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I
    return-void
.end method
