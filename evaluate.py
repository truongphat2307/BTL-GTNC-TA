"""Measure all requests individually, no result cache. Save failures for inspection."""
import json
import platform
import sys
import argparse
import math
from collections import defaultdict
from pathlib import Path
from time import perf_counter, perf_counter_ns
from segmenter import Segmenter

ROOT = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--batch-index', type=int)
    parser.add_argument('--batch-size', type=int, default=1000)
    parser.add_argument('--merge-batches', action='store_true')
    args = parser.parse_args()
    cases = json.loads((ROOT / 'testcases.json').read_text(encoding='utf-8'))
    cases += json.loads((ROOT / 'testcases_abbreviations.json').read_text(encoding='utf-8'))
    cases += [dict(category='latency_stress_80_tokens', address=' '.join(['zzzzz'] * 80),
                   version='after', expected=dict(street=None, ward=None, province=None)) for _ in range(64)]
    total_cases = len(cases)
    if args.batch_size <= 0:
        parser.error('batch-size must be positive')
    parts = ROOT / 'benchmark_parts'
    if args.batch_index is not None:
        if not 0 <= args.batch_index < math.ceil(total_cases / args.batch_size):
            parser.error('batch-index out of range')
        cases = cases[args.batch_index * args.batch_size:(args.batch_index + 1) * args.batch_size]
    start = perf_counter()
    engine = None if args.merge_batches else Segmenter.load(ROOT / 'database.json')
    load_seconds = perf_counter() - start
    timings, failures = [], []
    groups = defaultdict(lambda: [0, 0])
    for case in ([] if args.merge_batches else cases):
        start = perf_counter_ns()
        actual = engine.parse(case['address'], case['version'])
        timings.append((perf_counter_ns() - start) / 1e9)
        passed = actual == case['expected']
        groups[case['category']][0] += int(passed)
        groups[case['category']][1] += 1
        if not passed:
            failures.append(dict(**case, actual=actual))
    if args.batch_index is not None:
        parts.mkdir(exist_ok=True)
        part = dict(index=args.batch_index, batch_size=args.batch_size, total_cases=total_cases,
                    timings=timings, failures=failures, groups=dict(groups), load_seconds=load_seconds)
        (parts / f'part_{args.batch_index:03d}.json').write_text(json.dumps(part, ensure_ascii=False), encoding='utf-8')
        print(f'Batch {args.batch_index}: {len(cases)} requests, {len(failures)} mismatches', flush=True)
        return
    if args.merge_batches:
        load_values = []
        for index in range(math.ceil(total_cases / args.batch_size)):
            part = json.loads((parts / f'part_{index:03d}.json').read_text(encoding='utf-8'))
            if (part['index'], part['batch_size'], part['total_cases']) != (index, args.batch_size, total_cases):
                raise ValueError('Incompatible benchmark batch')
            timings.extend(part['timings'])
            failures.extend(part['failures'])
            load_values.append(part['load_seconds'])
            for category, (passed, count) in part['groups'].items():
                groups[category][0] += passed
                groups[category][1] += count
        if len(timings) != total_cases:
            raise ValueError('Incomplete benchmark')
        load_seconds = max(load_values)
        cases = range(total_cases)
    timings.sort()
    report = dict(python=sys.version, platform=platform.platform(), load_seconds=load_seconds,
                  requests=len(cases), passed=len(cases)-len(failures), failed=len(failures),
                  accuracy=(len(cases)-len(failures))/len(cases),
                  mean_seconds=sum(timings)/len(timings), p95_seconds=timings[int(.95*(len(timings)-1))],
                  p99_seconds=timings[int(.99*(len(timings)-1))], max_seconds=max(timings),
                  requests_over_005=sum(t >= .05 for t in timings), groups=dict(groups),
                  note='Generated dictionary-derived tests, not private test accuracy. Startup excluded.')
    (ROOT / 'benchmark.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (ROOT / 'failures.json').write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
