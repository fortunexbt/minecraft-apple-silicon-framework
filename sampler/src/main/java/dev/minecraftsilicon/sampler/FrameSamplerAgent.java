package dev.minecraftsilicon.sampler;

import java.io.BufferedWriter;
import java.io.IOException;
import java.io.OutputStreamWriter;
import java.lang.instrument.ClassFileTransformer;
import java.lang.instrument.Instrumentation;
import java.lang.reflect.Method;
import java.nio.channels.Channels;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.nio.file.AtomicMoveNotSupportedException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.nio.file.StandardOpenOption;
import java.security.ProtectionDomain;
import java.time.Instant;
import java.util.Properties;
import java.util.UUID;
import java.util.jar.JarFile;
import org.objectweb.asm.ClassReader;
import org.objectweb.asm.ClassVisitor;
import org.objectweb.asm.ClassWriter;
import org.objectweb.asm.MethodVisitor;
import org.objectweb.asm.Opcodes;
import org.objectweb.asm.Type;

/**
 * Explicitly mapped Java instrumentation agent for CPU frame-production timing.
 * It never chooses a Minecraft hook by guesswork.
 */
public final class FrameSamplerAgent {
    private static final String METRIC = "cpu_frame_production";
    private static final long HOOK_WAIT_NANOS = 90000000000L;
    private static final String ID_PATTERN = "[A-Za-z0-9_-]{1,100}";
    private static final String SINK_CLASS = "dev.minecraftsilicon.sampler.FrameSink";

    private static volatile Path root;
    private static volatile Hook hook;
    private static volatile String configurationError;
    private static volatile String transformError;
    private static volatile boolean hookInstalled;
    private static volatile String activeId;
    private static volatile int activeSeconds;
    private static volatile long requestNanos;
    private static volatile boolean recordingStatusWritten;
    private static volatile boolean capturePrepared;
    private static volatile boolean statusOwned;
    private static volatile String lastSeenId = "";
    private static volatile boolean sinkAvailable;
    private static volatile Method sinkPrepare;
    private static volatile Method sinkIsFinished;
    private static volatile Method sinkHasStarted;
    private static volatile Method sinkGetCount;
    private static volatile Method sinkGetUnfocusedFrames;
    private static volatile Method sinkIsBufferFull;
    private static volatile Method sinkGetError;
    private static volatile Method sinkGetTimes;
    private static volatile Method sinkStop;
    private static JarFile bootstrapSinkJar;
    private static volatile String lastAgentErrorMessage;
    private static volatile long lastAgentErrorNanos;

    private FrameSamplerAgent() { }

    public static void premain(String argument, Instrumentation instrumentation) throws Exception {
        if (argument == null || argument.trim().isEmpty()) throw new IllegalArgumentException("javaagent argument must be a control directory");
        root = Paths.get(argument).toAbsolutePath().normalize();
        Files.createDirectories(root);
        try {
            hook = Hook.read(root.resolve("hook.properties"));
        } catch (Throwable e) {
            configurationError = message(e);
        }

        Path ownJar = Paths.get(FrameSamplerAgent.class.getProtectionDomain().getCodeSource().getLocation().toURI());
        Path sinkPath = ownJar.resolveSibling("frame-sampler-sink.jar");
        try {
            if (!Files.isRegularFile(sinkPath)) throw new IOException("missing adjacent frame-sampler-sink.jar");
            bootstrapSinkJar = new JarFile(sinkPath.toFile());
            instrumentation.appendToBootstrapClassLoaderSearch(bootstrapSinkJar);
            loadSinkApi();
        } catch (Throwable e) {
            configurationError = "bootstrap frame sink: " + message(e);
        }
        if (hook != null && sinkAvailable && configurationError == null) {
            for (Class<?> loaded : instrumentation.getAllLoadedClasses()) {
                if (loaded.getName().replace('.', '/').equals(hook.targetClass)) {
                    transformError = "configured target class was already loaded before the sampler attached";
                    break;
                }
            }
            instrumentation.addTransformer(new HookTransformer(hook), false);
        }
        Thread control = new Thread(new Runnable() {
            @Override public void run() { controlLoop(); }
        }, "frame-sampler-control");
        control.setDaemon(true);
        control.start();
    }

