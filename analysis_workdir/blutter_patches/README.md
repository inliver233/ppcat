# blutter / Dart SDK patches attempted

These patches were applied to `blutter/dartsdk/v2.19.0/runtime/vm/` to work around
the custom-engine incompatibilities. They got blutter further but ultimately failed
at `cid 84 not in class table` (cluster format mismatch).

## Patches

1. **app_snapshot.cc - VerifyFeatures**: skip the feature-string comparison
   (custom engine has `arm64-sysv` instead of standard `arm64 android`).
   Still calls ReadFeatures to advance the stream position.

2. **image_snapshot.cc - VerifyAlignment**: skip the 64-byte alignment check
   (snapshot data at vaddr 0x3330 has only 16-byte alignment).

3. **app_snapshot.cc - Deserialize base object count check**: convert FATAL
   to warning (snapshot's base object count is off-by-one vs Dart 2.19.x:
   expects 93, provided 94).

## Even with all 3 patches, blutter fails at:
`No cluster defined for cid 84` — the custom Dart VM has a class table that
differs structurally from any official Dart 2.19.x release.
