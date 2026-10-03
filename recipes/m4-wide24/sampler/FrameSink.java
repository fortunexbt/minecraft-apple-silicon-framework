package m4peak;

import java.lang.reflect.Method;

/** Shared bootstrap-visible buffer so vanilla and Fabric use the same sampler. */
public final class FrameSink {
    public static final long[] times = new long[500000];
    public static volatile int count;
    public static volatile boolean recording;
    public static volatile long deadline;
    public static volatile Object client;
    public static volatile Method focusMethod;
    public static volatile int unfocusedFrames;
    public static volatile String error = "";

    /** End on the next observed frame, retaining the interval that finishes the route. */
    public static void requestStop() { deadline = System.nanoTime(); }

    public static void frame(Object mc) {
        client = mc;
        if (!recording) return;
        long now = System.nanoTime();
        if (count >= times.length) { recording = false; return; }
        try {
            if (focusMethod == null) focusMethod = mc.getClass().getMethod("isWindowActive");
            if (!Boolean.TRUE.equals(focusMethod.invoke(mc))) unfocusedFrames++;
        } catch (Throwable e) { error = e.toString(); recording = false; return; }
        times[count] = now;
        count++;
        if (now >= deadline) recording = false;
    }
}
