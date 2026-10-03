#!/bin/sh
set -eu
# Original campaign Frame Bench sampler. No network downloads or game launch.
# Supply local ASM core and tree 9.10.1 JARs; Java 25 is the measured runtime.
if [ "$#" -ne 3 ]; then
  echo 'usage: build.sh ASM_CORE.jar ASM_TREE.jar NEW_BUILD_DIRECTORY' >&2
  exit 2
fi
recipe_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mkdir "$3"
build_dir=$(CDPATH= cd -- "$3" && pwd)
mkdir "$build_dir/classes" "$build_dir/sink"
javac -d "$build_dir/sink" "$recipe_dir/FrameSink.java"
jar --create --file "$build_dir/frame-sink.jar" -C "$build_dir/sink" .
javac -cp "$1:$2:$build_dir/sink" -d "$build_dir/classes" "$recipe_dir/FrameAgent.java"
printf 'Premain-Class: m4peak.FrameAgent\n\n' > "$build_dir/agent-manifest.mf"
jar --create --file "$build_dir/frame-agent.jar" --manifest "$build_dir/agent-manifest.mf" -C "$build_dir/classes" .
echo 'Keep both generated JARs adjacent. See the recipe for the lab-only JVM argument.'
