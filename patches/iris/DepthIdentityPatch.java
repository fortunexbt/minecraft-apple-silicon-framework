// Original patch recipe, licensed under the repository's top-level MIT license.
// Applies only to the campaign's exact Iris 1.11.6+26.3-fabric artifact.
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.jar.JarEntry;
import java.util.jar.JarFile;
import java.util.jar.JarOutputStream;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.tree.AbstractInsnNode;
import org.objectweb.asm.tree.ClassNode;
import org.objectweb.asm.tree.FieldInsnNode;
import org.objectweb.asm.tree.FrameNode;
import org.objectweb.asm.tree.InsnList;
import org.objectweb.asm.tree.JumpInsnNode;
import org.objectweb.asm.tree.LabelNode;
import org.objectweb.asm.tree.MethodNode;
import org.objectweb.asm.tree.VarInsnNode;

public final class DepthIdentityPatch {
    private static final String INPUT_SHA256 = "0fcd6f8858db94ed1f28210005fcff9b9364beaa6eb2a8eccf9449a6f709f14d";
    private static final String REFERENCE_OUTPUT_SHA256 = "141d40c59c116893dfb9f88fb40c853368cfe8a1e965e7eb17161682489ca9be";
    private static final String PATCHED_CLASS_SHA256 = "39514240c3eb5467c5a56ac5247662efd16e58bd373abe563d53d628b8b66658";
    private static final String OWNER = "net/irisshaders/iris/targets/RenderTargets";
    private static final String GPU = "com/mojang/renderpearl/api/textures/GpuTexture";
    private static final String FORMAT = "net/irisshaders/iris/gl/texture/DepthBufferFormat";
    private static final String DIRECTIVES = "net/irisshaders/iris/shaderpack/properties/PackDirectives";
    private static final String CLASS_ENTRY = OWNER + ".class";
    private static final String METHOD_DESC = "(IL" + GPU + ";IIL" + FORMAT + ";L" + DIRECTIVES + ";)Z";

    private static String sha256(Path path) throws Exception {
        MessageDigest digest = MessageDigest.getInstance("SHA-256");
        try (InputStream input = Files.newInputStream(path)) {
            byte[] buffer = new byte[64 * 1024];
            int count;
            while ((count = input.read(buffer)) != -1) digest.update(buffer, 0, count);
        }
        return HexFormat.of().formatHex(digest.digest());
    }

    private static String sha256(byte[] bytes) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes));
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) throw new IllegalArgumentException("usage: DepthIdentityPatch <original-iris.jar> <new-patched-iris.jar>");
        Path inputPath = Path.of(args[0]).toAbsolutePath();
        Path outputPath = Path.of(args[1]).toAbsolutePath();
        if (inputPath.equals(outputPath)) throw new IllegalArgumentException("output must be a new file; keep the original JAR");
        if (!sha256(inputPath).equals(INPUT_SHA256)) throw new IllegalArgumentException("input SHA-256 does not match tested Iris 1.11.6+26.3-fabric; refusing to patch");
        if (Files.exists(outputPath, LinkOption.NOFOLLOW_LINKS)) throw new IllegalArgumentException("output already exists; choose a new filename");

        Path temporary = Files.createTempFile(outputPath.getParent(), "." + outputPath.getFileName() + ".", ".tmp");
        int changed = 0;
        try (JarFile input = new JarFile(inputPath.toFile());
             JarOutputStream output = new JarOutputStream(Files.newOutputStream(temporary))) {
            var entries = input.entries();
            while (entries.hasMoreElements()) {
                JarEntry sourceEntry = entries.nextElement();
                byte[] bytes;
                try (InputStream stream = input.getInputStream(sourceEntry)) { bytes = stream.readAllBytes(); }
                if (sourceEntry.getName().equals(CLASS_ENTRY)) {
                    ClassNode node = new ClassNode();
                    new ClassReader(bytes).accept(node, ClassReader.EXPAND_FRAMES);
                    int methodChanges = 0;
                    for (MethodNode method : node.methods) {
                        if (!method.name.equals("resizeIfNeeded") || !method.desc.equals(METHOD_DESC)) continue;
                        JumpInsnNode versionGuard = null;
                        for (AbstractInsnNode instruction : method.instructions) {
                            if (instruction instanceof JumpInsnNode jump && jump.getOpcode() == Opcodes.IF_ICMPEQ) {
                                versionGuard = jump;
                                break;
                            }
                        }
                        if (versionGuard == null) throw new IllegalStateException("expected original depth-version guard was not found");
                        LabelNode originalSkip = versionGuard.label;
                        LabelNode update = new LabelNode();
                        InsnList identityCheck = new InsnList();
                        identityCheck.add(new VarInsnNode(Opcodes.ALOAD, 0));
                        identityCheck.add(new FieldInsnNode(Opcodes.GETFIELD, OWNER, "currentDepthTexture", "L" + GPU + ";"));
                        identityCheck.add(new VarInsnNode(Opcodes.ALOAD, 2));
                        identityCheck.add(new JumpInsnNode(Opcodes.IF_ACMPEQ, originalSkip));
                        identityCheck.add(update);
                        identityCheck.add(new FrameNode(Opcodes.F_NEW, 8,
                            new Object[]{OWNER, Opcodes.INTEGER, GPU, Opcodes.INTEGER, Opcodes.INTEGER, FORMAT, DIRECTIVES, Opcodes.INTEGER},
                            0, new Object[]{}));
                        versionGuard.setOpcode(Opcodes.IF_ICMPNE);
                        versionGuard.label = update;
                        method.instructions.insert(versionGuard, identityCheck);
                        methodChanges++;
                    }
                    if (methodChanges != 1) throw new IllegalStateException("expected exactly one resizeIfNeeded method patch; found " + methodChanges);
                    ClassWriter writer = new ClassWriter(ClassWriter.COMPUTE_MAXS);
                    node.accept(writer);
                    bytes = writer.toByteArray();
                    String patchedClassHash = sha256(bytes);
                    if (!patchedClassHash.equals(PATCHED_CLASS_SHA256)) throw new IllegalStateException("patched class SHA-256 mismatch: " + patchedClassHash);
                    changed++;
                }
                JarEntry destinationEntry = new JarEntry(sourceEntry.getName());
                destinationEntry.setTime(sourceEntry.getTime());
                output.putNextEntry(destinationEntry);
                output.write(bytes);
                output.closeEntry();
            }
        } catch (Exception error) {
            Files.deleteIfExists(temporary);
            throw error;
        }
        if (changed != 1) {
            Files.deleteIfExists(temporary);
            throw new IllegalStateException("expected one RenderTargets.class change; found " + changed);
        }
        try {
            // A hard link publishes the completed file atomically and fails if
            // another process created the destination after our initial check.
            Files.createLink(outputPath, temporary);
            Files.delete(temporary);
        } catch (Exception error) {
            Files.deleteIfExists(temporary);
            throw error;
        }
        String outputHash = sha256(outputPath);
        System.out.println("Patched class hash verified: " + PATCHED_CLASS_SHA256);
        System.out.println("Output JAR SHA-256: " + outputHash);
        System.out.println("Campaign reference JAR SHA-256: " + REFERENCE_OUTPUT_SHA256);
        System.out.println("Reference archive match: " + outputHash.equals(REFERENCE_OUTPUT_SHA256));
    }
}
