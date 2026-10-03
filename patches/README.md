# Reproducible correctness patches

These recipes operate on copies of official upstream artifacts that the user has obtained from the linked project pages. They never replace the downloaded original and never ship an Iris JAR or shader ZIP. The Iris class transformer is original code under the repository's top-level MIT license. The MakeUp shader patch and its application script carry LGPL-3.0-only attribution; copies of the LGPL and incorporated GPL texts are in [`makeup/`](makeup/). See [`THIRD_PARTY.md`](../THIRD_PARTY.md).

## Iris depth identity v3

The campaign patched Iris 1.11.6+26.3-fabric only. The Java recipe fails closed unless the input JAR SHA-256 is `0fcd6f8858db94ed1f28210005fcff9b9364beaa6eb2a8eccf9449a6f709f14d`. It changes one guard in `RenderTargets.resizeIfNeeded`: a cached depth-buffer version is treated as unchanged only if the incoming `GpuTexture` is also the same object. It then checks the patched class SHA-256 (`39514240c3eb5467c5a56ac5247662efd16e58bd373abe563d53d628b8b66658`) and reports the output JAR hash. The campaign reference output JAR SHA-256 is `141d40c59c116893dfb9f88fb40c853368cfe8a1e965e7eb17161682489ca9be`.

Build with JDK 17 or newer and ASM 9.9.1 core and tree modules from Maven Central:

```sh
javac -cp asm-9.9.1.jar:asm-tree-9.9.1.jar patches/iris/DepthIdentityPatch.java
java -cp patches/iris:asm-9.9.1.jar:asm-tree-9.9.1.jar DepthIdentityPatch iris-1.11.6+mc26.3.jar iris-1.11.6-depth-identity-v3.jar
```

Keep the original JAR and install the output under a distinct filename. An input hash mismatch means the recipe does not match that Iris build; stop and requalify instead of forcing it.

## MakeUp exposure-history initialization

[`makeup-exposure-init.patch`](makeup-exposure-init.patch) and [`apply-makeup-exposure-init.py`](apply-makeup-exposure-init.py) target the exact MakeUp Ultra Fast 9.5f archive used by the campaign. The script requires the original archive SHA-256 `afbf622b983d29ffa5fe5f15197f321d3921915bd44584d85f14bc11b5e0e5e8`, changes exactly one line in `shaders/common/composite_vertex.glsl`, writes a separate output ZIP, and validates the ZIP. The change bypasses temporal smoothing only when the previous exposure history value is zero or negative. Positive history keeps the original smoothing formula. The campaign's modified archive SHA-256 was `3ff5d3b3a8b47e4743f3d90e77faf6ca8d89e97f2f5989694f28bc9ad753b922`.

```sh
python3 patches/apply-makeup-exposure-init.py MakeUp-UltraFast-9.5f.zip MakeUp-UltraFast-9.5f-exposure-init.zip
```

The Python recipe uses the standard library and supports Python 3.10 or newer.

The campaign's patched ZIP hash (`3ff5d3b3a8b47e4743f3d90e77faf6ca8d89e97f2f5989694f28bc9ad753b922`) is a historical receipt, not a guaranteed digest for a newly repacked archive. ZIP metadata and compression can change the archive hash while leaving identical members. The script verifies the exact input hash, verifies every untouched member byte-for-byte, checks the patched source member, and prints the new output hash.

This shader patch and patching recipe are under the upstream MakeUp LGPL-3.0-only terms; copies of [LGPL-3.0](makeup/LICENSE-LGPL-3.0.txt) and the referenced [GPL-3.0](makeup/LICENSE-GPL-3.0.txt) are provided. It credits [KDXavier's project](https://modrinth.com/shader/makeup-ultra-fast-shaders). No shader archive or other shader source is distributed here.
