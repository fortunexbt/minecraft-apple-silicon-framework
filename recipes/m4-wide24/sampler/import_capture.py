#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Import a real campaign text completion; never create sampler status files."""
import hashlib
import json
from pathlib import Path
import sys
from silicon_shader.measure import analyze, read_csv, validate

def properties(path):
    return dict(line.split('=', 1) for line in path.read_text().splitlines() if '=' in line)

def main():
    if len(sys.argv) != 5:
        raise SystemExit('usage: import_capture.py CONTROL RUN_ID OPERATOR_MANIFEST.json NEW_CAPTURE.json')
    root, run, manifest_path, output = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4])
    from silicon_shader.common import identifier
    identifier(run)
    manifest = json.loads(manifest_path.read_text())
    completion_path = root / (run + '-done.txt')
    completion = properties(completion_path)
    start = properties(root / (run + '-start.txt'))
    if (root / (run + '-route.txt')).exists():
        from silicon_shader.workload import import_route
        receipt = import_route(root, run)
        if receipt['samples'][0]['framebuffer'] != manifest['observed']['framebuffer']:
            raise SystemExit('Observed framebuffer differs from standard route')
        route = None
    else:
        route = json.loads((root / (run + '-route.json')).read_text())
    csv_path = root / (run + '-frames.csv')
    values, count = read_csv(csv_path)
    if (completion.get('frames') != str(count) or completion.get('unfocused_frames') != '0'
        or completion.get('frame_sink_error') != '' or completion.get('buffer_full') != 'false'):
        raise SystemExit('Missing or invalid real sampler completion')
    if (start.get('live_inactivity_policy') != 'MINIMIZED' or start.get('live_throttle_reason') != 'NONE'
        or start.get('live_frame_limit') != str(manifest['observed']['cap'])):
        raise SystemExit('Live sampler policy/cap differs from operator manifest')
    if route is not None and (not 20 <= route['seconds'] <= 31 or 'normal world simulation' not in route['kind']):
        raise SystemExit('Incomplete or incompatible route')
    if completion.get('hook') != 'Minecraft.renderFrame(boolean) return; CPU frame-production interval, including limiter':
        raise SystemExit('Unsupported campaign hook')
    result = dict(id=run, profile='standard-flight' if route is None else 'historical-showcase', status='done', metric='cpu_frame_production',
        expected=manifest['expected'], observed=manifest['observed'], visual=manifest['visual'],
        completion=dict(unfocused_frames=0, buffer_full=False, error=''), metrics=analyze(values),
        provenance=dict(csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
            completion_sha256=hashlib.sha256(completion_path.read_bytes()).hexdigest(), hook=completion['hook']))
    errors = validate(result)
    if errors:
        raise SystemExit('; '.join(errors))
    with output.open('x') as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
        stream.write('\n')
    print('Imported real completion and operator-reviewed context; remains self-reported')

if __name__ == '__main__':
    main()
