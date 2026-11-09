import unittest
from segmenter import Segmenter, FieldLimit, expand_abbreviations
from unittest.mock import patch
from time import perf_counter


class Tests(unittest.TestCase):
    def setUp(self):
        self.engine = Segmenter([
            dict(id='p', kind='province', name='TP. Hồ Chí Minh', aliases=['TP HCM'], version='after'),
            dict(id='w', kind='ward', name='Diên Hồng', parent_id='p', version='after'),
            dict(id='s', kind='street', name='LTK', aliases=['Lý Thường Kiệt'], parent_id='p', version='after'),
        ])

    def test_pdf(self):
        self.assertEqual(self.engine.parse('268 Lý Thường Kiệt, Diên Hồng, TP. HCM', 'after'),
                         dict(street='LTK', ward='Diên Hồng', province='TP. Hồ Chí Minh'))

    def test_absent(self):
        self.assertEqual(self.engine.parse('zzzzzz qqqqqq'), dict(street=None, ward=None, province=None))

    def test_no_accents_glued(self):
        self.assertEqual(self.engine.parse('268 LyThuongKiet, DienHong, TPHCM', 'after')['street'], 'LTK')

    def test_ocr_substitution(self):
        self.assertEqual(self.engine.parse('Ly Thuong Kiet, Dien Hongg, TP HCM', 'after')['ward'], 'Diên Hồng')

    def test_missing_database_ward(self):
        self.assertIsNone(self.engine.parse('268 Lý Thường Kiệt, Con cò bé bé, TP HCM', 'after')['ward'])

    def test_version(self):
        self.assertEqual(self.engine.parse('Diên Hồng, TP HCM', 'before'), dict(street=None, ward=None, province=None))

    def test_parent(self):
        rows = [dict(id='a', kind='province', name='Hà Nội'),
                dict(id='b', kind='province', name='Long An'),
                dict(id='w', kind='ward', name='Diên Hồng', parent_id='b')]
        self.assertIsNone(Segmenter(rows).parse('Diên Hồng, Hà Nội')['ward'])

    def test_ambiguous(self):
        rows = [dict(id='a', kind='ward', name='Hòa'), dict(id='b', kind='ward', name='Hoá')]
        self.assertIsNone(Segmenter(rows).parse('hoa')['ward'])

    def test_cycle(self):
        with self.assertRaises(ValueError):
            Segmenter([dict(id='a', kind='ward', name='A', parent_id='a')])

    def test_bounds(self):
        with self.assertRaises(ValueError):
            self.engine.parse('x' * 513)

    def test_hxh(self):
        engine = Segmenter([dict(id='s', kind='street', name='Hồ Xuân Hương')])
        for value in ('HXH', 'hxh', 'H.X.H', 'Hồ Xuân Hương'):
            with self.subTest(value=value):
                self.assertEqual(engine.parse('12 ' + value)['street'], 'Hồ Xuân Hương')

    def test_peninsula_expansion(self):
        # Synthetic fixture to test the abbreviation, not a real administrative claim.
        engine = Segmenter([dict(id='s', kind='street', name='Bán đảo Minh Họa')])
        for value in ('BĐ', 'BD', 'B.Đ', 'bđ', 'bán đảo'):
            with self.subTest(value=value):
                self.assertEqual(engine.parse(value + ' Minh Họa')['street'], 'Bán đảo Minh Họa')
        self.assertEqual(expand_abbreviations('ABĐC'), 'ABĐC')

    def test_stuck_ward_does_not_block_street(self):
        original = self.engine._find
        def find(kind, *args):
            if kind == 'ward':
                raise FieldLimit
            return original(kind, *args)
        with patch.object(self.engine, '_find', side_effect=find):
            self.assertEqual(self.engine.parse('LTK, Diên Hồng, TP HCM', 'after'),
                             dict(street='LTK', ward=None, province='TP. Hồ Chí Minh'))

    def test_large_collision_skips_field(self):
        rows = [dict(id=f'w{i}', kind='ward', name='Cùng Tên') for i in range(600)]
        rows.append(dict(id='s', kind='street', name='Hồ Xuân Hương'))
        result = Segmenter(rows).parse('Cùng Tên, HXH')
        self.assertIsNone(result['ward'])
        self.assertEqual(result['street'], 'Hồ Xuân Hương')

    def test_deadline_is_checked(self):
        # Deterministic simulated clock: budget expires while evaluating a field.
        clock = iter(range(0, 100_000_000, 1_000_000))
        with patch('segmenter.perf_counter_ns', side_effect=lambda: next(clock)):
            self.assertEqual(self.engine.parse('zzzzzz qqqqqq'),
                             dict(street=None, ward=None, province=None))

    def test_long_input_latency(self):
        start = perf_counter()
        result = self.engine.parse(' '.join(['zzzzz'] * 80))
        elapsed = perf_counter() - start
        self.assertEqual(result, dict(street=None, ward=None, province=None))
        self.assertLess(elapsed, .05)


if __name__ == '__main__':
    unittest.main()
