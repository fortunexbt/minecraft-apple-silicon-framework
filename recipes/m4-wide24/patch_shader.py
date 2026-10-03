#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-3.0-only
# Changes to MakeUp Ultra Fast 9.5f by KDXavier; AMD CAS copyright retained.
"""Patch a new local shader copy; preserve every untouched upstream member."""
import hashlib
import json
from pathlib import Path
import sys
import zipfile

HERE = Path(__file__).resolve().parent

def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: patch_shader.py ORIGINAL.zip NEW.zip')
    source, output = map(Path, sys.argv[1:])
    inputs = json.loads((HERE / 'shader-inputs.json').read_text())
    if hashlib.sha256(source.read_bytes()).hexdigest() != inputs['upstream_sha256']:
        raise SystemExit('Input is not the measured upstream MakeUp 9.5f archive')
    operations = json.loads((HERE / 'shader-operations.json').read_text())
    with zipfile.ZipFile(source) as original:
        changed = {}
        for member, spec in operations.items():
            text = original.read(member).decode()
            for change in spec['changes']:
                if text.count(change['before']) != 1:
                    raise SystemExit('Expected unique source context in ' + member)
                text = text.replace(change['before'], change['after'], 1)
            changed[member] = text.encode()
            if hashlib.sha256(changed[member]).hexdigest() != spec['expected_sha256']:
                raise SystemExit('Patched member differs from measured source: ' + member)
        with output.open('xb') as stream, zipfile.ZipFile(stream, 'w') as patched:
            for entry in original.infolist():
                patched.writestr(entry, changed.get(entry.filename, original.read(entry.filename)))
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(output) as patched:
        if original.namelist() != patched.namelist():
            raise SystemExit('Archive layout changed')
        for member in original.namelist():
            expected = changed.get(member, original.read(member))
            if patched.read(member) != expected:
                raise SystemExit('Member verification failed: ' + member)
    print('Verified exposure initialization and finite nine-tap CAS; all other members unchanged')
    print(hashlib.sha256(output.read_bytes()).hexdigest())

if __name__ == '__main__':
    main()
