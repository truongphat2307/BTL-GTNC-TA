"""Run editable demo_tests.json; compare accuracy and latency per request."""
import json
import sys
from pathlib import Path
from time import perf_counter_ns
from segmenter import Segmenter

ROOT = Path(__file__).parent


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    start = perf_counter_ns()
    engines = dict(real=Segmenter.load(ROOT / 'database.json'),
                   synthetic=Segmenter.load(ROOT / 'demo_fixture_SYNTHETIC.json'))
    startup_ms = (perf_counter_ns() - start) / 1e6
    cases = json.loads((ROOT / 'demo_tests.json').read_text(encoding='utf-8'))
    results = []
    print('Nạp database một lần. Mỗi request phải <= 50 ms.\n')
    for case in cases:
        start = perf_counter_ns()
        actual = engines[case['database']].parse(case['address'], case['version'])
        elapsed_ms = (perf_counter_ns() - start) / 1e6
        correct = actual == case['expected']
        within_limit = elapsed_ms <= 50
        results.append(dict(**case, actual=actual, elapsed_ms=elapsed_ms,
                            correct=correct, within_50ms=within_limit))
        status = 'PASS' if correct and within_limit else 'FAIL'
        print(f"{case['id']:02d}. {status} | {elapsed_ms:.3f} ms | {case['category']}")
        print('    Input : ' + (case['address'] or '(rỗng)'))
        print('    Output: ' + json.dumps(actual, ensure_ascii=False))
        if not correct:
            print('    Expected: ' + json.dumps(case['expected'], ensure_ascii=False))
    report = dict(requests=len(results), startup_ms=startup_ms,
                  correct=sum(r['correct'] for r in results),
                  within_50ms=sum(r['within_50ms'] for r in results),
                  mean_ms=sum(r['elapsed_ms'] for r in results)/len(results),
                  max_ms=max(r['elapsed_ms'] for r in results), results=results,
                  note='Latency measures parse only; synthetic cases do not assert real geography.')
    (ROOT / 'demo_results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nĐúng: {report['correct']}/{len(results)}; <=50 ms: {report['within_50ms']}/{len(results)}")
    print(f"Trung bình: {report['mean_ms']:.3f} ms; lớn nhất: {report['max_ms']:.3f} ms")
    print(f"Nạp ban đầu: {startup_ms:.1f} ms (không tính vào từng request)")
    print('Chi tiết đã lưu vào demo_results.json')
    return 0 if all(r['correct'] and r['within_50ms'] for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
