#!/usr/bin/env bash
set -euo pipefail

SAMPLER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AGENT="${1:-$SAMPLER_DIR/build/frame-sampler-agent.jar}"
TEMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/frame-sampler-smoke.XXXXXX")"
trap 'rm -rf "$TEMP_DIR"' EXIT

"$SAMPLER_DIR/build.sh" "$AGENT"
for tool in javac java python3; do
  command -v "$tool" >/dev/null 2>&1 || { echo "missing required smoke tool: $tool" >&2; exit 2; }
done

CLASSES="$TEMP_DIR/classes"
mkdir -p "$CLASSES"
JAVAC_VERSION="$(javac -version 2>&1 | awk '{print $2}')"
JAVAC_MAJOR="${JAVAC_VERSION%%.*}"
if [[ "$JAVAC_MAJOR" =~ ^[0-9]+$ ]] && (( JAVAC_MAJOR >= 9 )); then
  javac --release 8 -Xlint:-options -d "$CLASSES" "$SAMPLER_DIR"/smoke/fixture/*.java
else
  javac -Xlint:-options -source 8 -target 8 -d "$CLASSES" "$SAMPLER_DIR"/smoke/fixture/*.java
fi

CONTROL="$TEMP_DIR/control"
mkdir -p "$CONTROL"
cat > "$CONTROL/hook.properties" <<'EOF'
target.class=fixture/GameClient
target.method=renderFrame
target.descriptor=(Z)V
focus.method=isWindowActive
focus.descriptor=()Z
EOF
cat > "$CONTROL/measure.properties" <<'EOF'
id=smoke_valid_001
seconds=5
EOF
java "-javaagent:$AGENT=$CONTROL" -cp "$CLASSES" fixture.Runner 12000 >"$TEMP_DIR/valid.log" 2>&1 &
JAVA_PID=$!
seen_starting=0
seen_recording=0
for ((i=0; i<900; i++)); do
  status="$CONTROL/smoke_valid_001-status.json"
  if [[ -f "$status" ]]; then
    state="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["state"])' "$status")"
    [[ "$state" == starting ]] && seen_starting=1
    [[ "$state" == recording ]] && seen_recording=1
    [[ "$state" == done || "$state" == error ]] && break
  fi
  sleep 0.02
done

cat > "$CONTROL/measure.next" <<'EOF'
id=smoke_valid_002
seconds=5
EOF
mv "$CONTROL/measure.next" "$CONTROL/measure.properties"
seen_second_starting=0
seen_second_recording=0
for ((i=0; i<500; i++)); do
  status="$CONTROL/smoke_valid_002-status.json"
  if [[ -f "$status" ]]; then
    state="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["state"])' "$status")"
    [[ "$state" == starting ]] && seen_second_starting=1
    [[ "$state" == recording ]] && seen_second_recording=1
    [[ "$state" == done || "$state" == error ]] && break
  fi
  sleep 0.02
done
wait "$JAVA_PID"
cp "$CONTROL/smoke_valid_002-status.json" "$TEMP_DIR/expected-status.json"
shasum -a 256 "$CONTROL/smoke_valid_002-frames.csv" > "$TEMP_DIR/expected-csv.sha256"
# Starting a new JVM with the last finished ID must leave its published receipt untouched.
java "-javaagent:$AGENT=$CONTROL" -cp "$CLASSES" fixture.Runner 500 >"$TEMP_DIR/replay.log" 2>&1
cmp "$TEMP_DIR/expected-status.json" "$CONTROL/smoke_valid_002-status.json"
shasum -a 256 -c "$TEMP_DIR/expected-csv.sha256" >/dev/null
python3 - "$CONTROL" "$seen_starting" "$seen_recording" "$seen_second_starting" "$seen_second_recording" <<'PY'
import csv, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
seen_starting, seen_recording, seen_second_starting, seen_second_recording = map(int, sys.argv[2:])
status = json.loads((root / "smoke_valid_001-status.json").read_text())
assert seen_starting or seen_recording, "no active capture state was observed"
assert seen_recording, "recording state was not observed"
assert seen_second_starting or seen_second_recording, "no active second capture state was observed"
assert seen_second_recording, "second capture's recording state was not observed"
assert status["state"] == "done", status
assert status["hook_ready"] is True, status
assert status["metric"] == "cpu_frame_production", status
assert status["error"] == "", status
assert status["frames"] >= 100, status
assert isinstance(status["unfocused_frames"], int) and status["unfocused_frames"] > 0, status
assert status["buffer_full"] is False, status
with (root / "smoke_valid_001-frames.csv").open(newline="") as f:
    rows = list(csv.DictReader(f))
assert len(rows) == status["frames"], (len(rows), status)
assert list(rows[0]) == ["frame", "nanotime", "interval_ns"]
assert int(rows[0]["interval_ns"]) == 0
assert max(int(row["interval_ns"]) for row in rows[1:]) > 0
second = json.loads((root / "smoke_valid_002-status.json").read_text())
assert second["state"] == "done" and second["frames"] >= 100, second
assert second["unfocused_frames"] is not None, second
print("sampler lifecycle, two sequential captures, and bootstrap injection passed:", status["frames"], "frames; second capture:", second["frames"])
PY

BAD="$TEMP_DIR/bad-control"
mkdir -p "$BAD"
cat > "$BAD/hook.properties" <<'EOF'
target.class=fixture/GameClient
target.method=missingFrame
target.descriptor=(Z)V
focus.method=isWindowActive
EOF
cat > "$BAD/measure.properties" <<'EOF'
id=smoke_missing_001
seconds=5
EOF
java "-javaagent:$AGENT=$BAD" -cp "$CLASSES" fixture.Runner 1000 >"$TEMP_DIR/missing.log" 2>&1 &
JAVA_PID=$!
for ((i=0; i<100; i++)); do
  status="$BAD/smoke_missing_001-status.json"
  if [[ -f "$status" ]]; then
    state="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["state"])' "$status")"
    [[ "$state" == error ]] && break
  fi
  sleep 0.1
done
wait "$JAVA_PID"
python3 - "$BAD" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
status = json.loads((root / "smoke_missing_001-status.json").read_text())
assert status["state"] == "error", status
assert status["hook_ready"] is False, status
assert "not found exactly once" in status["error"], status
assert not (root / "smoke_missing_001-frames.csv").exists()
print("fail-closed hook check passed")
PY

FOCUS_BAD="$TEMP_DIR/bad-focus-control"
mkdir -p "$FOCUS_BAD"
cat > "$FOCUS_BAD/hook.properties" <<'EOF'
target.class=fixture/GameClient
target.method=renderFrame
target.descriptor=(Z)V
focus.method=missingWindowProbe
focus.descriptor=()Z
EOF
cat > "$FOCUS_BAD/measure.properties" <<'EOF'
id=smoke_focus_unknown_001
seconds=5
EOF
java "-javaagent:$AGENT=$FOCUS_BAD" -cp "$CLASSES" fixture.Runner 500 >"$TEMP_DIR/focus.log" 2>&1
python3 - "$FOCUS_BAD" <<'PY'
import json, pathlib, sys
root = pathlib.Path(sys.argv[1])
status = json.loads((root / "smoke_focus_unknown_001-status.json").read_text())
assert status["state"] == "error", status
assert status["unfocused_frames"] is None, status
assert "focus probe failed" in status["error"], status
print("unknown focus probe fails closed without inventing a zero count")
PY
