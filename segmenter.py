"""Offline dictionary address segmentation. Python >= 3.10, standard library only."""
import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from time import perf_counter_ns

KINDS = ('province', 'district', 'ward', 'street')
ABBREVIATIONS = {
    'BĐ': 'bán đảo', 'BD': 'bán đảo', 'B.Đ': 'bán đảo', 'B.D': 'bán đảo',
    'HXH': 'Hồ Xuân Hương', 'H.X.H': 'Hồ Xuân Hương',
}
ABBREVIATION_RE = re.compile(r'(?<!\w)(' + '|'.join(
    re.escape(s) for s in sorted(ABBREVIATIONS, key=len, reverse=True)) + r')(?!\w)', re.I)


class FieldLimit(Exception):
    """Internal signal: leave this field empty and try the next field."""


def expand_abbreviations(value):
    return ABBREVIATION_RE.sub(lambda m: ABBREVIATIONS[m[0].upper()], value)

PREFIX = {
    'province': r'^(?:tinh|thanh pho|tp|t)\s+',
    'district': r'^(?:quan|huyen|thi xa|thanh pho|q|h|tx|tp)\s+',
    'ward': r'^(?:phuong|xa|thi tran|dac khu|p|x|tt)\s+',
    'street': r'^(?:duong|street)\s+',
}


def normalize(value, keep_accents=False):
    value = ''.join((' ' if i and c.isupper() and value[i-1].islower() else '') + c
                    for i, c in enumerate(value))
    if keep_accents:
        return ' '.join(re.sub(r'[\W_]+', ' ', unicodedata.normalize('NFC', value.lower())).split())
    value = unicodedata.normalize('NFD', value.lower().replace('đ', 'd'))
    value = ''.join(c for c in value if unicodedata.category(c) != 'Mn')
    return ' '.join(re.sub(r'[^a-z0-9]+', ' ', value).split())


def key(value, kind):
    return re.sub(PREFIX[kind], '', normalize(value)).replace(' ', '')


def edits1(value):
    """Deletion signatures: bounded fuzzy candidate retrieval, not a full scan."""
    return {value[:i] + value[i+1:] for i in range(len(value))}


def distance1(a, b):
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    i = j = errors = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
            j += 1
        else:
            errors += 1
            j += 1
            if errors > 1:
                return False
    return True