    private static void loadSinkApi() throws Exception {
        Class<?> sink = Class.forName(SINK_CLASS, true, null);
        sink.getMethod("frame", Object.class);
        sinkPrepare = sink.getMethod("prepare", Integer.TYPE, String.class);
        sinkIsFinished = sink.getMethod("isFinished");
        sinkHasStarted = sink.getMethod("hasStarted");
        sinkGetCount = sink.getMethod("getCount");
        sinkGetUnfocusedFrames = sink.getMethod("getUnfocusedFrames");
        sinkIsBufferFull = sink.getMethod("isBufferFull");
        sinkGetError = sink.getMethod("getError");
        sinkGetTimes = sink.getMethod("getTimes");
        sinkStop = sink.getMethod("stop");
        sinkAvailable = true;
    }

    private static boolean sinkBoolean(Method method) throws Exception {
        return ((Boolean) method.invoke(null)).booleanValue();
    }

    private static SinkSnapshot sinkSnapshot() throws Exception {
        long[] times = (long[]) sinkGetTimes.invoke(null);
        int count = ((Integer) sinkGetCount.invoke(null)).intValue();
        int unfocused = ((Integer) sinkGetUnfocusedFrames.invoke(null)).intValue();
        if (count != times.length) unfocused = -1;
        return new SinkSnapshot(times, times.length, unfocused,
                sinkBoolean(sinkIsBufferFull), (String) sinkGetError.invoke(null));
    }

    private static SinkSnapshot emptySnapshot() {
        return new SinkSnapshot(new long[0], 0, -1, false, null);
    }

    private static final class SinkSnapshot {
        final long[] times;
        final int frames;
        final int unfocusedFrames;
        final boolean bufferFull;
        final String error;

        SinkSnapshot(long[] times, int frames, int unfocusedFrames, boolean bufferFull, String error) {
            this.times = times;
            this.frames = frames;
            this.unfocusedFrames = unfocusedFrames;
            this.bufferFull = bufferFull;
            this.error = error;
        }
    }

    private static void controlLoop() {
        while (true) {
            try {
                pollActiveCapture();
                if (activeId == null) pollRequest();
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            } catch (Throwable e) {
                String id = activeId;
                if (id != null) failActive(message(e), true);
                else writeAgentError(message(e));
            }
            try {
                Thread.sleep(50L);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
                return;
            }
        }
    }

    private static void pollRequest() throws IOException {
        Path request = root.resolve("measure.properties");
        if (!Files.isRegularFile(request)) return;

        Properties p = new Properties();
        try (java.io.Reader reader = Files.newBufferedReader(request, StandardCharsets.UTF_8)) {
            p.load(reader);
        }
        String id = p.getProperty("id", "").trim();
        if (!id.matches(ID_PATTERN) || id.equals(lastSeenId)) return;
        lastSeenId = id;
        int seconds;
        try {
            seconds = Integer.parseInt(p.getProperty("seconds", "20").trim());
        } catch (NumberFormatException e) {
            refuse(id, "seconds must be an integer from 5 through 30");
            return;
        }
        if (seconds < 5 || seconds > 30) {
            refuse(id, "seconds must be from 5 through 30");
            return;
        }

        Path status = statusPath(id);
        Path csv = csvPath(id);
        Path partial = root.resolve(id + "-frames.csv.tmp");
        if (Files.exists(status)) return;
        if (Files.exists(csv) || Files.exists(partial)) {
            refuse(id, "capture ID already has output artifacts; choose a new ID");
            return;
        }
        activeId = id;
        activeSeconds = seconds;
        requestNanos = System.nanoTime();
        recordingStatusWritten = false;
        capturePrepared = false;
        statusOwned = false;
        writeStatus("starting", id, 0, -1, false, null, hookInstalled, hook == null ? null : hook.display(), false);
        statusOwned = true;

        if (configurationError != null) {
            failActive("hook configuration: " + configurationError, false);
            return;
        }
        if (transformError != null) {
            failActive("hook installation: " + transformError, false);
            return;
        }
        if (hook == null) {
            failActive("hook configuration is unavailable", false);
            return;
        }
        if (hookInstalled) beginRecording();
    }

