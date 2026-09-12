#!/usr/bin/env python3
"""Execute patched engine render-work ownership methods through bounded adapters."""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import subprocess
import sys
import time

BASE = 'd728e61e7d835e02c453c70ae9523a40f6c03215'
PREFIX = 'engine/src/flutter/shell/common/'
CASES = ('zero-item', 'interleaved', 'stale-pending', 'untagged',
         'resubmission', 'early-end', 'pipeline-full', 'real-error', 'allocation-failure',
         'retained-retry', 'retained-reuse', 'stale-topology')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def section(text, start, end):
    begin = text.index(start)
    return text[begin:text.index(end, begin)].rstrip() + '\n'


def core_off():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    core_off()
    repo = Path(__file__).resolve().parents[2]
    output = args.output.absolute()
    output.mkdir(parents=True, exist_ok=False)
    started_all = time.monotonic()
    result = {'base': BASE, 'kind': 'render-work-method-regression',
              'status': 'FAIL', 'sources': {}, 'sections': {}, 'runs': [],
              'boundaries': [
                  'Patched production Work/Admission/Scope, Pipeline/FrameItem, Animator BeginFrame/Render/EndFrame/AwaitVSync/DrawLastLayerTrees, VsyncWaiter FireCallback, Shell OnAnimatorDraw/OnAnimatorDrawDenialRenderWork and Rasterizer Draw/DrawDenialRenderOutputs/DrawToSurfacesUnsafe/ShouldResubmitFrame/StoreDenialPendingTask/ResubmitDenialRenderWork execute unchanged.',
                  'DrawToSurfaceUnsafe executes its exact admission prefix; subsequent GPU allocation/presentation is an explicit counted success/failure/retry adapter.',
                  'Dart dispatch is synchronous callback adapter; task runners, time, tracing, weak lifetimes and semaphore are deterministic single-thread adapters.',
                  'Actual public embedder.h is compiled with exact function-pointer ABI assertions for both new exports.',
                  'Projection boundary supplies already-projected synthetic-view LayerTreeTasks; graphics layer transforms are not executed.',
                  'Actual resubmission handling and FrameItem creation execute; retry decision comes from GPU adapter.',
                  'RequestFrame records pipeline-full retry without scheduling another vsync. Delayed idle callbacks remain queued.'
              ]}
    try:
        helper_path = repo / 'scripts/host/repository-test-report.py'
        specification = importlib.util.spec_from_file_location('frame_order_report', helper_path)
        helper = importlib.util.module_from_spec(specification)
        sys.dont_write_bytecode = True
        specification.loader.exec_module(helper)
        result['process_runner_sha256'] = digest(helper_path.read_bytes())
        files = {}
        patches = sorted((repo / 'patches/flutter-engine-d728e61e').glob('000[1234]-*.patch'))
        if len(patches) != 4:
            raise ValueError('Expected exact prerequisite patches 0001 through 0004')
        paths = {PREFIX + name for name in ('pipeline.h', 'rasterizer.h', 'animator.cc', 'rasterizer.cc', 'shell.cc', 'vsync_waiter.cc')}
        for patch in patches:
            paths.update(re.findall(r'^--- a/(.+)$', patch.read_text(), re.MULTILINE))
        for path in sorted(paths):
            data = subprocess.check_output(
                ['git', '-C', str(args.source), 'show', BASE + ':' + path], timeout=10)
            saved = output / 'source' / path
            saved.parent.mkdir(parents=True, exist_ok=True)
            saved.write_bytes(data)
            result['sources'][path] = digest(data)
        result['patches'] = {}
        for patch in patches:
            subprocess.run(['git', 'apply', '--check', str(patch)], cwd=output / 'source', check=True, timeout=10)
            subprocess.run(['git', 'apply', str(patch)], cwd=output / 'source', check=True, timeout=10)
            result['patches'][patch.name] = digest(patch.read_bytes())
        for name in ('pipeline.h', 'rasterizer.h', 'animator.cc', 'rasterizer.cc', 'shell.cc', 'vsync_waiter.cc'):
            files[name] = (output / 'source' / PREFIX / name).read_text()
        sections = {
            'WORK': section(files['rasterizer.h'], 'struct DenialRenderWork {', '// The information to draw to all views of a frame.'),
            'PIPELINE': section(files['pipeline.h'], 'struct PipelineProduceResult', '}  // namespace flutter'),
            'FRAME_ITEM': section(files['rasterizer.h'], 'struct FrameItem {', '//------------------------------------------------------------------------------'),
            'BEGIN_FRAME': section(files['animator.cc'], 'void Animator::BeginFrame(', 'void Animator::EndFrame()'),
            'END_FRAME': section(files['animator.cc'], 'void Animator::EndFrame()', 'void Animator::Render('),
            'RENDER': section(files['animator.cc'], 'void Animator::Render(', 'const std::weak_ptr<VsyncWaiter>'),
            'ALL_VIEWS': section(files['animator.cc'], 'void Animator::OnAllViewsRendered()', 'void Animator::ScheduleSecondaryVsyncCallback'),
            'DRAW': section(files['rasterizer.cc'], 'DrawStatus Rasterizer::Draw(', 'bool Rasterizer::ShouldResubmitFrame'),
            'AWAIT_VSYNC': section(files['animator.cc'], 'void Animator::AwaitVSync()', 'void Animator::OnAllViewsRendered()'),
            'DRAW_LAST': section(files['animator.cc'], 'void Animator::DrawLastLayerTrees(', 'void Animator::RequestFrame('),
            'FIRE_CALLBACK': section(files['vsync_waiter.cc'], 'void VsyncWaiter::FireCallback(', 'void VsyncWaiter::PauseDartEventLoopTasks()'),
            'STORE_PENDING': section(files['rasterizer.cc'], 'void Rasterizer::StoreDenialPendingTask(', 'void Rasterizer::MarkDenialWorkTextures()'),
            'RESUBMIT_WORK': section(files['rasterizer.cc'], 'void Rasterizer::ResubmitDenialRenderWork(', 'std::shared_ptr<flutter::TextureRegistry> Rasterizer::GetTextureRegistry()'),
            'DRAW_SURFACES': section(files['rasterizer.cc'], 'std::unique_ptr<FrameItem> Rasterizer::DrawToSurfacesUnsafe(', r'/// \see Rasterizer::DrawToSurfaces'),
            'DRAW_SURFACE_PREFIX': section(files['rasterizer.cc'], 'DrawSurfaceStatus Rasterizer::DrawToSurfaceUnsafe(', '  DlCanvas* embedder_root_canvas = nullptr;'),
            'SHELL_DRAW_WORK': section(files['shell.cc'], 'void Shell::OnAnimatorDrawDenialRenderWork(', '// |PlatformView::Delegate|'),
            'DRAW_RETAINED': section(files['rasterizer.cc'], 'void Rasterizer::DrawDenialRenderOutputs(', 'std::unique_ptr<LayerTreeTask> Rasterizer::ReprojectDenialRenderOutputTask('),
            'SHELL_DRAW': section(files['shell.cc'], 'void Shell::OnAnimatorDraw(', '// |Animator::Delegate|'),
        }
        # The resubmission helper has no nested function, and its closing brace
        # is part of the exact source slice, not synthesized implementation.
        resubmit_start = files['rasterizer.cc'].index('bool Rasterizer::ShouldResubmitFrame')
        resubmit_end = files['rasterizer.cc'].index('\n}', resubmit_start) + 2
        sections['RESUBMIT'] = files['rasterizer.cc'][resubmit_start:resubmit_end] + '\n'
        fixture = repo / 'tools/denial-engine-tests/render-work.cc'
        result['fixture_sha256'] = digest(fixture.read_bytes())
        result['runner_sha256'] = digest(Path(__file__).read_bytes())
        unit_text = fixture.read_text()
        for name, value in sections.items():
            marker = '// @' + name + '@'
            if unit_text.count(marker) != 1:
                raise ValueError('Expected exactly one fixture marker: ' + marker)
            unit_text = unit_text.replace(marker, value)
            (output / (name.lower() + '.inc')).write_text(value)
            result['sections'][name] = digest(value.encode())
        if re.search(r'^// @[A-Z_]+@$', unit_text, re.MULTILINE):
            raise ValueError('Unreplaced fixture marker')
        unit = output / 'fixture.cc'
        unit.write_text(unit_text)
        result['translation_unit_sha256'] = digest(unit.read_bytes())
        binary = output / 'fixture'
        command = [os.environ.get('CXX', 'c++'), '-std=c++20', '-Wall', '-Wextra',
                   '-Werror', '-pthread', str(unit), '-o', str(binary)]
        with (output / 'build.stdout.log').open('w') as stdout, (output / 'build.stderr.log').open('w') as stderr:
            status, reason, duration = helper.execute(command, 30, stdout, stderr)
        result['build'] = {'command': command, 'status': status, 'reason': reason,
                           'duration_seconds': duration}
        if status == 'PASS':
            for mode in CASES:
                stdout_path = output / (mode + '.stdout.log')
                with stdout_path.open('w') as stdout, (output / (mode + '.stderr.log')).open('w') as stderr:
                    status, reason, duration = helper.execute([str(binary), mode], 10, stdout, stderr)
                if status == 'PASS' and stdout_path.read_text().splitlines().count('PASS ' + mode) != 1:
                    status, reason = 'FAIL', 'missing or repeated exact PASS marker'
                result['runs'].append({'case': mode, 'status': status, 'reason': reason,
                                      'duration_seconds': duration})
            if len(result['runs']) == len(CASES) and all(run['status'] == 'PASS' for run in result['runs']):
                result['status'] = 'PASS'
    except (OSError, ValueError, AssertionError, subprocess.SubprocessError) as error:
        result['error'] = repr(error)
    finally:
        result['duration_seconds'] = time.monotonic() - started_all
        (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps(result, indent=2))
    return result['status'] != 'PASS'


if __name__ == '__main__':
    raise SystemExit(main())