class Segmenter:
    def __init__(self, rows, max_candidates=512, request_budget_seconds=.040,
                 field_budget_seconds=.008):
        if not 0 < request_budget_seconds <= .040 or not 0 < field_budget_seconds <= .008:
            raise ValueError('Budgets must be positive; request <= .040 s, field <= .008 s')
        self.request_budget_ns = int(request_budget_seconds * 1e9)
        self.field_budget_ns = int(field_budget_seconds * 1e9)
        self.max_candidates = max_candidates
        self.exact = {k: defaultdict(list) for k in KINDS}
        self.deleted = {k: defaultdict(set) for k in KINDS}
        self.lengths = {k: 1 for k in KINDS}
        self.rows = {}
        self.labels = {}
        for row in rows:
            rid = row['id']
            if rid in self.rows:
                raise ValueError(f'Duplicate id: {rid}')
            if row['kind'] not in KINDS or not row['name']:
                raise ValueError(f'Invalid row: {row}')
            self.rows[rid] = row
            self.labels[rid] = (normalize(row['name']), normalize(row['name'], keep_accents=True))
            kind = row['kind']
            for alias in [row['name'], *row.get('aliases', [])]:
                word = key(alias, kind)
                if not word:
                    raise ValueError(f'Empty normalized alias: {alias}')
                self.exact[kind][word].append(rid)
                self.lengths[kind] = max(self.lengths[kind], len(normalize(alias).split()) + 2)
        for row in rows:
            parent = row.get('parent_id')
            if parent and parent not in self.rows:
                raise ValueError(f'Unknown parent: {parent}')
            visited = {row['id']}
            while parent:
                if parent in visited:
                    raise ValueError('Parent cycle')
                visited.add(parent)
                parent = self.rows[parent].get('parent_id')
        for kind in KINDS:
            for word in self.exact[kind]:
                if len(word) >= 5:
                    for signature in edits1(word):
                        self.deleted[kind][signature].add(word)

    @classmethod
    def load(cls, filename):
        return cls(json.loads(Path(filename).read_text(encoding='utf-8')))

    def _compatible(self, rid, selected, version):
        row = self.rows[rid]
        if version and row.get('version') != version:
            return False
        parent = row.get('parent_id')
        ancestors = {}
        while parent:
            item = self.rows[parent]
            ancestors[item['kind']] = parent
            parent = item.get('parent_id')
        return all(k not in ancestors or ancestors[k] == v for k, v in selected.items())

    def parse(self, address, version=None, include_district=False):
        deadline = perf_counter_ns() + self.request_budget_ns
        if not isinstance(address, str):
            raise TypeError('address must be a string')
        if len(address) > 512:
            raise ValueError('Maximum address length: 512 characters')
        address = expand_abbreviations(address)
        tokens = normalize(address).split()
        accented_tokens = normalize(address, keep_accents=True).split()
        if len(tokens) > 80:
            raise ValueError('Maximum address length: 80 tokens')
        chosen, used, ambiguous = {}, set(), []
        for kind in KINDS:
            if perf_counter_ns() >= deadline:
                break
            field_deadline = min(deadline, perf_counter_ns() + self.field_budget_ns)
            try:
                matches = self._find(kind, tokens, accented_tokens, used, chosen, version, field_deadline)
            except FieldLimit:
                continue
            if not matches:
                continue
            best = max(v[0] for v in matches.values())
            winners = [rid for rid, v in matches.items() if v[0] == best]
            if len(winners) != 1:
                ambiguous.append(kind)
                continue
            rid = winners[0]
            chosen[kind] = rid
            _, start, end = matches[rid]
            used.update(range(start, end))
        result = {k: self.rows[chosen[k]]['name'] if k in chosen else None
                  for k in ('street', 'ward', 'province')}
        if include_district:
            result['district'] = self.rows[chosen['district']]['name'] if 'district' in chosen else None
        return result

    def _find(self, kind, tokens, accented_tokens, used, chosen, version, deadline):
        matches = {}
        for start in range(len(tokens)):
            for end in range(start + 1, min(len(tokens), start + self.lengths[kind]) + 1):
                if perf_counter_ns() >= deadline:
                    raise FieldLimit
                if any(i in used for i in range(start, end)):
                    continue
                word = key(' '.join(tokens[start:end]), kind)
                candidates = [(word, 0)] if word in self.exact[kind] else []
                if not candidates and len(word) >= 5:
                    pool = set(self.deleted[kind].get(word, ()))
                    for signature in edits1(word):
                        if perf_counter_ns() >= deadline:
                            raise FieldLimit
                        if signature in self.exact[kind]:
                            pool.add(signature)
                        pool.update(self.deleted[kind].get(signature, ()))
                        if len(pool) > self.max_candidates:
                            break
                    if len(pool) <= self.max_candidates:
                        candidates = [(w, 1) for w in pool if distance1(word, w)]
                for candidate, error in candidates:
                    if len(self.exact[kind][candidate]) > self.max_candidates:
                        raise FieldLimit
                    for rid in self.exact[kind][candidate]:
                        if perf_counter_ns() >= deadline:
                            raise FieldLimit
                        if not self._compatible(rid, chosen, version):
                            continue
                        span = ' '.join(tokens[start:end])
                        explicit = bool(re.match(PREFIX[kind], span))
                        label_plain, label_accented = self.labels[rid]
                        full_label = span == label_plain
                        accented = ' '.join(accented_tokens[start:end])
                        accent_match = accented == label_accented
                        score = (1 - error, explicit, full_label, accent_match,
                                 end if kind == 'province' else 0,
                                 len(candidate), end - start)
                        if rid not in matches or score > matches[rid][0]:
                            matches[rid] = (score, start, end)
        return matches


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default=str(Path(__file__).with_name('database.json')))
    parser.add_argument('--version', choices=['before', 'after'])
    parser.add_argument('--address')
    parser.add_argument('--district', action='store_true')
    args = parser.parse_args()
    engine = Segmenter.load(args.db)
    if args.address is not None:
        start = perf_counter_ns()
        result = engine.parse(args.address, args.version, args.district)
        elapsed = (perf_counter_ns() - start) / 1e9
        print(json.dumps({'result': result, 'elapsed_seconds': elapsed}, ensure_ascii=False))
    else:
        import sys
        for line in sys.stdin:
            request = json.loads(line)
            print(json.dumps(engine.parse(request['address'], request.get('version'), args.district), ensure_ascii=False))


if __name__ == '__main__':
    main()