    private static void pollActiveCapture() throws Exception {
        String id = activeId;
        if (id == null) return;

        String mappingError = transformError;
        if (mappingError != null) {
            failActive("hook installation: " + mappingError, false);
            return;
        }

        if (!hookInstalled) {
            if (System.nanoTime() - requestNanos > HOOK_WAIT_NANOS) {
                failActive("configured target class/method was not observed within 90 seconds", false);
            }
            return;
        }

        if (sinkBoolean(sinkIsFinished)) {
            finishActive();
            return;
        }
        if (hookInstalled && !capturePrepared) beginRecording();
        boolean started = sinkBoolean(sinkHasStarted);
        if (started && !recordingStatusWritten) {
            SinkSnapshot snapshot = sinkSnapshot();
            writeStatus("recording", id, snapshot.frames, snapshot.unfocusedFrames, snapshot.bufferFull, snapshot.error, true, hook.display(), true);
            recordingStatusWritten = true;
        }
        if (!started && System.nanoTime() - requestNanos > HOOK_WAIT_NANOS) {
            failActive("configured hook did not produce a frame within 90 seconds", false);
        }
    }

    private static void beginRecording() {
        try {
            sinkPrepare.invoke(null, Integer.valueOf(activeSeconds), hook == null ? null : hook.focusMethod);
            capturePrepared = true;
        } catch (Throwable e) {
            failActive("could not start frame sink: " + message(e), false);
        }
    }

    private static void finishActive() throws Exception {
        String id = activeId;
        if (id == null) return;
        SinkSnapshot snapshot = sinkSnapshot();
        writeCsv(id, snapshot.times);
        String finalState = snapshot.error == null && !snapshot.bufferFull ? "done" : "error";
        writeStatus(finalState, id, snapshot.frames, snapshot.unfocusedFrames, snapshot.bufferFull,
                snapshot.error, true, hook == null ? null : hook.display(), true);
        activeId = null;
        recordingStatusWritten = false;
        capturePrepared = false;
    }

    private static void failActive(String reason, boolean includePartial) {
        String id = activeId;
        if (id == null) return;
        try {
            SinkSnapshot snapshot = emptySnapshot();
            if (sinkAvailable) {
                sinkStop.invoke(null);
                snapshot = sinkSnapshot();
            }
            if (includePartial && snapshot.frames > 0 && !Files.exists(csvPath(id))) writeCsv(id, snapshot.times);
            String combined = reason;
            if (snapshot.error != null && !reason.contains(snapshot.error)) combined += "; " + snapshot.error;
            if (statusOwned) writeStatus("error", id, snapshot.frames, snapshot.unfocusedFrames, snapshot.bufferFull,
                    combined, hookInstalled, hook == null ? null : hook.display(), true);
            else writeAgentError(combined);
        } catch (Throwable e) {
            writeAgentError(reason + "; additionally could not publish capture error: " + message(e));
        } finally {
            activeId = null;
            recordingStatusWritten = false;
            capturePrepared = false;
            statusOwned = false;
        }
    }

    private static void refuse(String id, String reason) {
        if (!id.matches(ID_PATTERN)) return;
        try {
            if (!Files.exists(statusPath(id)))
                writeStatus("error", id, 0, -1, false, reason, hookInstalled, hook == null ? null : hook.display(), false);
        } catch (Throwable e) {
            writeAgentError(reason + "; could not publish status: " + message(e));
        }
    }

    private static void writeCsv(String id, long[] times) throws IOException {
        Path destination = csvPath(id);
        if (Files.exists(destination)) throw new IOException("refusing to overwrite existing CSV " + destination.getFileName());
        Path temporary = root.resolve(id + "-frames.csv.tmp");
        if (Files.exists(temporary)) throw new IOException("refusing to overwrite stale CSV temporary file");
        try (FileChannel channel = FileChannel.open(temporary, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE);
             BufferedWriter writer = new BufferedWriter(new OutputStreamWriter(Channels.newOutputStream(channel), StandardCharsets.UTF_8))) {
            writer.write("frame,nanotime,interval_ns\n");
            for (int i = 0; i < times.length; i++) {
                long interval = i == 0 ? 0L : times[i] - times[i - 1];
                writer.write(Integer.toString(i)); writer.write(',');
                writer.write(Long.toString(times[i])); writer.write(',');
                writer.write(Long.toString(interval)); writer.write('\n');
            }
            writer.flush();
            channel.force(true);
        }
        atomicCreate(temporary, destination);
    }

