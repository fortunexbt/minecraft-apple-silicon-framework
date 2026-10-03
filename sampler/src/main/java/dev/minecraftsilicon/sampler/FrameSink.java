package dev.minecraftsilicon.sampler;

import java.lang.reflect.Method;
import java.util.Arrays;

/** Bootstrap-visible API used by injected client bytecode. */
public final class FrameSink {
    private static final int MAX_FRAMES = 250000;
    private static final long[] TIMES = new long[MAX_FRAMES];

    private static volatile boolean recording;
    private static volatile boolean finished;
    private static volatile boolean bufferFull;
    private static volatile String error;
    private static volatile String focusName;
    private static volatile Method focusMethod;
    private static volatile Class<?> focusClass;
    private static volatile long startedNanos;
    private static volatile long deadlineNanos;
    private static volatile int count;
    private static volatile int unfocusedFrames;
    private static volatile int focusSamples;
    private static volatile boolean focusConfigured;
    private static volatile int durationSeconds;

    private FrameSink() { }

    public static synchronized void prepare(int seconds, String configuredFocusName) {
        recording = false;
        finished = false;
        bufferFull = false;
        error = null;
        focusName = configuredFocusName;
        focusMethod = null;
        focusClass = null;
        startedNanos = 0L;
        deadlineNanos = 0L;
        count = 0;
        unfocusedFrames = 0;
        focusSamples = 0;
        focusConfigured = configuredFocusName != null && !configuredFocusName.isEmpty();
        durationSeconds = seconds;
        recording = true;
    }

    public static synchronized boolean isFinished() { return finished; }
    public static synchronized boolean hasStarted() { return startedNanos != 0L; }
    public static synchronized int getCount() { return count; }
    /** Returns -1 unless an active focus probe succeeded for every stored frame. */
    public static synchronized int getUnfocusedFrames() {
        return focusConfigured && focusSamples > 0 && focusSamples == count ? unfocusedFrames : -1;
    }
    public static synchronized boolean isBufferFull() { return bufferFull; }
    public static synchronized String getError() { return error; }
    public static synchronized long[] getTimes() { return Arrays.copyOf(TIMES, count); }

    /** Called at the configured instance method's normal void return. */
    public static synchronized void frame(Object client) {
        if (!recording || finished) return;
        if (count >= MAX_FRAMES) {
            bufferFull = true;
            error = "sample buffer full at " + MAX_FRAMES + " frames";
            recording = false;
            finished = true;
            return;
        }

        final long now = System.nanoTime();
        try {
            if (focusConfigured) {
                Method probe = resolveFocusProbe(client);
                if (!Boolean.TRUE.equals(probe.invoke(client))) unfocusedFrames++;
                focusSamples++;
            }
        } catch (Throwable e) {
            error = "focus probe failed: " + describe(e);
            recording = false;
            finished = true;
            return;
        }

        if (startedNanos == 0L) {
            startedNanos = now;
            deadlineNanos = now + durationSeconds * 1000000000L;
        }
        TIMES[count++] = now;

        // Keep the first callback at or after the deadline. Its interval reveals
        // a whole-frame stall that crossed the deadline instead of losing it.
        if (now >= deadlineNanos) {
            recording = false;
            finished = true;
        }
    }

    public static synchronized void stop() {
        recording = false;
        finished = true;
    }

    private static Method resolveFocusProbe(Object client) throws Exception {
        Class<?> cls = client.getClass();
        Method method = focusMethod;
        if (method == null || focusClass != cls) {
            method = cls.getMethod(focusName);
            if (method.getParameterTypes().length != 0 || method.getReturnType() != Boolean.TYPE)
                throw new NoSuchMethodException(focusName + " must be public boolean " + focusName + "() (descriptor ()Z)");
            focusMethod = method;
            focusClass = cls;
        }
        return method;
    }

    private static String describe(Throwable e) {
        Throwable cause = e;
        if (e instanceof java.lang.reflect.InvocationTargetException && e.getCause() != null) cause = e.getCause();
        return cause.getClass().getName() + ": " + String.valueOf(cause.getMessage());
    }
}
