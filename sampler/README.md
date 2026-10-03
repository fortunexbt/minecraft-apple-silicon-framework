# Frame sampler

This small Java agent samples the CPU frame-production boundary of one explicitly mapped instance method. It does not measure GPU execution, frame presentation, display refresh, input latency, or the number of frames the display showed. The hook runs immediately before each normal `void` return and includes work that happened earlier in that method, such as a limiter wait.

The hook is version-specific. A missing or mismatched mapping fails closed; the agent does not try alternate methods. A run still needs independent checks for the expected world and dimension, framebuffer size and scaling, game focus, and visual validity. The sampler cannot prove those facts.

## Build

Use a JDK with `javac` and `jar`, plus `curl` and `shasum`. Java 8 source and bytecode are targeted so the agent can run on the Java runtime already selected for an instance. Minecraft's own version decides which Java runtime that instance needs.

```sh
./sampler/build.sh
```

The build writes `sampler/build/frame-sampler-agent.jar` and its adjacent `sampler/build/frame-sampler-sink.jar`. ASM 9.10.1 is downloaded from Maven Central during the build and checked against the SHA-256 in `asm.lock`; the upstream release list and license are linked in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). No dependency or agent binary is committed to the repository.

## Configure one instance

Create a dedicated control directory and write `hook.properties` in it:

```properties
target.class=net/minecraft/client/Minecraft
target.method=renderFrame
target.descriptor=(Z)V
focus.method=isWindowActive
focus.descriptor=()Z
```

Those values are only an example. Confirm the exact internal class name, method name, descriptor, and focus probe against the selected Minecraft and loader versions. Method descriptors use JVM syntax. Do not copy the example merely because it has worked for another version. The target method must be an instance method returning `void`; a focus probe, when supplied, must be a public no-argument `boolean` method. If the focus probe is omitted, `unfocused_frames` is JSON `null`, never a guessed zero.

Add this single Java argument to the chosen Prism instance and restart it:

```text
"-javaagent:/absolute/path/frame-sampler-agent.jar=/absolute/path/to/control-directory"
```

Use the runtime already configured for that instance. An agent already attached to a running JVM cannot retroactively instrument a class that has loaded; the sampler reports that condition as an error.

## Request and status protocol

After the instance is ready, write `measure.properties` in the control directory. Use an atomic temporary-file rename when the CLI creates it.

```properties
id=sample-001
seconds=20
```

IDs must match `[A-Za-z0-9_-]{1,100}`. Duration is 5–30 seconds; it defaults to 20. The sampler accepts one capture at a time. The same ID cannot be replayed: an existing `<id>-status.json`, `<id>-frames.csv`, or CSV temporary file blocks it. A restart with a stale `starting` status does not resume that capture.

The atomic `<id>-status.json` moves through `starting`, `recording`, then `done` or `error`. It includes `state`, `id`, `frames`, `unfocused_frames`, `buffer_full`, `error`, `metric`, `hook`, `hook_ready`, and `updated_at`. `unfocused_frames` is `null` when no usable focus observations were collected. The `done` status is installed only after `<id>-frames.csv` has been flushed, synced, and atomically renamed into place. CSV columns are `frame,nanotime,interval_ns`; row zero's interval is zero. Time values use `System.nanoTime()` and are comparable only within that JVM run.

A control program timing out while it waits has not proved that Minecraft or the capture stopped. Leave the status unresolved and inspect it again; only an agent-published `done` or `error` is terminal. A bounded status wait must not kill the game process.

The agent and the adjacent bootstrap helper JAR must stay together. The helper is a separate JAR so only its public recorder class is visible to injected client bytecode. The in-memory limit is 250,000 frame rows. Hitting it publishes an `error` status with `buffer_full: true`; that CSV is incomplete and must be rejected. Focus checks use reflection once to resolve the configured probe and then once per sampled frame. This adds some work to the measured thread, so compare captures made with the same agent build and configuration.

## Synthetic smoke check

`./sampler/smoke.sh` builds the agent and runs a tiny Java fixture with no Minecraft or graphics runtime. It checks the lifecycle, sequential captures, non-replay of a finished ID after a JVM restart, the frame CSV schema, observed focus counts, and fail-closed hook and focus probes. It validates bytecode injection and the file protocol only; it is not a Minecraft compatibility or performance result.
