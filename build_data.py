"""Rebuild offline database and deterministic tests from bundled source snapshots."""
import json
from pathlib import Path
from collections import Counter
from segmenter import normalize, key

ROOT = Path(__file__).parent


def save(name, value):
    (ROOT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def main():
    rows = []
    def add(version, kind, item, parent=None):
        rid = f'{version}:{kind}:{item["Code"]}'
        aliases = []
        name = item['FullName']
        if kind == 'province' and 'Hồ Chí Minh' in name:
            aliases = ['TP HCM', 'TPHCM', 'HCM', 'Sài Gòn']
        if kind == 'province' and 'Hà Nội' in name:
            aliases = ['HN', 'TP HN']
        rows.append(dict(id=rid, kind=kind, name=name, parent_id=parent,
                         version=version, aliases=aliases))
        return rid
    for version in ('before', 'after'):
        source = json.loads((ROOT / 'source_data' / f'{version}.json').read_text(encoding='utf-8'))
        for province in source:
            pid = add(version, 'province', province)
            for district in (province.get('District') or []):
                did = add(version, 'district', district, pid)
                for ward in (district.get('Ward') or []):
                    add(version, 'ward', ward, did)
            for ward in (province.get('Wards') or []):
                add(version, 'ward', ward, pid)
    # Source street data is at district granularity and historically dated.
    # Preserve only unique names at city level; never invent ward boundaries.
    streets = json.loads((ROOT / 'source_data/streets_HCM.json').read_text(encoding='utf-8'))
    names = sorted({s for d in streets['district'] for s in d.get('street', []) if len(key(s, 'street')) >= 4})
    for version in ('before', 'after'):
        for i, name in enumerate(names):
            rows.append(dict(id=f'{version}:street:{i}', kind='street', name=name,
                             parent_id=f'{version}:province:79', version=version,
                             aliases={'Lý Thường Kiệt': ['LTK'], 'Hồ Xuân Hương': ['HXH', 'H.X.H'],
                                      'Sư Vạn Hạnh': ['SVH'], 'Nguyễn Tri Phương': ['NTP']}.get(name, []),
                             scope='historical_HCM_city_name_list',
                             source_note='Historical street names reused for recognition; post-merger ward membership unverified'))
    save('database.json', rows)
    # Generate expected labels directly from source records, never from parser output.
    by_id = {r['id']: r for r in rows}
    tests = []
    for ward in (r for r in rows if r['kind'] == 'ward'):
        chain = [ward]
        while chain[-1].get('parent_id'):
            chain.append(by_id[chain[-1]['parent_id']])
        province = chain[-1]
        address = ', '.join(r['name'] for r in chain)
        expected = dict(street=None, ward=ward['name'], province=province['name'])
        for category, value in [('canonical', address), ('no_accents', normalize(address))]:
            tests.append(dict(category=category, address=value, version=ward['version'], expected=expected))
    for version in ('before', 'after'):
        tests.append(dict(category='unknown', address='zzzzzzzz qqqqqqqq', version=version,
                          expected=dict(street=None, ward=None, province=None)))
        for name in ['Lý Thường Kiệt', 'Sư Vạn Hạnh', 'Nguyễn Tri Phương']:
            if name in names:
                tests.append(dict(category='street', address=f'268 {name}, TP. HCM', version=version,
                                  expected=dict(street=name, ward=None, province='Thành phố Hồ Chí Minh')))
    save('testcases.json', tests)
    abbreviation_tests = []
    for version in ('before', 'after'):
        for alias, name in [('HXH', 'Hồ Xuân Hương'), ('H.X.H', 'Hồ Xuân Hương'),
                            ('hxh', 'Hồ Xuân Hương'), ('LTK', 'Lý Thường Kiệt'),
                            ('SVH', 'Sư Vạn Hạnh'), ('NTP', 'Nguyễn Tri Phương')]:
            if name not in names:
                raise ValueError(f'Missing street in source: {name}')
            for number in ('12', '268', '12/3'):
                abbreviation_tests.append(dict(category='abbreviation',
                    address=f'{number} {alias}, TP HCM', version=version,
                    expected=dict(street=name, ward=None, province='Thành phố Hồ Chí Minh')))
        for alias in ('BĐ', 'BD', 'B.Đ', 'bđ'):
            abbreviation_tests.append(dict(category='geographic_abbreviation_unknown',
                address=f'{alias} qqqqqq, TP HCM', version=version,
                expected=dict(street=None, ward=None, province='Thành phố Hồ Chí Minh')))
    save('testcases_abbreviations.json', abbreviation_tests)
    save('data_summary.json', {'records': dict(Counter(f'{r["version"]}:{r["kind"]}' for r in rows)),
                               'testcases': len(tests), 'street_scope': 'Historical HCM only; no ward mapping'})
    print((ROOT / 'data_summary.json').read_text(encoding='utf-8'))


if __name__ == '__main__':
    main()


