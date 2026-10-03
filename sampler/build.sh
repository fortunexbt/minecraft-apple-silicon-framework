#!/usr/bin/env bash
set -euo pipefail

SAMPLER_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
OUTPUT="${1:-$SAMPLER_DIR/build/frame-sampler-agent.jar}"
BUILD_DIR="$SAMPLER_DIR/build"
DEPS_DIR="$BUILD_DIR/deps"
ASM_LOCK="$SAMPLER_DIR/asm.lock"
lock_value() { awk -F= -v key="$1" '$1 == key { sub(/^[^=]*=/, ""); print; exit }' "$ASM_LOCK"; }
ASM_VERSION="$(lock_value version)"
ASM_JAR="$DEPS_DIR/asm-$ASM_VERSION.jar"
ASM_URL="$(lock_value url)"
ASM_SHA256="$(lock_value sha256)"
if [[ -z "$ASM_VERSION" || -z "$ASM_URL" || -z "$ASM_SHA256" ]]; then
  echo "incomplete ASM pin in $ASM_LOCK" >&2
  exit 2
fi

for tool in javac jar curl shasum; do
  command -v "$tool" >/dev/null 2>&1 || { echo "missing required build tool: $tool" >&2; exit 2; }
done

mkdir -p "$DEPS_DIR"
if [[ ! -f "$ASM_JAR" ]] || [[ "$(shasum -a 256 "$ASM_JAR" | awk '{print $1}')" != "$ASM_SHA256" ]]; then
  temp="$DEPS_DIR/asm-$ASM_VERSION.jar.download"
  rm -f "$temp"
  curl --fail --location --silent --show-error "$ASM_URL" --output "$temp"
  actual="$(shasum -a 256 "$temp" | awk '{print $1}')"
  if [[ "$actual" != "$ASM_SHA256" ]]; then
    rm -f "$temp"
    echo "ASM checksum mismatch: expected $ASM_SHA256, got $actual" >&2
    exit 1
  fi
  mv -f "$temp" "$ASM_JAR"
fi

CLASSES="$BUILD_DIR/classes"
AGENT_CLASSES="$BUILD_DIR/agent-classes"
SINK_CLASSES="$BUILD_DIR/sink-classes"
ASM_CLASSES="$BUILD_DIR/asm"
rm -rf "$CLASSES" "$AGENT_CLASSES" "$SINK_CLASSES" "$ASM_CLASSES"
mkdir -p "$CLASSES" "$AGENT_CLASSES" "$SINK_CLASSES" "$ASM_CLASSES"
JAVAC_VERSION="$(javac -version 2>&1 | awk '{print $2}')"
JAVAC_MAJOR="${JAVAC_VERSION%%.*}"
if [[ "$JAVAC_MAJOR" =~ ^[0-9]+$ ]] && (( JAVAC_MAJOR >= 9 )); then
  javac --release 8 -Xlint:-options -encoding UTF-8 -cp "$ASM_JAR" -d "$CLASSES" \
    "$SAMPLER_DIR/src/main/java/dev/minecraftsilicon/sampler/FrameSink.java" \
    "$SAMPLER_DIR/src/main/java/dev/minecraftsilicon/sampler/FrameSamplerAgent.java"
else
  javac -Xlint:-options -encoding UTF-8 -source 8 -target 8 -cp "$ASM_JAR" -d "$CLASSES" \
    "$SAMPLER_DIR/src/main/java/dev/minecraftsilicon/sampler/FrameSink.java" \
    "$SAMPLER_DIR/src/main/java/dev/minecraftsilicon/sampler/FrameSamplerAgent.java"
fi

cp -R "$CLASSES/dev" "$AGENT_CLASSES/"
rm -f "$AGENT_CLASSES/dev/minecraftsilicon/sampler/FrameSink.class"
mkdir -p "$SINK_CLASSES/dev/minecraftsilicon/sampler"
cp "$CLASSES/dev/minecraftsilicon/sampler/FrameSink.class" "$SINK_CLASSES/dev/minecraftsilicon/sampler/"
cp "$SAMPLER_DIR/THIRD_PARTY_NOTICES.md" "$AGENT_CLASSES/THIRD_PARTY_NOTICES.md"
(
  cd "$ASM_CLASSES"
  jar xf "$ASM_JAR"
  rm -f META-INF/MANIFEST.MF
  mkdir -p META-INF
  cp "$SAMPLER_DIR/THIRD_PARTY_NOTICES.md" META-INF/THIRD_PARTY_NOTICES.md
)

OUTPUT_DIR="$(dirname -- "$OUTPUT")"
SINK_OUTPUT="$OUTPUT_DIR/frame-sampler-sink.jar"
mkdir -p "$OUTPUT_DIR"
cat > "$BUILD_DIR/agent-manifest.mf" <<'EOF'
Manifest-Version: 1.0
Premain-Class: dev.minecraftsilicon.sampler.FrameSamplerAgent
Can-Redefine-Classes: false
Can-Retransform-Classes: false

EOF
jar cfm "$OUTPUT" "$BUILD_DIR/agent-manifest.mf" -C "$AGENT_CLASSES" . -C "$ASM_CLASSES" .
jar cf "$SINK_OUTPUT" -C "$SINK_CLASSES" .
echo "Built agent: $OUTPUT"
echo "Built bootstrap helper: $SINK_OUTPUT"