    private static void writeStatus(String state, String id, int frames, int unfocused, boolean full,
                                    String error, boolean ready, String hookText, boolean replace) throws IOException {
        Path target = statusPath(id);
        String json = "{\"state\":" + quote(state) +
                ",\"id\":" + quote(id) +
                ",\"frames\":" + frames +
                ",\"unfocused_frames\":" + (unfocused < 0 ? "null" : Integer.toString(unfocused)) +
                ",\"buffer_full\":" + full +
                ",\"error\":" + quote(error == null ? "" : error) +
                ",\"metric\":" + quote(METRIC) +
                ",\"hook\":" + (hookText == null ? "null" : quote(hookText)) +
                ",\"hook_ready\":" + ready +
                ",\"updated_at\":" + quote(Instant.now().toString()) + "}\n";
        Path temp = root.resolve(id + "-status." + UUID.randomUUID().toString() + ".tmp");
        byte[] bytes = json.getBytes(StandardCharsets.UTF_8);
        try (FileChannel channel = FileChannel.open(temp, StandardOpenOption.CREATE_NEW, StandardOpenOption.WRITE)) {
            java.nio.ByteBuffer buffer = java.nio.ByteBuffer.wrap(bytes);
            while (buffer.hasRemaining()) channel.write(buffer);
            channel.force(true);
        }
        if (replace) atomicMove(temp, target, true);
        else atomicCreate(temp, target);
    }

    private static void atomicCreate(Path from, Path to) throws IOException {
        try {
            Files.createLink(to, from);
            Files.delete(from);
        } catch (UnsupportedOperationException e) {
            throw new IOException("filesystem does not support atomic no-overwrite publication", e);
        }
    }

    private static void atomicMove(Path from, Path to, boolean replace) throws IOException {
        try {
            if (replace) Files.move(from, to, StandardCopyOption.ATOMIC_MOVE, StandardCopyOption.REPLACE_EXISTING);
            else Files.move(from, to, StandardCopyOption.ATOMIC_MOVE);
        } catch (AtomicMoveNotSupportedException e) {
            throw new IOException("filesystem does not support atomic publication", e);
        }
    }

