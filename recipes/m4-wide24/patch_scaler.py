#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Reproduce the measured scaler class from a pinned upstream local copy."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
MEMBER = 'dev/zelo/renderscale/RenderScale.class'

def main():
    if len(sys.argv) != 5:
        raise SystemExit('usage: patch_scaler.py ORIGINAL.jar ASM_CORE.jar ASM_TREE.jar NEW.jar')
    original, core, tree, output = (Path(x).resolve() for x in sys.argv[1:])
    inputs = json.loads((HERE / 'shader-inputs.json').read_text())
    if hashlib.sha256(original.read_bytes()).hexdigest() != inputs['renderscale_upstream_sha256']:
        raise SystemExit('Input is not the measured RenderScale 1.4.0-alpha.6 build')
    if output.exists() or output.is_symlink():
        raise SystemExit('Refusing an existing output')
    dependencies = str(core) + ':' + str(tree)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        subprocess.run(['javac', '-cp', dependencies, '-d', str(root), str(HERE / 'RenderScaleStraightPatch.java'), str(HERE / 'RenderScaleQuantizedPatch.java')], check=True)
        classpath = str(root) + ':' + dependencies
        first, final = root / 'straight.jar', root / 'quantized.jar'
        subprocess.run(['java', '-cp', classpath, 'RenderScaleStraightPatch', str(original), str(first)], check=True)
        subprocess.run(['java', '-cp', classpath, 'RenderScaleQuantizedPatch', str(first), str(final)], check=True)
        with zipfile.ZipFile(original) as a, zipfile.ZipFile(final) as b:
            if set(a.namelist()) != set(b.namelist()):
                raise SystemExit('Archive layout changed')
            if hashlib.sha256(b.read(MEMBER)).hexdigest() != inputs['renderscale_class_sha256']:
                raise SystemExit('Result differs from the measured scaler class')
            for member in a.namelist():
                if member != MEMBER and a.read(member) != b.read(member):
                    raise SystemExit('Unexpected changed member: ' + member)
        with output.open('xb') as stream:
            stream.write(final.read_bytes())
    print('Verified measured scaler class and all unchanged archive members')
    print(hashlib.sha256(output.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