    private static String quote(String value) {
        StringBuilder out = new StringBuilder(value.length() + 16).append('"');
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            if (c == '"') out.append("\\\"");
            else if (c == '\\') out.append("\\\\");
            else if (c == '\n') out.append("\\n");
            else if (c == '\r') out.append("\\r");
            else if (c == '\t') out.append("\\t");
            else if (c < 0x20) out.append(String.format("\\u%04x", (int) c));
            else out.append(c);
        }
        return out.append('"').toString();
    }

    private static Path statusPath(String id) { return root.resolve(id + "-status.json"); }
    private static Path csvPath(String id) { return root.resolve(id + "-frames.csv"); }

    private static String message(Throwable e) {
        return e.getClass().getSimpleName() + ": " + String.valueOf(e.getMessage());
    }

    private static synchronized void writeAgentError(String text) {
        try {
            long now = System.nanoTime();
            if (text.equals(lastAgentErrorMessage) && now - lastAgentErrorNanos < 10000000000L) return;
            lastAgentErrorMessage = text;
            lastAgentErrorNanos = now;
            Path path = root.resolve("agent-error.txt");
            Files.write(path, (text + System.lineSeparator()).getBytes(StandardCharsets.UTF_8),
                    StandardOpenOption.CREATE, StandardOpenOption.APPEND);
        } catch (Throwable ignored) { }
    }

    private static final class Hook {
        final String targetClass;
        final String targetMethod;
        final String targetDescriptor;
        final String focusMethod;

        Hook(String targetClass, String targetMethod, String targetDescriptor, String focusMethod) {
            this.targetClass = targetClass;
            this.targetMethod = targetMethod;
            this.targetDescriptor = targetDescriptor;
            this.focusMethod = focusMethod;
        }

        String display() {
            return targetClass + "." + targetMethod + targetDescriptor + " normal void return; CPU frame production";
        }

        static Hook read(Path file) throws IOException {
            if (!Files.isRegularFile(file)) throw new IOException("missing " + file.getFileName());
            Properties p = new Properties();
            try (java.io.Reader reader = Files.newBufferedReader(file, StandardCharsets.UTF_8)) { p.load(reader); }
            String cls = p.getProperty("target.class", "").trim();
            String method = p.getProperty("target.method", "").trim();
            String desc = p.getProperty("target.descriptor", "").trim();
            String focus = p.getProperty("focus.method", "").trim();
            String focusDesc = p.getProperty("focus.descriptor", "()Z").trim();
            if (!cls.matches("[A-Za-z0-9_$/]+") || cls.startsWith("/") || cls.contains("//"))
                throw new IOException("target.class must be an exact JVM internal name such as net/minecraft/client/Minecraft");
            if (!method.matches("[A-Za-z_$][A-Za-z0-9_$]*")) throw new IOException("target.method is missing or invalid");
            if (!desc.startsWith("(") || desc.indexOf(')') < 0) throw new IOException("target.descriptor must be an exact JVM method descriptor");
            try {
                Type type = Type.getMethodType(desc);
                if (type.getReturnType().getSort() != Type.VOID) throw new IOException("target method must return void so each normal return can be sampled");
            } catch (IllegalArgumentException e) { throw new IOException("invalid target.descriptor: " + desc, e); }
            if (!focus.isEmpty() && (!focus.matches("[A-Za-z_$][A-Za-z0-9_$]*") || !"()Z".equals(focusDesc)))
                throw new IOException("focus probe must be configured as a public no-argument boolean method with descriptor ()Z");
            if (focus.isEmpty()) focus = null;
            return new Hook(cls, method, desc, focus);
        }
    }

    private static final class HookTransformer implements ClassFileTransformer {
        private final Hook mapping;
        HookTransformer(Hook mapping) { this.mapping = mapping; }

        @Override public byte[] transform(ClassLoader loader, String name, Class<?> classBeingRedefined,
                                          ProtectionDomain domain, byte[] bytes) {
            if (!mapping.targetClass.equals(name)) return null;
            if (transformError != null) return null;
            try {
                final int[] methodMatches = {0};
                final int[] returnMatches = {0};
                final String[] invalid = {null};
                ClassReader reader = new ClassReader(bytes);
                ClassWriter writer = new ClassWriter(reader, ClassWriter.COMPUTE_MAXS);
                ClassVisitor visitor = new ClassVisitor(Opcodes.ASM9, writer) {
                    @Override public MethodVisitor visitMethod(int access, String name, String descriptor,
                                                              String signature, String[] exceptions) {
                        MethodVisitor delegate = super.visitMethod(access, name, descriptor, signature, exceptions);
                        if (!mapping.targetMethod.equals(name) || !mapping.targetDescriptor.equals(descriptor)) return delegate;
                        methodMatches[0]++;
                        if ((access & Opcodes.ACC_STATIC) != 0) {
                            invalid[0] = "configured hook method is static; an instance method is required";
                            return delegate;
                        }
                        return new MethodVisitor(Opcodes.ASM9, delegate) {
                            @Override public void visitInsn(int opcode) {
                                if (opcode == Opcodes.RETURN) {
                                    returnMatches[0]++;
                                    super.visitVarInsn(Opcodes.ALOAD, 0);
                                    super.visitMethodInsn(Opcodes.INVOKESTATIC,
                                            "dev/minecraftsilicon/sampler/FrameSink", "frame", "(Ljava/lang/Object;)V", false);
                                }
                                super.visitInsn(opcode);
                            }
                        };
                    }
                };
                reader.accept(visitor, 0);
                if (methodMatches[0] != 1) {
                    transformError = "configured method not found exactly once in target class";
                    return null;
                }
                if (invalid[0] != null) {
                    transformError = invalid[0];
                    return null;
                }
                if (returnMatches[0] == 0) {
                    transformError = "configured method has no normal void return to sample";
                    return null;
                }
                byte[] transformed = writer.toByteArray();
                hookInstalled = true;
                return transformed;
            } catch (Throwable e) {
                transformError = message(e);
                return null;
            }
        }
    }
}
